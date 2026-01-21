"""
Unit tests for syssimx.system.algorithms

Tests the co-simulation algorithms (Jacobi, Gauss-Seidel, IJCSA) in isolation
using simple component configurations.
"""

import numpy as np
import pytest

from syssimx.system import Connection, System
from syssimx.system.algorithms.base import Algorithm
from syssimx.system.algorithms.gauss_seidel import GaussSeidelAlgorithm
from syssimx.system.algorithms.ijcsa import IJCSAAlgorithm
from syssimx.system.algorithms.jacobi import JacobiAlgorithm
from tests.fixtures.components import ConstantSource, IntegratorComponent, SimpleGain


# ============================================================================
# Test Algorithm Base Class and Interface
# ============================================================================
class TestAlgorithmInterface:
    """Test algorithm base class and interface compliance."""

    def test_jacobi_is_algorithm(self):
        """Test that JacobiAlgorithm implements Algorithm interface."""
        alg = JacobiAlgorithm()
        assert isinstance(alg, Algorithm)
        assert hasattr(alg, "step")
        assert hasattr(alg, "name")

    def test_gauss_seidel_is_algorithm(self):
        """Test that GaussSeidelAlgorithm implements Algorithm interface."""
        alg = GaussSeidelAlgorithm()
        assert isinstance(alg, Algorithm)
        assert hasattr(alg, "step")
        assert hasattr(alg, "name")

    def test_ijcsa_is_algorithm(self):
        """Test that IJCSAAlgorithm implements Algorithm interface."""
        alg = IJCSAAlgorithm()
        assert isinstance(alg, Algorithm)
        assert hasattr(alg, "step")
        assert hasattr(alg, "name")

    def test_algorithm_names(self):
        """Test that algorithms have distinct names."""
        jacobi = JacobiAlgorithm()
        gauss_seidel = GaussSeidelAlgorithm()
        ijcsa = IJCSAAlgorithm()

        assert jacobi.name == "Jacobi"
        assert gauss_seidel.name == "Gauss-Seidel"
        assert ijcsa.name == "IJCSA"

    def test_ijcsa_parameters(self):
        """Test IJCSA algorithm configurable parameters."""
        alg = IJCSAAlgorithm(max_iter=100, tol=1e-8)

        assert alg.max_iter == 100
        assert alg.tol == 1e-8

    def test_ijcsa_default_parameters(self):
        """Test IJCSA algorithm default parameters."""
        alg = IJCSAAlgorithm()

        assert alg.max_iter == 50
        assert alg.tol == 1e-6


# ============================================================================
# Test Algorithms with Single Component (Baseline)
# ============================================================================
class TestAlgorithmsSingleComponent:
    """Test algorithms with a single component - baseline correctness."""

    @pytest.fixture
    def single_integrator_system(self):
        """Create a system with a single integrator."""
        sys = System(name="SingleIntegrator")
        integrator = IntegratorComponent(name="Integrator", x0=0.0)
        sys.add_component(integrator)
        return sys, integrator

    @pytest.mark.parametrize(
        "algorithm",
        [JacobiAlgorithm(), GaussSeidelAlgorithm(), IJCSAAlgorithm()],
        ids=["Jacobi", "GaussSeidel", "IJCSA"],
    )
    def test_single_integrator_step(self, single_integrator_system: System, algorithm: Algorithm):
        """Test that all algorithms produce correct result for single integrator."""
        sys, integrator = single_integrator_system
        sys.set_algorithm(algorithm)
        sys.initialize(t0=0.0)

        # Set constant input u = 1.0
        integrator.set_inputs({"u": 1.0}, t=0.0)

        # Step forward dt = 0.1
        algorithm.step(sys, t=0.0, dt=0.1)

        # Expected: y = x0 + u * dt = 0 + 1.0 * 0.1 = 0.1
        y = integrator.outputs["y"].get()
        assert np.isclose(y, 0.1, rtol=1e-10)

    @pytest.mark.parametrize(
        "algorithm",
        [JacobiAlgorithm(), GaussSeidelAlgorithm(), IJCSAAlgorithm()],
        ids=["Jacobi", "GaussSeidel", "IJCSA"],
    )
    def test_single_integrator_multiple_steps(
        self, single_integrator_system: System, algorithm: Algorithm
    ):
        """Test multiple steps with all algorithms."""
        sys, integrator = single_integrator_system
        sys.set_algorithm(algorithm)
        sys.initialize(t0=0.0)

        # Set constant input u = 2.0
        integrator.set_inputs({"u": 2.0}, t=0.0)

        # Take 10 steps of dt = 0.1
        dt = 0.1
        for i in range(10):
            algorithm.step(sys, t=i * dt, dt=dt)

        # Expected: y = x0 + u * t = 0 + 2.0 * 1.0 = 2.0
        y = integrator.outputs["y"].get()
        assert np.isclose(y, 2.0, rtol=1e-10)


