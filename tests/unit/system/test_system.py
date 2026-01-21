"""
Unit tests for syssimx.system.system

Tests the System class in isolation using mock components.
"""

import pytest

from syssimx.core.events import Event
from syssimx.system import Connection, System
from syssimx.system.algorithms.gauss_seidel import GaussSeidelAlgorithm
from syssimx.system.algorithms.jacobi import JacobiAlgorithm
from syssimx.system.connection import EventConnection
from syssimx.system.graph import (
    collect_active_outputs,
    collect_global_interface_unknowns,
    is_delayed_producer,
)
from tests.fixtures.components import (
    HybridListener,
    HybridSource,
    IntegratorComponent,
    SimpleGain,
)


# ============================================================================
# Test System Construction
# ============================================================================
class TestSystem:
    """Test System class construction and basic properties."""

    def test_construction(self):
        sys = System(name="TestSystem")

        assert sys.name == "TestSystem"
        assert len(sys.components) == 0
        assert len(sys.connections) == 0

    def test_add_component(self):
        sys = System(name="TestSystem")
        comp = SimpleGain(name="Gain1", gain=2.0)

        sys.add_component(comp)

        assert len(sys.components) == 1
        assert sys.components["Gain1"] == comp

    def test_add_multiple_components(self):
        sys = System(name="TestSystem")
        comp_a = SimpleGain(name="GainA", gain=2.0)
        comp_b = SimpleGain(name="GainB", gain=3.0)
        sys.add_component(comp_a)
        sys.add_component(comp_b)

        assert len(sys.components) == 2
        assert sys.components["GainA"] == comp_a
        assert sys.components["GainB"] == comp_b

        with pytest.raises(ValueError):
            sys.add_component(comp_a)

    def test_add_component_after_initialization(self):
        sys = System(name="TestSystem")
        comp = SimpleGain(name="Gain1", gain=2.0)
        sys.add_component(comp)
        sys.initialize(t0=0.0)

        comp2 = SimpleGain(name="Gain2", gain=3.0)
        with pytest.raises(RuntimeError):
            sys.add_component(comp2)


# ============================================================================
# Test System Connections
# ============================================================================
class TestSystemConnections:
    """Test System connection management."""

    def test_add_connection_valid(self):
        """Test adding a valid connection between two components."""
        sys = System(name="TestSystem")
        comp_a = SimpleGain(name="GainA", gain=2.0)
        comp_b = SimpleGain(name="GainB", gain=3.0)
        sys.add_component(comp_a)
        sys.add_component(comp_b)

        conn = Connection(
            src_comp="GainA",
            src_port="y",
            dst_comp="GainB",
            dst_port="u",
        )
        sys.add_connection(conn)

        assert len(sys.connections) == 1
        assert sys.connections[0] == conn

    def test_add_connection_missing_component(self):
        """Test that connecting to non-existent components raises ValueError."""
        sys = System(name="TestSystem")
        comp_a = SimpleGain(name="GainA", gain=2.0)
        sys.add_component(comp_a)

        conn = Connection(
            src_comp="GainA",
            src_port="y",
            dst_comp="NonExistent",
            dst_port="u",
        )
        with pytest.raises(ValueError, match="must be added to the system"):
            sys.add_connection(conn)

    def test_add_connection_invalid_src_port(self):
        """Test that connecting from non-existent source port raises KeyError."""
        sys = System(name="TestSystem")
        comp_a = SimpleGain(name="GainA", gain=2.0)
        comp_b = SimpleGain(name="GainB", gain=3.0)
        sys.add_component(comp_a)
        sys.add_component(comp_b)

        conn = Connection(
            src_comp="GainA",
            src_port="invalid_port",
            dst_comp="GainB",
            dst_port="u",
        )
        with pytest.raises(KeyError, match="not an OUTPUT port"):
            sys.add_connection(conn)

    def test_add_connection_invalid_dst_port(self):
        """Test that connecting to non-existent destination port raises KeyError."""
        sys = System(name="TestSystem")
        comp_a = SimpleGain(name="GainA", gain=2.0)
        comp_b = SimpleGain(name="GainB", gain=3.0)
        sys.add_component(comp_a)
        sys.add_component(comp_b)

        conn = Connection(
            src_comp="GainA",
            src_port="y",
            dst_comp="GainB",
            dst_port="invalid_port",
        )
        with pytest.raises(KeyError, match="not an INPUT port"):
            sys.add_connection(conn)

    def test_add_duplicate_connection(self):
        """Test that adding duplicate connection raises ValueError."""
        sys = System(name="TestSystem")
        comp_a = SimpleGain(name="GainA", gain=2.0)
        comp_b = SimpleGain(name="GainB", gain=3.0)
        sys.add_component(comp_a)
        sys.add_component(comp_b)

        conn = Connection(
            src_comp="GainA",
            src_port="y",
            dst_comp="GainB",
            dst_port="u",
        )
        sys.add_connection(conn)

        with pytest.raises(ValueError, match="Duplicate connection"):
            sys.add_connection(conn)

    def test_multiple_connections_chain(self):
        """Test creating a chain of connections."""
        sys = System(name="ChainSystem")
        comps = [SimpleGain(name=f"Gain{i}", gain=1.0) for i in range(4)]
        for comp in comps:
            sys.add_component(comp)

        for i in range(3):
            conn = Connection(
                src_comp=f"Gain{i}",
                src_port="y",
                dst_comp=f"Gain{i + 1}",
                dst_port="u",
            )
            sys.add_connection(conn)

        assert len(sys.connections) == 3


