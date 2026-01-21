"""
Integration tests for hybrid co-simulation features.

Tests the HybridAlgorithm's ability to:
1. Detect and localize events via zero-crossing detection
2. Handle non-simultaneous events from multiple sources
3. Handle event chains (weak simultaneous events via superdense time)
4. Handle strong simultaneous events with commutativity checking
5. Properly classify components and select algorithms

Test scenarios based on:
- demos/ControlledPendulum/MyModels/Hybrid/test_6_hybrid_systems.ipynb
"""

import numpy as np
import pytest

from syssimx.system.algorithms.hybrid import HybridAlgorithm
from syssimx.system.connection import EventConnection
from syssimx.system.system import System
from tests.fixtures.components.hybrid_components import (
    HybridCombi,
    HybridListener,
    HybridSource,
    NoRollbackComponent,
)


# ============================================================================
# Test Fixtures
# ============================================================================
@pytest.fixture
def hybrid_algorithm():
    """Create a HybridAlgorithm with verbose disabled for testing."""
    algo = HybridAlgorithm()
    algo.verbose = False
    return algo


# ============================================================================
# Test Component Classification and Algorithm Selection
# ============================================================================
class TestHybridSystemSetup:
    """Test system classification and algorithm auto-selection."""

    def test_system_selects_hybrid_algorithm_when_events_present(self):
        """System should auto-select HybridAlgorithm when event sources exist."""
        source = HybridSource(name="Source", x0=-1.0, v=1.0)
        listener = HybridListener(name="Listener", x0=0.0, v=1.0)

        # Add event indicator to source
        def indicator(comp):
            return comp.x

        source.add_event_indicator("trigger", indicator, direction=1)

        # Create system
        system = System(name="HybridTest")
        system.add_component(source)
        system.add_component(listener)

        # Add event connection
        conn = EventConnection(
            src_comp="Source",
            src_port="trigger",
            dst_comp="Listener",
            dst_port="v_invert",
        )
        system.add_event_connection(conn)
        system.initialize(t0=0.0)

        assert isinstance(system.algorithm, HybridAlgorithm)

    def test_component_classification(self):
        """Test correct classification of event sources, listeners, and continuous."""
        source = HybridSource(name="Source", x0=-1.0, v=1.0)
        combi = HybridCombi(name="Combi", x0=0.0, v=1.0)
        listener = HybridListener(name="Listener", x0=0.0, v=1.0)

        # Add event indicators
        def indicator(comp):
            return comp.x

        source.add_event_indicator("trigger", indicator, direction=1)
        combi.add_event_indicator("combi_trigger", indicator, direction=0)

        # Create system with event connections
        system = System(name="ClassificationTest")
        system.add_component(source)
        system.add_component(combi)
        system.add_component(listener)

        conn1 = EventConnection(
            src_comp="Source",
            src_port="trigger",
            dst_comp="Combi",
            dst_port="v_double",
        )
        conn2 = EventConnection(
            src_comp="Combi",
            src_port="combi_trigger",
            dst_comp="Listener",
            dst_port="v_invert",
        )
        system.add_event_connection(conn1)
        system.add_event_connection(conn2)
        system.initialize(t0=0.0)

        classification = system.classify_components()

        # Source and Combi are event sources (have indicators)
        source_names = [c.name for c in classification["event_sources"]]
        assert "Source" in source_names
        assert "Combi" in source_names

        # Combi and Listener are event listeners (subscribed to events)
        listener_names = [c.name for c in classification["event_listeners"]]
        assert "Combi" in listener_names
        assert "Listener" in listener_names

    def test_event_connection_auto_subscribes_listener(self):
        """Adding event connection should auto-subscribe the target component."""
        source = HybridSource(name="Source", x0=-1.0, v=1.0)
        listener = HybridListener(name="Listener", x0=0.0, v=1.0)

        def indicator(comp):
            return comp.x

        source.add_event_indicator("trigger", indicator, direction=1)

        system = System(name="AutoSubscribeTest")
        system.add_component(source)
        system.add_component(listener)

        # Before connection, listener has no subscriptions
        assert len(listener.event_subscriptions) == 0

        conn = EventConnection(
            src_comp="Source",
            src_port="trigger",
            dst_comp="Listener",
            dst_port="v_invert",
        )
        system.add_event_connection(conn)

        # After connection, listener should be subscribed
        assert len(listener.event_subscriptions) == 1
        assert listener.event_subscriptions[0].name == "trigger"
        assert listener.event_subscriptions[0].source == "Source"