# ============================================================================
# Test Algorithms with Chain Topology (No Algebraic Loops)
# ============================================================================
class TestAlgorithmsChainTopology:
    """Test algorithms with chain topology - input propagation order."""

    @pytest.fixture
    def source_integrator_chain(self):
        """Create Source -> Integrator chain."""
        sys = System(name="SourceIntegratorChain")

        source = ConstantSource(name="Source", value=1.0)
        integrator = IntegratorComponent(name="Integrator", x0=0.0)

        sys.add_component(source)
        sys.add_component(integrator)
        sys.add_connection(Connection("Source", "y", "Integrator", "u"))

        return sys, source, integrator

    @pytest.mark.parametrize(
        "algorithm",
        [JacobiAlgorithm(), GaussSeidelAlgorithm(), IJCSAAlgorithm()],
        ids=["Jacobi", "GaussSeidel", "IJCSA"],
    )
    def test_chain_input_propagation(self, source_integrator_chain, algorithm):
        """Test that input is propagated correctly through chain."""
        sys, source, integrator = source_integrator_chain
        sys.set_algorithm(algorithm)
        sys.initialize(t0=0.0)

        # Step forward
        dt = 0.1
        algorithm.step(sys, t=0.0, dt=dt)

        # Source outputs 1.0, integrator should have y = 0 + 1.0 * 0.1 = 0.1
        y = integrator.outputs["y"].get()
        assert np.isclose(y, 0.1, rtol=1e-10)

    @pytest.fixture
    def gain_chain_with_source(self):
        """Create Source -> Gain -> Gain -> Gain chain."""
        sys = System(name="GainChain")

        source = ConstantSource(name="Source", value=1.0)
        gain1 = SimpleGain(name="Gain1", gain=2.0)
        gain2 = SimpleGain(name="Gain2", gain=3.0)
        gain3 = SimpleGain(name="Gain3", gain=0.5)

        sys.add_component(source)
        sys.add_component(gain1)
        sys.add_component(gain2)
        sys.add_component(gain3)
        sys.add_connection(Connection("Source", "y", "Gain1", "u"))
        sys.add_connection(Connection("Gain1", "y", "Gain2", "u"))
        sys.add_connection(Connection("Gain2", "y", "Gain3", "u"))

        return sys, source, gain1, gain2, gain3

    @pytest.mark.parametrize(
        "algorithm",
        [GaussSeidelAlgorithm()],
        ids=["GaussSeidel"],
    )
    def test_gain_chain_propagation(self, gain_chain_with_source, algorithm):
        """Test signal propagation through gain chain with Gauss-Seidel."""
        sys, source, gain1, gain2, gain3 = gain_chain_with_source
        sys.set_algorithm(algorithm)
        sys.initialize(t0=0.0)

        # Step forward - Gauss-Seidel should propagate within same step
        algorithm.step(sys, t=0.0, dt=0.1)

        # Expected: 1.0 * 2.0 * 3.0 * 0.5 = 3.0
        y3 = gain3.outputs["y"].get()
        assert np.isclose(y3, 3.0, rtol=1e-10)