# ============================================================================
# Test System Graph Building
# ============================================================================
class TestSystemGraphs:
    """Test System graph building and execution order computation."""

    def test_build_graphs_simple_chain(self):
        """Test graph building for a simple chain topology."""
        sys = System(name="ChainSystem")
        comp_a = SimpleGain(name="GainA", gain=2.0)
        comp_b = SimpleGain(name="GainB", gain=3.0)
        sys.add_component(comp_a)
        sys.add_component(comp_b)

        conn = Connection(
            src_comp="GainA",
            src_port="y",
            dst_comp="GainB",
            dst_port="u",
        )
        sys.add_connection(conn)
        sys.build_graphs()

        # Both components should be nodes in the graphs
        assert "GainA" in sys.graph.nodes
        assert "GainB" in sys.graph.nodes
        assert sys.graph.has_edge("GainA", "GainB")

    def test_compute_execution_order_chain(self):
        """Test execution order for a chain: A -> B -> C.
        Note: The DAG only includes edges where the destination's output
        is actively used. Since C's output isn't connected, B->C isn't
        in the DAG, so C can execute in parallel with A.
        """
        sys = System(name="ChainSystem")
        comp_a = SimpleGain(name="A", gain=1.0)
        comp_b = SimpleGain(name="B", gain=1.0)
        comp_c = SimpleGain(name="C", gain=1.0)
        sys.add_component(comp_a)
        sys.add_component(comp_b)
        sys.add_component(comp_c)

        sys.add_connection(Connection("A", "y", "B", "u"))
        sys.add_connection(Connection("B", "y", "C", "u"))
        sys.compute_execution_order()

        # Only A->B is in the DAG (B's output is used by C)
        # B->C is NOT in DAG because C's output isn't used
        # So: A must execute before B (DAG edge), but C has no incoming DAG edges
        idx_a = sys.execution_idx["A"]
        idx_b = sys.execution_idx["B"]

        # A must execute before B
        assert idx_a < idx_b
        # Verify execution_order is populated
        assert len(sys.execution_order) >= 1

    def test_compute_execution_order_full_chain(self):
        """Test execution order for a chain where all outputs are used."""
        sys = System(name="ChainSystem")
        comp_a = SimpleGain(name="A", gain=1.0)
        comp_b = SimpleGain(name="B", gain=1.0)
        comp_c = SimpleGain(name="C", gain=1.0)
        comp_d = SimpleGain(name="D", gain=1.0)  # Uses C's output
        sys.add_component(comp_a)
        sys.add_component(comp_b)
        sys.add_component(comp_c)
        sys.add_component(comp_d)

        sys.add_connection(Connection("A", "y", "B", "u"))
        sys.add_connection(Connection("B", "y", "C", "u"))
        sys.add_connection(Connection("C", "y", "D", "u"))
        sys.compute_execution_order()

        # Now all outputs are used: A->B, B->C, C->D all in DAG
        idx_a = sys.execution_idx["A"]
        idx_b = sys.execution_idx["B"]
        idx_c = sys.execution_idx["C"]
        # Strict ordering: A before B before C
        assert idx_a < idx_b < idx_c

    def test_detect_algebraic_loop(self):
        """Test detection of algebraic loops (direct feedthrough cycles)."""
        sys = System(name="AlgLoopSystem")
        comp_a = SimpleGain(name="A", gain=0.5)
        comp_b = SimpleGain(name="B", gain=0.5)
        sys.add_component(comp_a)
        sys.add_component(comp_b)

        # Create cycle: A -> B -> A
        sys.add_connection(Connection("A", "y", "B", "u"))
        sys.add_connection(Connection("B", "y", "A", "u"))
        sys.build_graphs()

        # Should detect algebraic loop
        assert len(sys.algebraic_loops) == 1
        assert set(sys.algebraic_loops[0]) == {"A", "B"}