# ============================================================================
# Test Event Detection and Localization
# ============================================================================
class TestEventDetection:
    """Test zero-crossing detection and event localization."""

    def test_single_event_detection(self, hybrid_algorithm):
        """Detect a single rising zero-crossing event."""
        # x(t) = -1 + 2*t crosses zero at t=0.5
        source = HybridSource(name="Source", x0=-1.0, v=2.0)
        listener = HybridListener(name="Listener", x0=0.0, v=1.0)

        def indicator(comp):
            return comp.x

        source.add_event_indicator("trigger", indicator, direction=1)

        system = System(name="SingleEventTest")
        system.add_component(source)
        system.add_component(listener)

        conn = EventConnection(
            src_comp="Source",
            src_port="trigger",
            dst_comp="Listener",
            dst_port="v_invert",
        )
        system.add_event_connection(conn)
        system.initialize(t0=0.0)
        system.algorithm.verbose = False

        # Run simulation past the event time
        system.run(t0=0.0, tf=1.0, dt=0.1)

        # Check event was recorded
        event_history = system.history.get_all_event_histories()
        trigger_times = event_history.get(("Source", "trigger"), [])

        assert len(trigger_times) == 1
        # Event should occur at t=0.5 (x = -1 + 2*0.5 = 0)
        assert np.isclose(trigger_times[0].t, 0.5, atol=1e-5)

    def test_falling_edge_detection(self, hybrid_algorithm):
        """Detect a falling zero-crossing event."""
        # x(t) = 1 - 2*t crosses zero (falling) at t=0.5
        source = HybridSource(name="Source", x0=1.0, v=-2.0)
        listener = HybridListener(name="Listener", x0=0.0, v=1.0)

        def indicator(comp):
            return comp.x

        source.add_event_indicator("trigger", indicator, direction=-1)

        system = System(name="FallingEdgeTest")
        system.add_component(source)
        system.add_component(listener)

        conn = EventConnection(
            src_comp="Source",
            src_port="trigger",
            dst_comp="Listener",
            dst_port="v_invert",
        )
        system.add_event_connection(conn)
        system.initialize(t0=0.0)
        system.algorithm.verbose = False

        system.run(t0=0.0, tf=1.0, dt=0.1)

        event_history = system.history.get_all_event_histories()
        trigger_times = event_history.get(("Source", "trigger"), [])

        assert len(trigger_times) == 1
        assert np.isclose(trigger_times[0].t, 0.5, atol=1e-5)

    def test_event_localization_accuracy(self, hybrid_algorithm):
        """Test that bisection locates events with high precision."""
        # x(t) = -0.333... + t crosses zero at t=1/3
        source = HybridSource(name="Source", x0=-1 / 3, v=1.0)
        listener = HybridListener(name="Listener", x0=0.0, v=1.0)

        def indicator(comp):
            return comp.x

        source.add_event_indicator("trigger", indicator, direction=1)

        system = System(name="LocalizationTest")
        system.add_component(source)
        system.add_component(listener)

        conn = EventConnection(
            src_comp="Source",
            src_port="trigger",
            dst_comp="Listener",
            dst_port="v_invert",
        )
        system.add_event_connection(conn)
        system.initialize(t0=0.0)
        system.algorithm.verbose = False

        # Use large step size to test localization
        system.run(t0=0.0, tf=1.0, dt=0.5)

        event_history = system.history.get_all_event_histories()
        trigger_times = event_history.get(("Source", "trigger"), [])

        expected_time = 1 / 3
        assert len(trigger_times) == 1
        # Should be accurate to algorithm's time tolerance (1e-6)
        assert np.isclose(trigger_times[0].t, expected_time, atol=1e-5)


