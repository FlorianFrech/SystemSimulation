"""
Unit tests for syssimx.core.base

Tests CoSimComponent base class functionality using the Gain component.
"""

import numpy as np
import pytest

from syssimx.core.base import CoSimComponent
from syssimx.core.events import Event, EventIndicator
from syssimx.core.port import PortSpec, PortState, PortType
from syssimx.utilities.units import ureg
from tests.fixtures.components import (
    GainComponent,
    HybridCombi,
    HybridListener,
    HybridSource,
    IntegratorComponent,
    NoRollbackComponent,
    SimpleGain,
)


# ============================================================================
# Test CoSimComponent Basics
# ============================================================================
class TestCoSimComponentBasics:
    """Test CoSimComponent creation and basic properties."""

    def test_construction(self):
        comp = GainComponent(name="Gain", gain=2.0)
        assert comp.name == "Gain"
        assert isinstance(comp, GainComponent)
        assert isinstance(comp, CoSimComponent)

        # Port specifications
        u_port_spec = PortSpec(
            name="u", type=PortType.REAL, direction="in", unit="N*m", description="Input torque"
        )
        y_port_spec = PortSpec(
            name="y",
            type=PortType.REAL,
            direction="out",
            unit="rad/s",
            description="Output angular velocity",
        )
        assert comp.input_specs["u"] == u_port_spec
        assert comp.output_specs["y"] == y_port_spec

    def test_parameter_getting_setting_validation(self):
        comp = GainComponent(name="Gain", gain=2.0)
        assert comp.get_parameters("k") == {"k": 2.0}

        comp.set_parameters(k=3.5)
        assert comp.get_parameters("k") == {"k": 3.5}

        with pytest.raises(TypeError):
            comp.set_parameters(k="invalid")  # k must be float or int

        with pytest.raises(KeyError):
            comp.set_parameters(nonexistent=1.0)  # nonexistent parameter

    def test_get_parameters_all(self):
        """Test get_parameters() with no arguments returns all parameters."""
        comp = GainComponent(name="Gain", gain=2.0)
        all_params = comp.get_parameters()
        assert "k" in all_params
        assert all_params["k"] == 2.0

    def test_get_parameters_unknown_raises_keyerror(self):
        """Test get_parameters with unknown parameter name raises KeyError."""
        comp = GainComponent(name="Gain", gain=2.0)
        with pytest.raises(KeyError, match="Unknown parameter 'nonexistent'"):
            comp.get_parameters("nonexistent")

    def test_initialization(self):
        comp = GainComponent(name="Gain", gain=2.0)
        comp.initialize(t0=0.0)  # NOW ports exist
        assert "u" in comp.inputs
        assert "y" in comp.outputs
        assert isinstance(comp.inputs["u"], PortState)
        assert isinstance(comp.outputs["y"], PortState)

        # Check default values
        u_value = comp.inputs["u"].get()
        assert u_value is not None
        assert np.isclose(u_value.magnitude, 0.0)  # Default REAL value

        y_value = comp.outputs["y"].get()
        assert y_value is not None
        assert np.isclose(y_value.magnitude, 0.0)  # 2.0 * 0.0

    def test_double_initialization_prevented(self):
        """Test that calling initialize() twice does not reinitialize."""
        comp = HybridSource("Source", x0=5.0, v=1.0, t0=0.0)
        comp.initialize(t0=0.0)

        # Modify state after initialization
        comp.x = 999.0

        # Second initialize should be a no-op
        comp.initialize(t0=10.0)

        # State should NOT be reset, time should NOT change
        assert comp.x == 999.0
        assert comp.t == 0.0  # Original t0, not 10.0
        assert comp._is_initialized is True

    def test_set_inputs(self):
        comp = GainComponent(name="Gain", gain=2.0)
        comp.initialize(t0=0.0)
        inputs = {"u": 5.0 * ureg("N*m")}
        comp.set_inputs(inputs, t=0.0)
        assert np.isclose(comp.inputs["u"].get().magnitude, 5.0)
        assert np.isclose(comp.inputs["u"].t_last, 0.0)

    def test_set_inputs_unknown_port_raises_keyerror(self):
        """Test set_inputs with unknown port raises KeyError."""
        comp = GainComponent(name="Gain", gain=2.0)
        comp.initialize(t0=0.0)
        with pytest.raises(KeyError, match="Input port 'nonexistent' not found"):
            comp.set_inputs({"nonexistent": 1.0}, t=0.0)

    def test_evaluate_outputs(self):
        comp = GainComponent(name="Gain", gain=2.0)
        comp.initialize(t0=0.0)
        inputs = {"u": 4.0 * ureg("N*m")}
        outputs = comp.evaluate_outputs(inputs)
        assert np.isclose(outputs["y"].magnitude, 8.0)  # 2.0 * 4.0
        assert outputs["y"].is_compatible_with(ureg("rad/s"))

    def test_get_outputs(self):
        comp = GainComponent(name="Gain", gain=2.0)
        comp.initialize(t0=0.0)
        inputs = {"u": 3.0 * ureg("N*m")}
        comp.set_inputs(inputs, t=0.0)
        comp._update_output_states(t=1.0)
        outputs = comp.get_outputs()
        assert np.isclose(outputs["y"].magnitude, 6.0)  # 2.0 * 3.0
        assert outputs["y"].is_compatible_with(ureg("rad/s"))

    def test_do_step(self):
        comp = IntegratorComponent(x0=0.0)
        comp.initialize(t0=0.0)
        inputs = {"u": 1.0}  # constant input (rate of change)
        comp.set_inputs(inputs, t=0.0)
        comp.do_step(t=0.0, dt=1.0)
        outputs = comp.get_outputs()
        history = comp.get_history()

        assert np.isclose(comp.t, 1.0)  # Current time after step
        assert np.isclose(outputs["y"], 1.0)  # Integrated value should be
        assert np.isclose(history["y"]["values"][0], 0.0)  # History should show initial value
        assert np.isclose(history["y"]["values"][1], 1.0)  # and updated value