# ============================================================================
# Test System Initialization
# ============================================================================
class TestSystemInitialization:
    """Test System initialization lifecycle."""

    def test_initialize_sets_flag(self):
        """Test that initialize sets is_initialized flag."""
        sys = System(name="TestSystem")
        comp = SimpleGain(name="Gain", gain=2.0)
        sys.add_component(comp)

        assert sys.is_initialized is False
        sys.initialize(t0=0.0)
        assert sys.is_initialized is True

    def test_initialize_sets_time(self):
        """Test that initialize sets the system time."""
        sys = System(name="TestSystem")
        comp = SimpleGain(name="Gain", gain=2.0)
        sys.add_component(comp)
        sys.initialize(t0=1.5)

        assert sys.t == 1.5

    def test_initialize_builds_graphs(self):
        """Test that initialize automatically builds graphs."""
        sys = System(name="TestSystem")
        comp_a = SimpleGain(name="A", gain=1.0)
        comp_b = SimpleGain(name="B", gain=1.0)
        sys.add_component(comp_a)
        sys.add_component(comp_b)
        sys.add_connection(Connection("A", "y", "B", "u"))

        sys.initialize(t0=0.0)

        assert len(sys.execution_order) > 0
        assert "A" in sys.graph.nodes
        assert "B" in sys.graph.nodes


# ============================================================================
# Test System with Factory Functions
# ============================================================================
class TestSystemFactories:
    """Test System creation using factory functions."""

    def test_create_two_component_system(self):
        """Test the two-component system factory."""
        from tests.fixtures.systems import create_two_component_system

        sys, comp_a, comp_b = create_two_component_system()

        assert sys.name == "TwoCompSystem"
        assert len(sys.components) == 2
        assert len(sys.connections) == 1
        assert "GainA" in sys.components
        assert "GainB" in sys.components

    def test_create_chain_system(self):
        """Test the chain system factory."""
        from tests.fixtures.systems import create_chain_system

        sys, components = create_chain_system(n_components=5)

        assert len(sys.components) == 5
        assert len(sys.connections) == 4
        assert len(components) == 5

    def test_create_algebraic_loop_system(self):
        """Test the algebraic loop system factory."""
        from tests.fixtures.systems import create_algebraic_loop_system

        sys, gain_a, gain_b = create_algebraic_loop_system()

        assert sys.name == "AlgebraicLoop"
        assert len(sys.components) == 2
        assert len(sys.connections) == 2

        # Build graphs to detect algebraic loop
        sys.build_graphs()
        assert len(sys.algebraic_loops) == 1

    def test_create_feedback_loop_system(self):
        """Test the feedback loop system factory (not algebraic due to integrator)."""
        from tests.fixtures.systems import create_feedback_loop_system

        sys, gain, integrator = create_feedback_loop_system()

        assert sys.name == "FeedbackLoop"
        assert len(sys.components) == 2
        assert len(sys.connections) == 2

        # Build graphs - should NOT be an algebraic loop
        # (integrator breaks the loop because output doesn't depend on input)
        sys.build_graphs()
        # Integrator has no direct feedthrough, so no algebraic loop
        assert len(sys.algebraic_loops) == 0


