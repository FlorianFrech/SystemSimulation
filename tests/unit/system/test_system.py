"""
Unit tests for syssimx.system.system

Tests the System class in isolation using mock components.
"""

import pytest

from syssimx.system import Connection, System
from tests.fixtures.components import SimpleGain


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