# ============================================================================
# Test History Recording Flag (trial-step suppression)
# ============================================================================
class TestRecordHistoryFlag:
    """Test the ``_record_history`` flag used to suppress trial-step recording.

    The hybrid master algorithm advances event sources over candidate
    intervals during event localization and then rolls them back. Those
    trial advances must not append samples to a component's history. This
    is controlled by the ``_record_history`` flag.
    """

    def test_record_history_defaults_true(self):
        """A freshly constructed component records history by default."""
        comp = IntegratorComponent(x0=0.0)
        assert comp._record_history is True

    def test_do_step_records_when_enabled(self):
        comp = IntegratorComponent(x0=0.0)
        comp.initialize(t0=0.0)
        comp.set_inputs({"u": 1.0}, t=0.0)

        before = len(comp.history.get_port_history("y"))
        comp.do_step(t=0.0, dt=1.0)
        after = len(comp.history.get_port_history("y"))

        assert after == before + 1

    def test_do_step_skips_recording_when_disabled(self):
        """With ``_record_history`` False, ``do_step`` advances state but
        does not append to history (the trial-step contract)."""
        comp = IntegratorComponent(x0=0.0)
        comp.initialize(t0=0.0)
        comp.set_inputs({"u": 1.0}, t=0.0)

        before = len(comp.history.get_port_history("y"))
        comp._record_history = False
        comp.do_step(t=0.0, dt=1.0)
        after = len(comp.history.get_port_history("y"))

        # State advanced ...
        assert np.isclose(comp.t, 1.0)
        # ... but no history sample was recorded.
        assert after == before

    def test_recording_resumes_after_reenabling(self):
        comp = IntegratorComponent(x0=0.0)
        comp.initialize(t0=0.0)
        comp.set_inputs({"u": 1.0}, t=0.0)

        comp._record_history = False
        comp.do_step(t=0.0, dt=1.0)  # suppressed
        comp._record_history = True
        comp.do_step(t=1.0, dt=1.0)  # recorded

        # Initial sample from initialize() + the one recorded step.
        assert len(comp.history.get_port_history("y")) == 2