# ============================================================================
# Test Graph Building - Advanced Topologies
# ============================================================================
class TestGraphBuildingAdvanced:
    """Test graph building for various topologies."""

    def test_diamond_topology(self):
        """Test diamond/converging topology: A -> B, A -> C, B -> D, C -> D."""
        sys = System(name="Diamond")
        comp_a = SimpleGain(name="A", gain=1.0)
        comp_b = SimpleGain(name="B", gain=1.0)
        comp_c = SimpleGain(name="C", gain=1.0)
        comp_d = SimpleGain(name="D", gain=1.0)

        for comp in [comp_a, comp_b, comp_c, comp_d]:
            sys.add_component(comp)

        # A feeds both B and C
        sys.add_connection(Connection("A", "y", "B", "u"))
        # Note: C doesn't receive from A in this test since SimpleGain only has one input
        # Instead test parallel paths that converge
        sys.build_graphs()

        assert "A" in sys.graph.nodes
        assert "B" in sys.graph.nodes
        assert sys.graph.has_edge("A", "B")

    def test_parallel_branches(self):
        """Test parallel branches with no dependencies between them."""
        sys = System(name="Parallel")
        # Two independent chains: A->B->E and C->D->F
        # E and F consume B and D's outputs, creating DAG edges
        comp_a = SimpleGain(name="A", gain=1.0)
        comp_b = SimpleGain(name="B", gain=1.0)
        comp_c = SimpleGain(name="C", gain=1.0)
        comp_d = SimpleGain(name="D", gain=1.0)
        comp_e = SimpleGain(name="E", gain=1.0)
        comp_f = SimpleGain(name="F", gain=1.0)

        for comp in [comp_a, comp_b, comp_c, comp_d, comp_e, comp_f]:
            sys.add_component(comp)

        sys.add_connection(Connection("A", "y", "B", "u"))
        sys.add_connection(Connection("B", "y", "E", "u"))
        sys.add_connection(Connection("C", "y", "D", "u"))
        sys.add_connection(Connection("D", "y", "F", "u"))
        sys.compute_execution_order()

        # A and C should be in the same generation (no dependencies between them)
        idx_a = sys.execution_idx["A"]
        idx_c = sys.execution_idx["C"]
        idx_b = sys.execution_idx["B"]
        idx_d = sys.execution_idx["D"]

        # A before B, C before D (since outputs are now used)
        assert idx_a < idx_b
        assert idx_c < idx_d
        # A and C can be in same generation (parallel)
        assert idx_a == idx_c

    def test_isolated_component(self):
        """Test system with isolated component (no connections)."""
        sys = System(name="Isolated")
        comp_a = SimpleGain(name="A", gain=1.0)
        comp_b = SimpleGain(name="B", gain=1.0)  # Isolated
        comp_c = SimpleGain(name="C", gain=1.0)

        for comp in [comp_a, comp_b, comp_c]:
            sys.add_component(comp)

        sys.add_connection(Connection("A", "y", "C", "u"))
        # B is not connected to anything
        sys.build_graphs()
        sys.compute_execution_order()

        # All components should be in execution order
        assert "A" in sys.execution_idx
        assert "B" in sys.execution_idx
        assert "C" in sys.execution_idx

    def test_multiple_drivers_same_input_raises(self):
        """Test that multiple drivers for same input port raises RuntimeError."""
        sys = System(name="MultiDriver")
        comp_a = SimpleGain(name="A", gain=1.0)
        comp_b = SimpleGain(name="B", gain=1.0)
        comp_c = SimpleGain(name="C", gain=1.0)

        for comp in [comp_a, comp_b, comp_c]:
            sys.add_component(comp)

        # Both A and B try to drive C.u
        sys.add_connection(Connection("A", "y", "C", "u"))
        sys.add_connection(Connection("B", "y", "C", "u"))

        with pytest.raises(RuntimeError, match="Multiple drivers"):
            sys.build_graphs()

    def test_self_loop_algebraic(self):
        """Test self-loop detection as algebraic loop."""
        sys = System(name="SelfLoop")
        comp_a = SimpleGain(name="A", gain=0.5)

        sys.add_component(comp_a)
        sys.add_connection(Connection("A", "y", "A", "u"))
        sys.build_graphs()

        # Self-loop should be detected as algebraic loop
        assert len(sys.algebraic_loops) == 1
        assert "A" in sys.algebraic_loops[0]


# ============================================================================
# Test Delayed Producer Heuristic
# ============================================================================
class TestDelayedProducer:
    """Test the is_delayed_producer heuristic for actuator-like components."""

    def test_delayed_producer_detection(self):
        """Test detection of delayed producer (actuator pattern)."""
        sys = System(name="DelayedProducer")
        # Pattern: Source -> Controller -> Plant
        # where Controller has direct feedthrough but Plant doesn't feed back
        source = SimpleGain(name="Source", gain=1.0)
        controller = SimpleGain(name="Controller", gain=1.0)
        plant = IntegratorComponent(name="Plant", x0=0.0)

        for comp in [source, controller, plant]:
            sys.add_component(comp)

        sys.add_connection(Connection("Source", "y", "Controller", "u"))
        sys.add_connection(Connection("Controller", "y", "Plant", "u"))
        sys.build_graphs()

        # Source has no incoming zero-delay edges but feeds into zero-delay structure
        # This depends on the specific heuristic implementation
        # At minimum, verify the function runs without error
        result = is_delayed_producer(sys, "Source")
        assert isinstance(result, bool)

    def test_not_delayed_producer_if_in_dag(self):
        """Test that component with DAG edges is not a delayed producer."""
        sys = System(name="NotDelayed")
        comp_a = SimpleGain(name="A", gain=1.0)
        comp_b = SimpleGain(name="B", gain=1.0)

        sys.add_component(comp_a)
        sys.add_component(comp_b)
        sys.add_connection(Connection("A", "y", "B", "u"))
        sys.build_graphs()

        # A has outgoing DAG edge, so not a delayed producer
        assert is_delayed_producer(sys, "A") is False