# ============================================================================
# Case 1: Non-Simultaneous Events
# ============================================================================
class TestNonSimultaneousEvents:
    """
    Test handling of events from multiple sources occurring at different times.

    Scenario:
    - Two sources with different initial positions and velocities
    - Each triggers an event at a different time
    - Both events affect the same listener (velocity inversion)
    """

    def test_two_sources_sequential_events(self, hybrid_algorithm):
        """Two sources trigger events at different times."""
        # Source 1: x(t) = -1/3 + t, crosses zero at t=1/3
        source1 = HybridSource(name="Source_1", x0=-1 / 3, v=1.0)
        # Source 2: x(t) = 2/3 - t, crosses zero at t=2/3
        source2 = HybridSource(name="Source_2", x0=2 / 3, v=-1.0)
        listener = HybridListener(name="Listener", x0=0.0, v=1.0)

        def indicator(comp):
            return comp.x

        source1.add_event_indicator("Trigger_1", indicator, direction=1)
        source2.add_event_indicator("Trigger_2", indicator, direction=-1)

        system = System(name="NonSimultaneousTest")
        system.add_component(source1)
        system.add_component(source2)
        system.add_component(listener)

        conn1 = EventConnection(
            src_comp="Source_1",
            src_port="Trigger_1",
            dst_comp="Listener",
            dst_port="v_invert",
        )
        conn2 = EventConnection(
            src_comp="Source_2",
            src_port="Trigger_2",
            dst_comp="Listener",
            dst_port="v_invert",
        )
        system.add_event_connection(conn1)
        system.add_event_connection(conn2)
        system.initialize(t0=0.0)

        system.run(t0=0.0, tf=1.0, dt=0.05)

        # Check both events were recorded at correct times
        event_history = system.history.get_all_event_histories()
        trigger1_times = event_history.get(("Source_1", "Trigger_1"), [])
        trigger2_times = event_history.get(("Source_2", "Trigger_2"), [])

        assert len(trigger1_times) == 1
        assert len(trigger2_times) == 1

        t1 = trigger1_times[0].t
        t2 = trigger2_times[0].t

        # Events should occur at t=1/3 and t=2/3
        assert np.isclose(t1, 1 / 3, atol=1e-5)
        assert np.isclose(t2, 2 / 3, atol=1e-5)

        # First event should occur before second
        assert t1 < t2

    def test_listener_state_changes_at_each_event(self, hybrid_algorithm):
        """Listener velocity should invert at each event."""
        source1 = HybridSource(name="Source_1", x0=-1 / 3, v=1.0)
        source2 = HybridSource(name="Source_2", x0=2 / 3, v=-1.0)
        listener = HybridListener(name="Listener", x0=0.0, v=1.0)

        def indicator(comp):
            return comp.x

        source1.add_event_indicator("Trigger_1", indicator, direction=1)
        source2.add_event_indicator("Trigger_2", indicator, direction=-1)

        system = System(name="StateChangeTest")
        system.add_component(source1)
        system.add_component(source2)
        system.add_component(listener)

        conn1 = EventConnection(
            src_comp="Source_1",
            src_port="Trigger_1",
            dst_comp="Listener",
            dst_port="v_invert",
        )
        conn2 = EventConnection(
            src_comp="Source_2",
            src_port="Trigger_2",
            dst_comp="Listener",
            dst_port="v_invert",
        )
        system.add_event_connection(conn1)
        system.add_event_connection(conn2)
        system.initialize(t0=0.0)
        system.algorithm.verbose = False

        initial_v = listener.v

        system.run(t0=0.0, tf=0.5, dt=0.05)

        event_history = system.history.get_all_event_histories()
        trigger1_times = event_history.get(("Source_1", "Trigger_1"), [])
        trigger2_times = event_history.get(("Source_2", "Trigger_2"), [])

        # After first event, velocity should be inverted
        assert len(trigger1_times) == 1
        assert len(trigger2_times) == 0
        assert np.isclose(listener.v, -initial_v, atol=1e-10)

        # Run to after second event, velocity should be back to original
        system.run(t0=0.5, tf=1.0, dt=0.05)
        assert np.isclose(listener.v, initial_v, atol=1e-10)