# ============================================================================
# Test CoSimComponent Hybrid Functionality
# ============================================================================
class TestCoSimComponentHybrid:
    """Test CoSimComponent hybrid features using a simple hybrid component."""

    class TestEventIndicator:
        """A simple hybrid component for testing event indicators."""

        def test_add_event_indicator(self):
            comp = HybridSource("HybridComp", x0=0.0, v=1.0, t0=0.0)
            comp.initialize(t0=0.0)

            def event_function(c: HybridSource) -> float:
                return c.x

            assert not comp.has_state_events
            comp.add_event_indicator(name="test_event", func=event_function, direction=1)
            assert comp.has_state_events
            assert "test_event" in comp.event_indicators

        def test_duplicate_event_indicator(self):
            comp = HybridSource("HybridComp", x0=0.0, v=1.0, t0=0.0)
            comp.initialize(t0=0.0)

            def event_function(c: HybridSource) -> float:
                return c.x

            comp.add_event_indicator(name="test_event", func=event_function, direction=1)
            with pytest.raises(KeyError):
                comp.add_event_indicator(name="test_event", func=event_function, direction=1)

        def test_invalid_event_direction(self):
            comp = HybridSource("HybridComp", x0=0.0, v=1.0, t0=0.0)
            comp.initialize(t0=0.0)

            def event_function(c: HybridSource) -> float:
                return c.x

            with pytest.raises(ValueError):
                comp.add_event_indicator(
                    name="invalid_direction_event", func=event_function, direction=2
                )  # Invalid direction

        def test_evaluate_event_indicators(self):
            comp = HybridSource("HybridComp", x0=0.0, v=1.0, t0=0.0)
            comp.initialize(t0=0.0)
            comp.add_event_indicator(name="test_event", func=lambda c: c.x, direction=1)
            # Initially x=0.0
            value = comp.evaluate_event_indicators()["test_event"]
            assert np.isclose(value, 0.0)

            # Advance time to t=1.0, x should be 1.0
            comp.do_step(t=0.0, dt=1.0)
            value = comp.evaluate_event_indicators()["test_event"]
            assert np.isclose(value, 1.0)

    class TestEventDetection:
        """Test event detection mechanism in hybrid components."""

        def test_event_detection_rising(self):
            comp = HybridSource("HybridComp", x0=-1.0, v=1.0, t0=0.0)
            comp.initialize(t0=0.0)
            comp.add_event_indicator(name="test_event", func=lambda c: c.x, direction=1)
            indicators_prev = comp.evaluate_event_indicators()
            # Advance time to t=2.0, x should be 1.0 (crossed zero)
            comp.do_step(t=0.0, dt=2.0)
            indicators_curr = comp.evaluate_event_indicators()
            crossed = comp.detect_event_crossings(previous=indicators_prev, current=indicators_curr)
            assert "test_event" in crossed

        def test_event_detection_falling(self):
            comp = HybridSource("HybridComp", x0=1.0, v=-1.0, t0=0.0)
            comp.initialize(t0=0.0)
            comp.add_event_indicator(name="test_event", func=lambda c: c.x, direction=-1)
            indicators_prev = comp.evaluate_event_indicators()
            # Advance time to t=2.0, x should be -1.0 (crossed zero)
            comp.do_step(t=0.0, dt=2.0)
            indicators_curr = comp.evaluate_event_indicators()
            crossed = comp.detect_event_crossings(previous=indicators_prev, current=indicators_curr)
            assert "test_event" in crossed

        def test_event_detection_both_directions(self):
            comp = HybridSource("HybridComp", x0=-1.0, v=2.0, t0=0.0)
            comp.initialize(t0=0.0)
            comp.add_event_indicator(name="test_event", func=lambda c: c.x, direction=0)
            indicators_prev = comp.evaluate_event_indicators()
            # Advance time to t=1.0, x should be 1.0 (crossed zero)
            comp.do_step(t=0.0, dt=1.0)
            indicators_curr = comp.evaluate_event_indicators()
            crossed = comp.detect_event_crossings(previous=indicators_prev, current=indicators_curr)
            assert "test_event" in crossed

    class TestEventSubscription:
        """Test event subscription mechanism in hybrid components."""

        def test_event_subscription(self):
            comp = HybridCombi("HybridCombi", x0=0.0, v=1.0, t0=0.0)
            comp.initialize(t0=0.0)

            def event_function(c: HybridCombi) -> float:
                return c.x

            event = Event(name="source_event", source=comp.name, direction=1)
            comp.add_event_indicator(
                name=event.name, func=event_function, direction=event.direction
            )

            ei = EventIndicator(name=event.name, function=event_function, direction=event.direction)
            comp.subscribe_event(event)

            assert "source_event" in comp.event_indicators.keys()
            assert comp.event_indicators["source_event"].function == ei.function
            assert comp.event_indicators["source_event"].direction == ei.direction
            assert event in comp.event_subscriptions

        def test_has_event_subscriptions(self):
            comp = HybridCombi("HybridCombi", x0=0.0, v=1.0, t0=0.0)
            comp.initialize(t0=0.0)
            assert not comp.has_event_subscriptions

            def event_function(c: HybridCombi) -> float:
                return c.x

            event = Event(name="source_event", source=comp.name, direction=1)
            comp.add_event_indicator(
                name=event.name, func=event_function, direction=event.direction
            )
            comp.subscribe_event(event)

            assert comp.has_event_subscriptions

    class TestStateRollback:
        """Test state snapshot and rollback functionality in hybrid components."""

        def test_support_rollback(self):
            source = HybridSource("HybridComp")
            listener = NoRollbackComponent("HybridListener")
            source.initialize(t0=0.0)
            listener.initialize(t0=0.0)
            assert source.supports_rollback
            assert not listener.supports_rollback

        def test_snapshot_and_restore_state(self):
            comp = HybridCombi("HybridCombi", x0=0.0, v=1.0, t0=0.0)
            comp.initialize(t0=0.0)
            comp.do_step(t=0.0, dt=2.0)  # Advance to t=2.0
            snapshot = comp.snapshot_state()
            t_snapshot = comp.t

            # Change state
            comp.v_curr += 2.0
            comp.do_step(t=2.0, dt=1.0)  # Advance to t=3.0

            # Restore state
            comp.restore_state(snapshot, t=t_snapshot)
            assert np.isclose(comp.t, t_snapshot)
            assert np.isclose(comp.x, 2.0)  # x should be back to value at t=2.0
            assert np.isclose(comp.v_curr, 1.0)  # v should be back to initial value

        def test_restore_state_invalid(self):
            comp = HybridCombi("HybridCombi", x0=0.0, v=1.0, t0=0.0)
            comp.initialize(t0=0.0)
            snapshot = {"invalid_key": 123}  # Invalid snapshot

            with pytest.raises(KeyError):
                comp.restore_state(snapshot, t=0.0)

        def test_rollback_with_event_indicators(self):
            comp = HybridSource("HybridComp", x0=0.0, v=1.0, t0=0.0)
            comp.initialize(t0=0.0)
            comp.add_event_indicator(name="test_event", func=lambda c: c.x, direction=1)
            comp.do_step(t=0.0, dt=2.0)  # Advance to t=2.0
            indicatores_before = comp.evaluate_event_indicators()
            snapshot = comp.snapshot_state()
            t_snapshot = comp.t

            # Change state
            comp.v += 2.0
            comp.do_step(t=2.0, dt=1.0)  # Advance to t=3.0
            indicators_after = comp.evaluate_event_indicators()
            assert not np.isclose(indicatores_before["test_event"], indicators_after["test_event"])

            # Restore state
            comp.restore_state(snapshot, t=t_snapshot)
            indicators_restored = comp.evaluate_event_indicators()
            assert np.isclose(indicatores_before["test_event"], indicators_restored["test_event"])