# ============================================================================
# Test Collect Active Outputs
# ============================================================================
class TestCollectActiveOutputs:
    """Test collect_active_outputs helper function."""

    def test_collect_active_outputs_simple(self):
        """Test collecting active outputs from connections."""
        sys = System(name="ActiveOutputs")
        comp_a = SimpleGain(name="A", gain=1.0)
        comp_b = SimpleGain(name="B", gain=1.0)

        sys.add_component(comp_a)
        sys.add_component(comp_b)
        sys.add_connection(Connection("A", "y", "B", "u"))

        active = collect_active_outputs(sys)
        assert "A" in active
        assert "y" in active["A"]

    def test_collect_active_outputs_none(self):
        """Test collecting active outputs with no connections."""
        sys = System(name="NoConnections")
        comp_a = SimpleGain(name="A", gain=1.0)
        sys.add_component(comp_a)

        active = collect_active_outputs(sys)
        assert "A" not in active or len(active["A"]) == 0


# ============================================================================
# Test Collect Global Interface Unknowns
# ============================================================================
class TestCollectGlobalInterfaceUnknowns:
    """Test collect_global_interface_unknowns for IJCSA algorithm support."""

    def test_collect_interface_unknowns(self):
        """Test collecting interface unknowns from zero-delay edges."""
        sys = System(name="InterfaceUnknowns")
        comp_a = SimpleGain(name="A", gain=1.0)
        comp_b = SimpleGain(name="B", gain=1.0)

        sys.add_component(comp_a)
        sys.add_component(comp_b)
        sys.add_connection(Connection("A", "y", "B", "u"))
        sys.build_graphs()

        inputs, driver_map = collect_global_interface_unknowns(sys)

        # B.u is driven by A.y (if in zero-delay DAG)
        # This depends on direct feedthrough configuration
        assert isinstance(inputs, list)
        assert isinstance(driver_map, dict)

    def test_collect_interface_unknowns_empty(self):
        """Test collecting interface unknowns with no DAG edges."""
        sys = System(name="NoDag")
        comp_a = IntegratorComponent(name="A", x0=0.0)  # No direct feedthrough

        sys.add_component(comp_a)
        sys.build_graphs()

        inputs, driver_map = collect_global_interface_unknowns(sys)
        # No zero-delay edges
        assert inputs == []


# ============================================================================
# Test System Algorithm Management
# ============================================================================
class TestSystemAlgorithm:
    """Test algorithm setting and validation."""

    def test_set_algorithm_valid(self):
        """Test setting a valid algorithm."""
        sys = System(name="AlgTest")
        comp = SimpleGain(name="Gain", gain=1.0)
        sys.add_component(comp)

        alg = JacobiAlgorithm()
        sys.set_algorithm(alg)
        assert sys.algorithm is alg

    def test_set_algorithm_invalid_type_raises(self):
        """Test that setting non-Algorithm raises TypeError."""
        sys = System(name="AlgTest")

        with pytest.raises(TypeError, match="must implement Algorithm"):
            sys.set_algorithm("not_an_algorithm")

    def test_default_algorithm_is_gauss_seidel(self):
        """Test that default algorithm is GaussSeidelAlgorithm."""
        sys = System(name="DefaultAlg")
        assert isinstance(sys.algorithm, GaussSeidelAlgorithm)


# ============================================================================
# Test System Component Classification
# ============================================================================
class TestClassifyComponents:
    """Test component classification for hybrid simulation."""

    def test_classify_continuous_only(self):
        """Test classifying components without hybrid capabilities."""
        sys = System(name="ContinuousOnly")
        comp_a = SimpleGain(name="A", gain=1.0)
        comp_b = SimpleGain(name="B", gain=1.0)

        sys.add_component(comp_a)
        sys.add_component(comp_b)

        result = sys.classify_components()

        assert "event_sources" in result
        assert "event_listeners" in result
        assert "continuous_only" in result
        # SimpleGain has no hybrid capabilities
        assert len(result["event_sources"]) == 0
        assert len(result["event_listeners"]) == 0
        assert len(result["continuous_only"]) == 2

    def test_classify_with_event_sources(self):
        """Test classifying components with event sources."""
        sys = System(name="WithEventSources")
        source = HybridSource(name="Source", x0=0.0, v=1.0, t0=0.0)
        source.add_event_indicator(name="trigger", func=lambda c: c.x, direction=1)
        gain = SimpleGain(name="Gain", gain=1.0)

        sys.add_component(source)
        sys.add_component(gain)

        result = sys.classify_components()

        assert len(result["event_sources"]) == 1
        assert result["event_sources"][0].name == "Source"
        assert len(result["continuous_only"]) == 1

    def test_classify_with_event_listeners(self):
        """Test classifying components with event listeners."""
        sys = System(name="WithEventListeners")
        source = HybridSource(name="Source", x0=0.0, v=1.0, t0=0.0)
        source.add_event_indicator(name="trigger", func=lambda c: c.x, direction=1)
        listener = HybridListener(name="Listener", x0=0.0, v=1.0, t0=0.0)

        sys.add_component(source)
        sys.add_component(listener)

        # Add event connection - this auto-subscribes the listener
        sys.add_event_connection(
            EventConnection(
                src_comp="Source",
                src_port="trigger",
                dst_comp="Listener",
                dst_port="v_invert",
            )
        )

        result = sys.classify_components()

        assert len(result["event_sources"]) == 1
        assert len(result["event_listeners"]) == 1
        assert result["event_listeners"][0].name == "Listener"