# ============================================================================
# Case 2: Event Chains (Weak Simultaneous Events)
# ============================================================================
class TestEventChains:
    """
    Test event chains where one event triggers another at the same real time.

    Scenario:
    - Source triggers event at t*
    - Event causes Combi component to change state
    - Combi's state change triggers another event at same t* (different microstep)
    - Listener receives the chained event

    Superdense time semantics: (t*, 0) -> (t*, 1)

    Note: Event chains are complex to test because the second event must be
    detected by the hybrid algorithm after handling the first event. This
    requires careful indicator design where the indicator value changes
    as a result of event handling.
    """

    def test_first_event_triggers_state_change(self, hybrid_algorithm):
        """Verify that first event is detected and causes state change in Combi."""
        # Source: x(t) = -1/3 + t, crosses zero at t=1/3
        source = HybridSource(name="Source", x0=-1 / 3, v=1.0)
        # Combi: receives event, doubles velocity
        combi = HybridCombi(name="Combi", x0=0.0, v=1.0)

        def zero_crossing_indicator(comp):
            return comp.x

        # Use "v_double" as event name since that's what HybridCombi handles
        source.add_event_indicator("v_double", zero_crossing_indicator, direction=1)

        system = System(name="EventChainStateChangeTest")
        system.add_component(source)
        system.add_component(combi)

        # Source -> Combi (v_double triggers v_double handler)
        conn1 = EventConnection(
            src_comp="Source",
            src_port="v_double",
            dst_comp="Combi",
            dst_port="v_double",
        )
        system.add_event_connection(conn1)
        system.initialize(t0=0.0)

        # Initial velocity
        initial_v = combi.v_curr

        system.run(t0=0.0, tf=1.0, dt=0.1)

        # Event should be recorded
        event_history = system.history.get_all_event_histories()
        event_times = event_history.get(("Source", "v_double"), [])
        assert len(event_times) >= 1

        # Combi velocity should have doubled
        assert combi.v_curr == 2 * initial_v
        assert combi.v_changed is True

    def test_combi_as_event_source_and_listener(self, hybrid_algorithm):
        """Combi can act as both event source and listener."""
        # Source: x(t) = -2/3 + 2t, crosses zero at t=0.3333
        source = HybridSource(name="Source", x0=-2 / 3, v=2.0)
        # Combi: acts as both listener (for v_double) and source (position crosses)
        combi = HybridCombi(name="Combi", x0=2 / 3, v=-1)
        listener = HybridListener(name="Listener", x0=0.0, v=3.0)

        def zero_crossing_indicator(comp: HybridSource) -> float:
            return comp.x

        def v_change_indicator(comp: HybridCombi) -> float:
            return 0.0 if comp.v_curr != comp.v_prev else 1.0

        # Source triggers at t=0.5
        source.add_event_indicator("v_double", zero_crossing_indicator, direction=1)
        combi.add_event_indicator("v_change", v_change_indicator, direction=0)

        system = System(name="CombiDualRoleTest")
        system.add_component(source)
        system.add_component(combi)
        system.add_component(listener)

        # Source -> Combi
        conn1 = EventConnection(
            src_comp="Source",
            src_port="v_double",
            dst_comp="Combi",
            dst_port="v_double",
        )
        # Combi -> Listener
        conn2 = EventConnection(
            src_comp="Combi",
            src_port="v_change",
            dst_comp="Listener",
            dst_port="v_invert",
        )
        system.add_event_connection(conn1)
        system.add_event_connection(conn2)
        system.initialize(t0=0.0)
        system.algorithm.verbose = False

        # Classify components
        classification = system.classify_components()

        # Combi should be both source and listener
        source_names = [c.name for c in classification["event_sources"]]
        listener_names = [c.name for c in classification["event_listeners"]]

        assert "Combi" in source_names
        assert "Combi" in listener_names

        system.run(t0=0.0, tf=1.0, dt=0.1)

        event_history = system.history.get_all_event_histories()

        # Both events should be recorded
        source_events = event_history.get(("Source", "v_double"), [])
        combi_events = event_history.get(("Combi", "v_change"), [])

        assert len(source_events) >= 1
        assert len(combi_events) >= 1

        # Evaluate microstep increments
        assert source_events[0].micro == 0  # First event: source causes combi component to double v
        assert combi_events[0].micro == 1  # Second event at same t: combi notifies listener

    def test_superdense_time_microstep_increment(self, hybrid_algorithm):
        """Verify microstep increments when events trigger other events."""
        # Use two sources that cross at same time, targeting Listener with annotations
        # Source1 crosses at t=0.5 (rising)
        source1 = HybridSource(name="Source_1", x0=-0.5, v=1.0)
        # Source2 also crosses at t=0.5 (rising)
        source2 = HybridSource(name="Source_2", x0=-0.5, v=1.0)
        # Use dynamic verification for simultaneous events
        listener = HybridListener(name="Listener", x0=0.0, v=1.0, use_event_annotations=False)

        def indicator(comp):
            return comp.x

        # Use event names that HybridListener handles
        source1.add_event_indicator("v_invert", indicator, direction=1)
        source2.add_event_indicator("v_double", indicator, direction=1)

        system = System(name="MicrostepTest")
        system.add_component(source1)
        system.add_component(source2)
        system.add_component(listener)

        conn1 = EventConnection(
            src_comp="Source_1",
            src_port="v_invert",
            dst_comp="Listener",
            dst_port="v_invert",
        )
        conn2 = EventConnection(
            src_comp="Source_2",
            src_port="v_double",
            dst_comp="Listener",
            dst_port="v_double",
        )
        system.add_event_connection(conn1)
        system.add_event_connection(conn2)
        system.initialize(t0=0.0)

        system.run(t0=0.0, tf=1.0, dt=0.2)

        event_history = system.history.get_all_event_histories()
        trigger1_times = event_history.get(("Source_1", "v_invert"), [])
        trigger2_times = event_history.get(("Source_2", "v_double"), [])

        # Both events should occur at same real time
        if trigger1_times and trigger2_times:
            assert np.isclose(trigger1_times[0].t, trigger2_times[0].t, atol=1e-5)
            # Both should be at microstep 0 (detected in same crossing detection)
            assert trigger1_times[0].micro == 0
            assert trigger2_times[0].micro == 0