# ============================================================================
# Test CoSimComponent Event Indicator Edge Cases
# ============================================================================
class TestEventIndicatorEdgeCases:
    """Test edge cases for event indicator registration and handling."""

    def test_add_event_indicator_before_initialization(self):
        """Test adding event indicator before initialize() defers port creation."""
        comp = HybridSource("Source", x0=0.0, v=1.0, t0=0.0)

        # Add event indicator BEFORE initialization
        comp.add_event_indicator(name="trigger", func=lambda c: c.x, direction=1)

        # Indicator registered but no output port yet
        assert "trigger" in comp.event_indicators
        assert "trigger" not in comp.outputs  # Port not created yet

        # Initialize - port should be created
        comp.initialize(t0=0.0)

        assert "trigger" in comp.outputs
        assert "trigger" in comp.output_specs
        assert comp.outputs["trigger"].spec.type == PortType.EVENT

    def test_add_event_indicator_after_initialization(self):
        """Test adding event indicator after initialize() creates port immediately."""
        comp = HybridSource("Source", x0=0.0, v=1.0, t0=0.0)
        comp.initialize(t0=0.0)

        # Add event indicator AFTER initialization
        comp.add_event_indicator(name="trigger", func=lambda c: c.x, direction=1)

        # Port should be created immediately
        assert "trigger" in comp.event_indicators
        assert "trigger" in comp.outputs
        assert "trigger" in comp.output_specs
        assert comp.outputs["trigger"].spec.type == PortType.EVENT