# ============================================================================
# Test Algorithms with Feedback Loop (Integrator breaks algebraic loop)
# ============================================================================
class TestAlgorithmsFeedbackLoop:
    """Test algorithms with feedback loop broken by integrator."""

    @pytest.fixture
    def feedback_system(self):
        """
        Create feedback system: Gain -> Integrator -> (feedback to Gain)

        This is NOT an algebraic loop because integrator has no direct feedthrough.
        The integrator's output at time t does not depend on its input at time t.
        """
        sys = System(name="FeedbackLoop")

        gain = SimpleGain(name="Gain", gain=-0.5)  # Negative for stability
        integrator = IntegratorComponent(name="Integrator", x0=1.0)  # Start at 1.0

        sys.add_component(gain)
        sys.add_component(integrator)

        # Gain output -> Integrator input
        sys.add_connection(Connection("Gain", "y", "Integrator", "u"))
        # Integrator output -> Gain input (feedback)
        sys.add_connection(Connection("Integrator", "y", "Gain", "u"))

        return sys, gain, integrator

    def test_feedback_no_algebraic_loop(self, feedback_system):
        """Test that integrator breaks the algebraic loop."""
        sys, gain, integrator = feedback_system
        sys.build_graphs()

        # Should have NO algebraic loops (integrator has no direct feedthrough)
        assert len(sys.algebraic_loops) == 0

    @pytest.mark.parametrize(
        "algorithm",
        [JacobiAlgorithm(), GaussSeidelAlgorithm(), IJCSAAlgorithm()],
        ids=["Jacobi", "GaussSeidel", "IJCSA"],
    )
    def test_feedback_stability(self, feedback_system, algorithm):
        """Test feedback system stability with all algorithms."""
        sys, gain, integrator = feedback_system
        sys.set_algorithm(algorithm)
        sys.initialize(t0=0.0)

        # Run for many steps
        dt = 0.1
        for i in range(100):
            algorithm.step(sys, t=i * dt, dt=dt)

        # System should decay toward 0 (stable feedback with gain < 1)
        y = integrator.outputs["y"].get()
        assert np.isfinite(y)
        # After 10 time units with gain=-0.5, should be decaying
        assert abs(y) < 1.0  # Should have decayed from initial value of 1.0


# ============================================================================
# Test Algorithms with Algebraic Loop (Gain Feedback)
# ============================================================================
class TestAlgorithmsAlgebraicLoop:
    """Test algorithms with true algebraic loop (gain feedback)."""

    @pytest.fixture
    def algebraic_loop_system(self):
        """
        Create algebraic loop: GainA <-> GainB (both have direct feedthrough)

        GainA: y = 0.5 * u
        GainB: y = 0.5 * u

        Combined: yA = 0.5 * yB, yB = 0.5 * yA
        Solution: yA = yB = 0
        """
        sys = System(name="AlgebraicLoop")

        gain_a = SimpleGain(name="GainA", gain=0.5)
        gain_b = SimpleGain(name="GainB", gain=0.5)

        sys.add_component(gain_a)
        sys.add_component(gain_b)

        sys.add_connection(Connection("GainA", "y", "GainB", "u"))
        sys.add_connection(Connection("GainB", "y", "GainA", "u"))

        return sys, gain_a, gain_b

    def test_algebraic_loop_detected(self, algebraic_loop_system):
        """Test that algebraic loop is detected."""
        sys, gain_a, gain_b = algebraic_loop_system
        sys.build_graphs()

        assert len(sys.algebraic_loops) == 1
        assert set(sys.algebraic_loops[0]) == {"GainA", "GainB"}

    def test_gauss_seidel_solves_algebraic_loop(self, algebraic_loop_system):
        """Test that Gauss-Seidel solves the algebraic loop."""
        sys, gain_a, gain_b = algebraic_loop_system
        alg = GaussSeidelAlgorithm()
        sys.set_algorithm(alg)
        sys.initialize(t0=0.0)

        # Step forward
        alg.step(sys, t=0.0, dt=0.1)

        # Both outputs should converge to 0 (the only fixed point)
        ya = gain_a.outputs["y"].get()
        yb = gain_b.outputs["y"].get()

        assert np.isclose(ya, 0.0, atol=1e-6)
        assert np.isclose(yb, 0.0, atol=1e-6)

    def test_ijcsa_solves_algebraic_loop(self, algebraic_loop_system):
        """Test that IJCSA solves the algebraic loop."""
        sys, gain_a, gain_b = algebraic_loop_system
        alg = IJCSAAlgorithm(max_iter=100, tol=1e-8)
        sys.set_algorithm(alg)
        sys.initialize(t0=0.0)

        # Step forward
        alg.step(sys, t=0.0, dt=0.1)

        # Both outputs should converge to 0
        ya = gain_a.outputs["y"].get()
        yb = gain_b.outputs["y"].get()

        assert np.isclose(ya, 0.0, atol=1e-6)
        assert np.isclose(yb, 0.0, atol=1e-6)