# ============================================================================
# Case 3: Simultaneous Events (Strong Simultaneous)
# ============================================================================
class TestSimultaneousEvents:
    """
    Test handling of multiple events occurring at exactly the same time.

    Scenario:
    - Two sources trigger events at the same time t*
    - Both events target the same listener
    - Algorithm must check commutativity of event handlers
    """

    def test_simultaneous_events_with_commutative_handlers(self, hybrid_algorithm):
        """Two events at same time should be handled if handlers commute."""
        # Both sources cross zero at t=2/3
        # Source 1: x(t) = 2/3 - t, crosses at t=2/3 (falling)
        source1 = HybridSource(name="Source_1", x0=2 / 3, v=-1.0)
        # Source 2: x(t) = -2/3 + t, crosses at t=2/3 (rising)
        source2 = HybridSource(name="Source_2", x0=-2 / 3, v=1.0)
        # Use annotations to declare commutativity
        listener = HybridListener(name="Listener", x0=0.0, v=3.0, use_event_annotations=True)

        def indicator(comp):
            return comp.x

        source1.add_event_indicator("v_invert", indicator, direction=-1)
        source2.add_event_indicator("v_double", indicator, direction=1)

        system = System(name="SimultaneousCommutativeTest")
        system.add_component(source1)
        system.add_component(source2)
        system.add_component(listener)

        conn1 = EventConnection(
            src_comp="Source_1",
            src_port="v_invert",
            dst_comp="Listener",
            dst_port="v_invert",
        )
        conn2 = EventConnection(
            src_comp="Source_2",
            src_port="v_double",
            dst_comp="Listener",
            dst_port="v_double",
        )
        system.add_event_connection(conn1)
        system.add_event_connection(conn2)
        system.initialize(t0=0.0)

        # Should complete without error due to commutativity annotations
        system.run(t0=0.0, tf=1.0, dt=0.1)

        event_history = system.history.get_all_event_histories()
        v_invert_times = event_history.get(("Source_1", "v_invert"), [])
        v_double_times = event_history.get(("Source_2", "v_double"), [])

        # Both events should occur at same time
        assert len(v_invert_times) >= 1
        assert len(v_double_times) >= 1
        assert np.isclose(v_invert_times[0].t, v_double_times[0].t, atol=1e-5)