# ============================================================================
# Test CoSimComponent Event Subscription Edge Cases
# ============================================================================
class TestEventSubscriptionEdgeCases:
    """Test edge cases for event subscription."""

    def test_subscribe_event_with_time_raises_valueerror(self):
        """Test subscribing to event with time set raises ValueError."""
        comp = HybridCombi("Combi", x0=0.0, v=1.0, t0=0.0)
        comp.initialize(t0=0.0)

        event_with_time = Event(name="some_event", source="OtherComp", direction=1, time=5.0)

        with pytest.raises(ValueError, match="must not include a time"):
            comp.subscribe_event(event_with_time)

    def test_subscribe_event_duplicate_raises_keyerror(self):
        """Test subscribing to same event twice raises KeyError."""
        comp = HybridCombi("Combi", x0=0.0, v=1.0, t0=0.0)
        comp.initialize(t0=0.0)

        event = Event(name="some_event", source="OtherComp", direction=1)
        comp.subscribe_event(event)

        with pytest.raises(KeyError, match="already exists"):
            comp.subscribe_event(event)


# ============================================================================
# Test CoSimComponent Internal Event Hints
# ============================================================================
class TestInternalEventHints:
    """Test internal event hint reporting for precise event localization."""

    def test_report_and_get_internal_event_hints(self):
        """Test reporting and retrieving internal event hints."""
        comp = HybridSource("Source", x0=0.0, v=1.0, t0=0.0)
        comp.initialize(t0=0.0)
        comp.add_event_indicator(name="trigger", func=lambda c: c.x, direction=1)

        # Report an internal event
        comp.report_internal_event(
            event_name="trigger",
            t_before=0.9,
            t_after=1.1,
            indicator_before=-0.1,
            indicator_after=0.1,
        )

        # Get and clear hints
        hints = comp.get_internal_event_hints()

        assert len(hints) == 1
        assert hints[0].event_name == "trigger"
        assert hints[0].t_before == 0.9
        assert hints[0].t_after == 1.1
        assert hints[0].indicator_before == -0.1
        assert hints[0].indicator_after == 0.1

        # Hints should be cleared
        assert len(comp.get_internal_event_hints()) == 0


# ============================================================================
# Test CoSimComponent Event Handling
# ============================================================================
class TestEventHandling:
    """Test event handling workflow."""

    def test_handle_event_calls_internal_hook_and_records(self):
        """Test handle_event calls _handle_events_internal and records outputs."""
        comp = HybridListener("Listener", x0=0.0, v=1.0, t0=0.0)
        comp.initialize(t0=0.0)
        comp.do_step(t=0.0, dt=1.0)  # x = 1.0

        initial_v = comp.v
        port_history = comp.history.get_port_history("x")
        initial_history_len = len(port_history)

        # Handle v_invert event
        comp.handle_event(["v_invert"], t=1.0)

        # Velocity should be inverted
        assert comp.v == -initial_v

        # History should have new record
        assert len(port_history) == initial_history_len + 1