# ============================================================================
# Test Algorithm Equivalence on Simple Systems
# ============================================================================
class TestAlgorithmEquivalence:
    """Test that algorithms produce equivalent results on simple systems."""

    def test_algorithms_equivalent_on_chain(self):
        """Test that all algorithms produce equivalent results on a chain."""
        dt = 0.1
        t_end = 1.0

        results = {}
        for alg_cls, name in [
            (JacobiAlgorithm, "Jacobi"),
            (GaussSeidelAlgorithm, "GaussSeidel"),
            (IJCSAAlgorithm, "IJCSA"),
        ]:
            # Create fresh system for each algorithm
            sys = System(name=f"Chain_{name}")
            source = ConstantSource(name="Source", value=1.0)
            integrator = IntegratorComponent(name="Integrator", x0=0.0)

            sys.add_component(source)
            sys.add_component(integrator)
            sys.add_connection(Connection("Source", "y", "Integrator", "u"))

            alg = alg_cls()
            sys.set_algorithm(alg)
            sys.initialize(t0=0.0)

            # Run simulation
            t = 0.0
            while t < t_end - 1e-12:
                alg.step(sys, t=t, dt=dt)
                t += dt

            results[name] = integrator.outputs["y"].get()

        # All algorithms should produce same result
        # Expected: y = 1.0 * 1.0 = 1.0 (constant input integrated over 1 second)
        for name, y in results.items():
            assert np.isclose(y, 1.0, rtol=1e-6), f"{name} produced y={y}, expected 1.0"


# ============================================================================
# Test Edge Cases
# ============================================================================
class TestAlgorithmEdgeCases:
    """Test algorithm behavior in edge cases."""

    def test_empty_system(self):
        """Test algorithm with empty system (no components)."""
        sys = System(name="Empty")
        alg = GaussSeidelAlgorithm()
        sys.set_algorithm(alg)
        sys.initialize(t0=0.0)

        # Should not raise
        alg.step(sys, t=0.0, dt=0.1)

    def test_zero_dt(self):
        """Test algorithm with zero time step."""
        sys = System(name="ZeroDt")
        integrator = IntegratorComponent(name="Integrator", x0=1.0)
        sys.add_component(integrator)

        alg = GaussSeidelAlgorithm()
        sys.set_algorithm(alg)
        sys.initialize(t0=0.0)

        integrator.set_inputs({"u": 1.0}, t=0.0)

        # Step with dt=0 should not change state
        alg.step(sys, t=0.0, dt=0.0)

        y = integrator.outputs["y"].get()
        assert np.isclose(y, 1.0)  # Should remain at x0

    def test_very_small_dt(self):
        """Test algorithm with very small time step."""
        sys = System(name="SmallDt")
        integrator = IntegratorComponent(name="Integrator", x0=0.0)
        sys.add_component(integrator)

        alg = GaussSeidelAlgorithm()
        sys.set_algorithm(alg)
        sys.initialize(t0=0.0)

        integrator.set_inputs({"u": 1.0}, t=0.0)

        # Step with very small dt
        alg.step(sys, t=0.0, dt=1e-10)

        y = integrator.outputs["y"].get()
        assert np.isclose(y, 1e-10, rtol=1e-6)

    def test_parallel_independent_components(self):
        """Test algorithm with parallel independent components."""
        sys = System(name="Parallel")

        # Two independent integrators
        int1 = IntegratorComponent(name="Int1", x0=0.0)
        int2 = IntegratorComponent(name="Int2", x0=0.0)

        sys.add_component(int1)
        sys.add_component(int2)
        # No connections - completely independent

        alg = GaussSeidelAlgorithm()
        sys.set_algorithm(alg)
        sys.initialize(t0=0.0)

        int1.set_inputs({"u": 1.0}, t=0.0)
        int2.set_inputs({"u": 2.0}, t=0.0)

        alg.step(sys, t=0.0, dt=0.1)

        y1 = int1.outputs["y"].get()
        y2 = int2.outputs["y"].get()

        assert np.isclose(y1, 0.1)  # 0 + 1.0 * 0.1
        assert np.isclose(y2, 0.2)  # 0 + 2.0 * 0.1