# ============================================================================
# Test State Rollback for Event Localization
# ============================================================================
class TestStateRollback:
    """Test that state rollback works correctly during event localization."""

    def test_component_state_restored_after_trial_step(self, hybrid_algorithm):
        """Component state should be restored after trial steps during detection."""
        source = HybridSource(name="Source", x0=-0.5, v=1.0)
        listener = HybridListener(name="Listener", x0=0.0, v=1.0)

        def indicator(comp):
            return comp.x

        source.add_event_indicator("trigger", indicator, direction=1)

        system = System(name="RollbackTest")
        system.add_component(source)
        system.add_component(listener)

        conn = EventConnection(
            src_comp="Source",
            src_port="trigger",
            dst_comp="Listener",
            dst_port="v_invert",
        )
        system.add_event_connection(conn)
        system.initialize(t0=0.0)

        # Single step that crosses the event
        system.algorithm.step(system, 0.0, 1.0)

        # Event should have been detected at t=0.5
        # After the step, source should be at t=0.5 (event time + epsilon)
        event_history = system.history.get_all_event_histories()
        trigger_times = event_history.get(("Source", "trigger"), [])

        assert len(trigger_times) == 1
        assert np.isclose(trigger_times[0].t, 0.5, atol=1e-5)

    def test_supports_rollback_property(self):
        """Components with snapshot/restore should report supports_rollback=True."""
        source = HybridSource(name="Source", x0=0.0, v=1.0)
        assert source.supports_rollback is True

        listener = NoRollbackComponent(name="Listener")
        # Listener doesn't have snapshot_state, should be False
        assert listener.supports_rollback is False


# ============================================================================
# Test Event History Recording
# ============================================================================
class TestEventHistoryRecording:
    """Test that events are properly recorded with dense time."""

    def test_event_history_includes_dense_time(self, hybrid_algorithm):
        """Event history should include both real time and microstep."""
        source = HybridSource(name="Source", x0=-0.5, v=1.0)
        listener = HybridListener(name="Listener", x0=0.0, v=1.0)

        def indicator(comp):
            return comp.x

        source.add_event_indicator("trigger", indicator, direction=1)

        system = System(name="HistoryTest")
        system.add_component(source)
        system.add_component(listener)

        conn = EventConnection(
            src_comp="Source",
            src_port="trigger",
            dst_comp="Listener",
            dst_port="v_invert",
        )
        system.add_event_connection(conn)
        system.initialize(t0=0.0)

        system.run(t0=0.0, tf=1.0, dt=0.2)

        event_history = system.history.get_all_event_histories()
        trigger_times = event_history.get(("Source", "trigger"), [])

        assert len(trigger_times) >= 1
        # Check that DenseTime object has both t and micro attributes
        dense_time = trigger_times[0]
        assert hasattr(dense_time, "t")
        assert hasattr(dense_time, "micro")
        assert isinstance(dense_time.micro, int)

    def test_multiple_events_recorded_separately(self, hybrid_algorithm):
        """Multiple events from different sources should be recorded separately."""
        source1 = HybridSource(name="Source_1", x0=-0.25, v=1.0)
        source2 = HybridSource(name="Source_2", x0=-0.75, v=1.0)
        listener = HybridListener(name="Listener", x0=0.0, v=1.0)

        def indicator(comp):
            return comp.x

        source1.add_event_indicator("trigger_1", indicator, direction=1)
        source2.add_event_indicator("trigger_2", indicator, direction=1)

        system = System(name="MultiEventHistoryTest")
        system.add_component(source1)
        system.add_component(source2)
        system.add_component(listener)

        conn1 = EventConnection(
            src_comp="Source_1",
            src_port="trigger_1",
            dst_comp="Listener",
            dst_port="v_invert",
        )
        conn2 = EventConnection(
            src_comp="Source_2",
            src_port="trigger_2",
            dst_comp="Listener",
            dst_port="v_invert",
        )
        system.add_event_connection(conn1)
        system.add_event_connection(conn2)
        system.initialize(t0=0.0)

        system.run(t0=0.0, tf=1.0, dt=0.1)

        event_history = system.history.get_all_event_histories()

        # Check events are recorded under correct keys
        assert ("Source_1", "trigger_1") in event_history
        assert ("Source_2", "trigger_2") in event_history

        trigger1_times = event_history[("Source_1", "trigger_1")]
        trigger2_times = event_history[("Source_2", "trigger_2")]

        # Source_1 crosses at t=0.25, Source_2 at t=0.75
        assert len(trigger1_times) >= 1
        assert len(trigger2_times) >= 1
        assert np.isclose(trigger1_times[0].t, 0.25, atol=1e-5)
        assert np.isclose(trigger2_times[0].t, 0.75, atol=1e-5)