# ============================================================================
# Test CoSimComponent Properties
# ============================================================================
class TestCoSimComponentProperties:
    """Test component properties for direct feedthrough and reactive inputs."""

    def test_reactive_inputs_with_feedthrough(self):
        """Test reactive_inputs returns inputs with direct feedthrough."""
        comp = SimpleGain(name="Gain", gain=2.0)

        # SimpleGain has direct_feedthrough = {"y": {"u"}}
        reactive = comp.reactive_inputs

        assert reactive == {"u"}

    def test_reactive_inputs_empty_when_no_feedthrough(self):
        """Test reactive_inputs is empty when no direct feedthrough."""
        comp = HybridSource("Source")
        # HybridSource has no direct feedthrough

        reactive = comp.reactive_inputs

        assert reactive == set()

    def test_has_direct_feedthrough_true(self):
        """Test has_direct_feedthrough returns True when feedthrough exists."""
        comp = SimpleGain(name="Gain", gain=2.0)

        assert comp.has_direct_feedthrough is True

    def test_has_direct_feedthrough_false(self):
        """Test has_direct_feedthrough returns False when no feedthrough."""
        comp = HybridSource("Source")

        assert comp.has_direct_feedthrough is False


# ============================================================================
# Test CoSimComponent Cleanup
# ============================================================================
class TestCoSimComponentCleanup:
    """Test component reset and cleanup functionality."""

    def test_reset_clears_time_and_history(self):
        """Test reset() clears time and history."""
        comp = HybridSource("Source", x0=0.0, v=1.0, t0=0.0)
        comp.initialize(t0=0.0)
        comp.do_step(t=0.0, dt=1.0)
        comp.do_step(t=1.0, dt=1.0)

        assert comp.t > 0.0
        port_history = comp.history.get_port_history("x")
        assert len(port_history) > 1

        comp.reset()

        assert comp.t == 0.0
        assert len(port_history) == 0


# ============================================================================
# Test CoSimComponent History Arrays
# ============================================================================
class TestHistoryArrays:
    """Test get_history_arrays method."""

    def test_get_history_arrays(self):
        """Test get_history_arrays returns numpy arrays."""
        comp = IntegratorComponent(x0=0.0)
        comp.initialize(t0=0.0)
        comp.set_inputs({"u": 1.0}, t=0.0)
        comp.do_step(t=0.0, dt=1.0)
        comp.do_step(t=1.0, dt=1.0)

        time_array, values_dict = comp.get_history_arrays()

        assert isinstance(time_array, np.ndarray)
        assert "y" in values_dict
        assert isinstance(values_dict["y"], np.ndarray)
        assert len(time_array) == 3  # t=0, t=1, t=2
        assert len(values_dict["y"]) == 3

    def test_get_history_arrays_specific_ports(self):
        """Test get_history_arrays with specific port names."""
        comp = HybridListener("Listener", x0=0.0, v=1.0, t0=0.0)
        comp.initialize(t0=0.0)
        comp.do_step(t=0.0, dt=1.0)

        time_array, values_dict = comp.get_history_arrays(port_names=["x"])

        assert "x" in values_dict
        assert "v" not in values_dict


# ============================================================================
# Test Base Class Rollback NotImplementedError
# ============================================================================
class TestBaseRollbackNotImplemented:
    """Test that base class raises NotImplementedError for rollback methods."""

    def test_snapshot_state_not_implemented(self):
        """Test snapshot_state raises NotImplementedError for non-rollback component."""
        comp = NoRollbackComponent("Listener")
        comp.initialize(t0=0.0)

        with pytest.raises(NotImplementedError):
            comp.snapshot_state()

    def test_restore_state_not_implemented(self):
        """Test restore_state raises NotImplementedError for non-rollback component."""
        comp = NoRollbackComponent("Listener")
        comp.initialize(t0=0.0)

        with pytest.raises(NotImplementedError):
            comp.restore_state({}, t=0.0)