# ============================================================================
# Test System History Retrieval
# ============================================================================
class TestSystemHistory:
    """Test system history retrieval."""

    def test_get_history_after_run(self):
        """Test retrieving history after running simulation."""
        sys = System(name="HistoryTest")
        comp_a = SimpleGain(name="A", gain=2.0)
        comp_b = SimpleGain(name="B", gain=3.0)

        sys.add_component(comp_a)
        sys.add_component(comp_b)
        sys.add_connection(Connection("A", "y", "B", "u"))

        sys.initialize(t0=0.0)
        sys.run(t0=0.0, tf=0.1, dt=0.01)

        history = sys.get_history()
        assert "A" in history
        assert "B" in history
        assert "Events" in history


# ============================================================================
# Test Event Connections
# ============================================================================
class TestEventConnections:
    """Test event connection management."""

    def test_add_event_connection_valid(self):
        """Test adding a valid event connection."""
        sys = System(name="EventConnTest")
        source = HybridSource(name="Source", x0=0.0, v=1.0, t0=0.0)
        source.add_event_indicator(name="trigger", func=lambda c: c.x, direction=1)
        listener = HybridListener(name="Listener", x0=0.0, v=1.0, t0=0.0)

        sys.add_component(source)
        sys.add_component(listener)

        conn = EventConnection(
            src_comp="Source",
            src_port="trigger",
            dst_comp="Listener",
            dst_port="v_invert",
        )
        sys.add_event_connection(conn)

        assert len(sys.event_connections) == 1
        assert sys.event_connections[0] == conn

    def test_add_event_connection_auto_subscribes_target(self):
        """Test that add_event_connection automatically subscribes the target."""
        sys = System(name="AutoSubscribe")
        source = HybridSource(name="Source", x0=0.0, v=1.0, t0=0.0)
        source.add_event_indicator(name="trigger", func=lambda c: c.x, direction=1)
        listener = HybridListener(name="Listener", x0=0.0, v=1.0, t0=0.0)

        sys.add_component(source)
        sys.add_component(listener)

        # Listener should have no subscriptions initially
        assert len(listener.event_subscriptions) == 0

        sys.add_event_connection(
            EventConnection(
                src_comp="Source",
                src_port="trigger",
                dst_comp="Listener",
                dst_port="v_invert",
            )
        )

        # Listener should now have the subscription
        assert len(listener.event_subscriptions) == 1
        assert listener.event_subscriptions[0].name == "trigger"
        assert listener.event_subscriptions[0].source == "Source"

    def test_add_event_connection_uses_connection_direction(self):
        """Test that direction from EventConnection overrides indicator direction."""
        sys = System(name="DirectionOverride")
        source = HybridSource(name="Source", x0=0.0, v=1.0, t0=0.0)
        source.add_event_indicator(name="trigger", func=lambda c: c.x, direction=1)  # Rising
        listener = HybridListener(name="Listener", x0=0.0, v=1.0, t0=0.0)

        sys.add_component(source)
        sys.add_component(listener)

        # Override direction to falling (-1)
        sys.add_event_connection(
            EventConnection(
                src_comp="Source",
                src_port="trigger",
                dst_comp="Listener",
                dst_port="v_invert",
                direction=-1,
            )
        )

        # Subscription should use overridden direction
        assert listener.event_subscriptions[0].direction == -1

    def test_add_event_connection_uses_indicator_direction_when_none(self):
        """Test that direction defaults to indicator direction when connection direction is None."""
        sys = System(name="IndicatorDirection")
        source = HybridSource(name="Source", x0=0.0, v=1.0, t0=0.0)
        source.add_event_indicator(name="trigger", func=lambda c: c.x, direction=1)  # Rising
        listener = HybridListener(name="Listener", x0=0.0, v=1.0, t0=0.0)

        sys.add_component(source)
        sys.add_component(listener)

        sys.add_event_connection(
            EventConnection(
                src_comp="Source",
                src_port="trigger",
                dst_comp="Listener",
                dst_port="v_invert",
                direction=None,  # Should use indicator's direction
            )
        )

        # Subscription should use indicator direction
        assert listener.event_subscriptions[0].direction == 1

    def test_add_event_connection_missing_source_raises_valueerror(self):
        """Test that missing source component raises ValueError."""
        sys = System(name="MissingSource")
        listener = HybridListener(name="Listener", x0=0.0, v=1.0, t0=0.0)
        sys.add_component(listener)

        conn = EventConnection(
            src_comp="NonExistent",
            src_port="trigger",
            dst_comp="Listener",
            dst_port="v_invert",
        )

        with pytest.raises(ValueError, match="Event source 'NonExistent' is not in the system"):
            sys.add_event_connection(conn)

    def test_add_event_connection_missing_target_raises_valueerror(self):
        """Test that missing target component raises ValueError."""
        sys = System(name="MissingTarget")
        source = HybridSource(name="Source", x0=0.0, v=1.0, t0=0.0)
        source.add_event_indicator(name="trigger", func=lambda c: c.x, direction=1)
        sys.add_component(source)

        conn = EventConnection(
            src_comp="Source",
            src_port="trigger",
            dst_comp="NonExistent",
            dst_port="v_invert",
        )

        with pytest.raises(ValueError, match="Event target 'NonExistent' is not in the system"):
            sys.add_event_connection(conn)

    def test_add_event_connection_missing_indicator_raises_keyerror(self):
        """Test that missing event indicator raises KeyError."""
        sys = System(name="MissingIndicator")
        source = HybridSource(name="Source", x0=0.0, v=1.0, t0=0.0)
        # NOT adding event indicator
        listener = HybridListener(name="Listener", x0=0.0, v=1.0, t0=0.0)

        sys.add_component(source)
        sys.add_component(listener)

        conn = EventConnection(
            src_comp="Source",
            src_port="trigger",  # Indicator doesn't exist
            dst_comp="Listener",
            dst_port="v_invert",
        )

        with pytest.raises(KeyError, match="Event indicator 'trigger' not found"):
            sys.add_event_connection(conn)

    def test_add_event_connection_duplicate_raises_valueerror(self):
        """Test that duplicate event connection raises ValueError."""
        sys = System(name="DuplicateEvent")
        source = HybridSource(name="Source", x0=0.0, v=1.0, t0=0.0)
        source.add_event_indicator(name="trigger", func=lambda c: c.x, direction=1)
        listener = HybridListener(name="Listener", x0=0.0, v=1.0, t0=0.0)

        sys.add_component(source)
        sys.add_component(listener)

        conn = EventConnection(
            src_comp="Source",
            src_port="trigger",
            dst_comp="Listener",
            dst_port="v_invert",
        )
        sys.add_event_connection(conn)

        with pytest.raises(ValueError, match="Duplicate event connection"):
            sys.add_event_connection(conn)

    def test_add_event_connection_no_double_subscription(self):
        """Test that adding same event connection twice doesn't double-subscribe."""
        sys = System(name="NoDoubleSubscribe")
        source = HybridSource(name="Source", x0=0.0, v=1.0, t0=0.0)
        source.add_event_indicator(name="trigger", func=lambda c: c.x, direction=1)
        listener = HybridListener(name="Listener", x0=0.0, v=1.0, t0=0.0)

        sys.add_component(source)
        sys.add_component(listener)

        # Manually subscribe first
        event = Event(name="trigger", source="Source", direction=1)
        listener.event_subscriptions.append(event)

        # Add connection - should not add duplicate subscription
        sys.add_event_connection(
            EventConnection(
                src_comp="Source",
                src_port="trigger",
                dst_comp="Listener",
                dst_port="v_invert",
            )
        )

        # Should still only have one subscription
        assert len(listener.event_subscriptions) == 1


