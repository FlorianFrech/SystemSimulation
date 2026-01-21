"""
Integration tests for syssimx.system.algorithms

Tests algorithm correctness against analytical solutions and compares
algorithm behavior on systems with algebraic loops.
"""

import numpy as np
import pytest

from syssimx.system import Connection, System
from syssimx.system.algorithms.gauss_seidel import GaussSeidelAlgorithm
from syssimx.system.algorithms.ijcsa import IJCSAAlgorithm
from tests.fixtures.components import (
    ConstantSource,
    SimpleGain,
)


# ============================================================================
# Test Algebraic Loop Convergence
# ============================================================================
class TestAlgebraicLoopConvergence:
    """
    Test algorithm convergence for algebraic loops.

    System: Two gains in feedback
    GainA: yA = kA * uA
    GainB: yB = kB * uB

    Connections:
    - yA -> uB
    - yB -> uA

    Fixed point equation:
    yA = kA * kB * yA
    => (1 - kA * kB) * yA = 0
    => yA = 0 (for kA * kB != 1)
    """

    @pytest.fixture
    def algebraic_loop_system(self):
        """Create algebraic loop system."""
        sys = System(name="AlgebraicLoop")

        gain_a = SimpleGain(name="GainA", gain=0.5)
        gain_b = SimpleGain(name="GainB", gain=0.5)

        sys.add_component(gain_a)
        sys.add_component(gain_b)

        sys.add_connection(Connection("GainA", "y", "GainB", "u"))
        sys.add_connection(Connection("GainB", "y", "GainA", "u"))

        return sys, gain_a, gain_b

    def test_gauss_seidel_convergence(self, algebraic_loop_system):
        """Test Gauss-Seidel converges to fixed point."""
        sys, gain_a, gain_b = algebraic_loop_system
        alg = GaussSeidelAlgorithm()
        sys.set_algorithm(alg)
        sys.initialize(t0=0.0)

        # Step forward
        alg.step(sys, t=0.0, dt=0.1)

        ya = gain_a.outputs["y"].get()
        yb = gain_b.outputs["y"].get()

        # Fixed point is (0, 0)
        assert np.isclose(ya, 0.0, atol=1e-6)
        assert np.isclose(yb, 0.0, atol=1e-6)

    def test_ijcsa_convergence(self, algebraic_loop_system):
        """Test IJCSA converges to fixed point."""
        sys, gain_a, gain_b = algebraic_loop_system
        alg = IJCSAAlgorithm(max_iter=100, tol=1e-10)
        sys.set_algorithm(alg)
        sys.initialize(t0=0.0)

        # Step forward
        alg.step(sys, t=0.0, dt=0.1)

        ya = gain_a.outputs["y"].get()
        yb = gain_b.outputs["y"].get()

        # Fixed point is (0, 0)
        assert np.isclose(ya, 0.0, atol=1e-10)
        assert np.isclose(yb, 0.0, atol=1e-10)


# ============================================================================
# Test Algebraic Loop with External Input
# ============================================================================
class TestAlgebraicLoopWithInput:
    """
    Test algebraic loop with external driving input.

    System:
    Source(1.0) -> GainA(0.5) <-> GainB(0.5) -> Sink

    With Subtractor to combine source and feedback:
    Source(1.0) -> Subtractor.pos
    GainB.y -> Subtractor.neg
    Subtractor.diff -> GainA.u -> GainB.u

    Fixed point: yA = 0.5 * (1 - yB) = 0.5 * (1 - 0.5 * yA)
    => yA = 0.5 - 0.25 * yA
    => 1.25 * yA = 0.5
    => yA = 0.4, yB = 0.2
    """

    @pytest.fixture
    def driven_loop_system(self):
        """Create algebraic loop with external driver."""
        from tests.fixtures.components.basic_components import Subtractor

        sys = System(name="DrivenLoop")

        source = ConstantSource(name="Source", value=1.0)
        subtractor = Subtractor(name="Sub")
        gain_a = SimpleGain(name="GainA", gain=0.5)
        gain_b = SimpleGain(name="GainB", gain=0.5)

        sys.add_component(source)
        sys.add_component(subtractor)
        sys.add_component(gain_a)
        sys.add_component(gain_b)

        # Source -> Subtractor.pos
        sys.add_connection(Connection("Source", "y", "Sub", "pos"))
        # Subtractor.diff -> GainA.u
        sys.add_connection(Connection("Sub", "diff", "GainA", "u"))
        # GainA.y -> GainB.u
        sys.add_connection(Connection("GainA", "y", "GainB", "u"))
        # GainB.y -> Subtractor.neg (feedback)
        sys.add_connection(Connection("GainB", "y", "Sub", "neg"))

        return sys, source, subtractor, gain_a, gain_b

    def test_driven_loop_gauss_seidel(self, driven_loop_system):
        """Test Gauss-Seidel solves driven algebraic loop."""
        sys, source, subtractor, gain_a, gain_b = driven_loop_system
        alg = GaussSeidelAlgorithm()
        sys.set_algorithm(alg)
        sys.initialize(t0=0.0)

        # Step forward multiple times to converge
        for _ in range(10):
            alg.step(sys, t=0.0, dt=0.1)

        ya = gain_a.outputs["y"].get()
        yb = gain_b.outputs["y"].get()

        # Expected: yA = 0.4, yB = 0.2
        assert np.isclose(ya, 0.4, rtol=1e-3), f"GainA output: {ya}, expected 0.4"
        assert np.isclose(yb, 0.2, rtol=1e-3), f"GainB output: {yb}, expected 0.2"

    def test_driven_loop_ijcsa(self, driven_loop_system):
        """Test IJCSA solves driven algebraic loop."""
        sys, source, subtractor, gain_a, gain_b = driven_loop_system
        alg = IJCSAAlgorithm(max_iter=100, tol=1e-10)
        sys.set_algorithm(alg)
        sys.initialize(t0=0.0)

        # IJCSA should converge in single step
        alg.step(sys, t=0.0, dt=0.1)

        ya = gain_a.outputs["y"].get()
        yb = gain_b.outputs["y"].get()

        # Expected: yA = 0.4, yB = 0.2
        assert np.isclose(ya, 0.4, rtol=1e-6), f"GainA output: {ya}, expected 0.4"
        assert np.isclose(yb, 0.2, rtol=1e-6), f"GainB output: {yb}, expected 0.2"