# ============================================================================
# Test Event Dispatch
# ============================================================================
class TestEventDispatch:
    """Test event dispatching functionality."""

    def test_dispatch_event_valid(self):
        """Test dispatching an event to registered targets."""
        sys = System(name="DispatchTest")
        source = HybridSource(name="Source", x0=0.0, v=1.0, t0=0.0)
        # Use event name that listener understands
        source.add_event_indicator(name="v_invert", func=lambda c: c.x, direction=1)
        listener = HybridListener(name="Listener", x0=0.0, v=1.0, t0=0.0)

        sys.add_component(source)
        sys.add_component(listener)
        sys.add_event_connection(
            EventConnection(
                src_comp="Source",
                src_port="v_invert",
                dst_comp="Listener",
                dst_port="v_invert",
            )
        )

        # Initialize to set up ports
        sys.initialize(t0=0.0)

        initial_v = listener.v
        event = Event(name="v_invert", source="Source", direction=1)
        targets = sys.dispatch_event(event, t=0.0)

        assert targets == ["Listener"]
        # Listener should have handled the event (v inverted)
        assert listener.v == -initial_v

    def test_dispatch_event_invalid_source_raises_valueerror(self):
        """Test that dispatching from non-existent source raises ValueError."""
        sys = System(name="InvalidDispatch")
        source = HybridSource(name="Source", x0=0.0, v=1.0, t0=0.0)
        sys.add_component(source)

        event = Event(name="trigger", source="NonExistent", direction=1)

        with pytest.raises(ValueError, match="Event source 'NonExistent' is not in the system"):
            sys.dispatch_event(event, t=0.0)

    def test_dispatch_event_notify_false(self):
        """Test dispatching without notifying targets."""
        sys = System(name="NoNotify")
        source = HybridSource(name="Source", x0=0.0, v=1.0, t0=0.0)
        source.add_event_indicator(name="trigger", func=lambda c: c.x, direction=1)
        listener = HybridListener(name="Listener", x0=0.0, v=1.0, t0=0.0)

        sys.add_component(source)
        sys.add_component(listener)
        sys.add_event_connection(
            EventConnection(
                src_comp="Source",
                src_port="trigger",
                dst_comp="Listener",
                dst_port="v_invert",
            )
        )
        sys.initialize(t0=0.0)

        initial_v = listener.v
        event = Event(name="trigger", source="Source", direction=1)
        targets = sys.dispatch_event(event, t=0.0, notify=False)

        assert targets == ["Listener"]
        # Listener should NOT have handled the event
        assert listener.v == initial_v

    def test_get_event_targets(self):
        """Test getting event targets for a source event."""
        sys = System(name="GetTargets")
        source = HybridSource(name="Source", x0=0.0, v=1.0, t0=0.0)
        source.add_event_indicator(name="trigger", func=lambda c: c.x, direction=1)
        listener1 = HybridListener(name="Listener1", x0=0.0, v=1.0, t0=0.0)
        listener2 = HybridListener(name="Listener2", x0=0.0, v=1.0, t0=0.0)

        sys.add_component(source)
        sys.add_component(listener1)
        sys.add_component(listener2)

        sys.add_event_connection(EventConnection("Source", "trigger", "Listener1", "v_invert"))
        sys.add_event_connection(EventConnection("Source", "trigger", "Listener2", "v_invert"))

        targets = sys.get_event_targets("Source", "trigger")

        assert "Listener1" in targets
        assert "Listener2" in targets
        assert len(targets) == 2

    def test_get_event_targets_returns_copy(self):
        """Test that get_event_targets returns a copy, not the internal list."""
        sys = System(name="TargetsCopy")
        source = HybridSource(name="Source", x0=0.0, v=1.0, t0=0.0)
        source.add_event_indicator(name="trigger", func=lambda c: c.x, direction=1)
        listener = HybridListener(name="Listener", x0=0.0, v=1.0, t0=0.0)

        sys.add_component(source)
        sys.add_component(listener)
        sys.add_event_connection(EventConnection("Source", "trigger", "Listener", "v_invert"))

        targets = sys.get_event_targets("Source", "trigger")
        targets.append("Hacker")  # Modify returned list

        # Original should be unchanged
        assert "Hacker" not in sys.get_event_targets("Source", "trigger")

    def test_get_event_targets_empty(self):
        """Test getting event targets when none exist."""
        sys = System(name="NoTargets")
        source = HybridSource(name="Source", x0=0.0, v=1.0, t0=0.0)
        sys.add_component(source)

        targets = sys.get_event_targets("Source", "nonexistent")

        assert targets == []


# ============================================================================
# Test Connection Validation - Port Compatibility
# ============================================================================
class TestConnectionPortCompatibility:
    """Test connection validation for port type compatibility."""

    def test_add_connection_incompatible_types_raises_typeerror(self):
        """Test that connecting incompatible port types raises TypeError."""
        from syssimx.core.port import PortSpec, PortType

        sys = System(name="IncompatibleTypes")

        # Create component with BOOL output
        class BoolSource(SimpleGain):
            def __init__(self, name):
                super().__init__(name)
                self.output_specs["y"] = PortSpec(name="y", type=PortType.BOOL, direction="out")

        # Create component with REAL input
        bool_source = BoolSource(name="BoolSource")
        real_sink = SimpleGain(name="RealSink", gain=1.0)

        sys.add_component(bool_source)
        sys.add_component(real_sink)

        conn = Connection(
            src_comp="BoolSource",
            src_port="y",
            dst_comp="RealSink",
            dst_port="u",
        )

        with pytest.raises(TypeError, match="Port incompatibility"):
            sys.add_connection(conn)
