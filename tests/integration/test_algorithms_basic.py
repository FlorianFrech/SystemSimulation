"""
Integration tests for syssimx.system.algorithms

Tests algorithm correctness against analytical solutions and compares
algorithm behavior on systems with algebraic loops.
"""

from typing import Any

import numpy as np
import pytest

from syssimx.core.base import CoSimComponent
from syssimx.core.port import PortSpec, PortType
from syssimx.system import Connection, System
from syssimx.system.algorithms.gauss_seidel import GaussSeidelAlgorithm
from syssimx.system.algorithms.ijcsa import IJCSAAlgorithm
from syssimx.system.algorithms.jacobi import JacobiAlgorithm
from tests.fixtures.components import IntegratorComponent, SimpleGain, SineSource, ConstantSource, LinearSource


# ============================================================================
# Test Analytical Accuracy - Constant Input
# ============================================================================
class TestAnalyticalAccuracyConstant:
    """
    Test algorithm accuracy against analytical solution for constant input.

    System: Source(1.0) -> Integrator(x0=0)
    Analytical solution: y(t) = 1.0 * t
    """

    @pytest.fixture
    def constant_input_system(self):
        """Create system with constant input to integrator."""
        sys = System(name="ConstantInput")
        source = ConstantSource(name="Source", value=1.0)
        integrator = IntegratorComponent(name="Integrator", x0=0.0)

        sys.add_component(source)
        sys.add_component(integrator)
        sys.add_connection(Connection("Source", "y", "Integrator", "u"))

        return sys, integrator

    @pytest.mark.parametrize("dt", [0.1, 0.01, 0.001])
    @pytest.mark.parametrize(
        "algorithm_cls",
        [JacobiAlgorithm, GaussSeidelAlgorithm, IJCSAAlgorithm],
        ids=["Jacobi", "GaussSeidel", "IJCSA"],
    )
    def test_constant_input_accuracy(self, constant_input_system, algorithm_cls, dt):
        """Test accuracy of integration with constant input."""
        sys, integrator = constant_input_system
        t_end = 1.0

        alg = algorithm_cls()
        sys.set_algorithm(alg)
        sys.initialize(t0=0.0)

        # Run simulation
        t = 0.0
        while t < t_end - 1e-12:
            step_dt = min(dt, t_end - t)
            alg.step(sys, t=t, dt=step_dt)
            t += step_dt

        # Analytical solution: y(t) = 1.0 * t = 1.0
        y_computed = integrator.outputs["y"].get()
        y_analytical = 1.0

        # Tolerance depends on step size (Euler method is O(dt))
        assert np.isclose(y_computed, y_analytical, rtol=dt), (
            f"{alg.name} with dt={dt}: y={y_computed}, expected {y_analytical}"
        )


# ============================================================================
# Test Analytical Accuracy - Linear Input
# ============================================================================
class TestAnalyticalAccuracyLinear:
    """
    Test algorithm accuracy against analytical solution for linear input.

    System: LinearSource(slope=1, offset=0) -> Integrator(x0=0)
    Input: u(t) = t
    Analytical solution: y(t) = ∫ t dt = 0.5 * t^2
    """

    @pytest.fixture
    def linear_input_system(self):
        """Create system with linear input to integrator."""
        sys = System(name="LinearInput")
        source = LinearSource(name="Source", slope=1.0, offset=0.0)
        integrator = IntegratorComponent(name="Integrator", x0=0.0)

        sys.add_component(source)
        sys.add_component(integrator)
        sys.add_connection(Connection("Source", "y", "Integrator", "u"))

        return sys, integrator

    @pytest.mark.parametrize("dt", [0.1, 0.01])
    @pytest.mark.parametrize(
        "algorithm_cls",
        [GaussSeidelAlgorithm],
        ids=["GaussSeidel"],
    )
    def test_linear_input_accuracy(self, linear_input_system, algorithm_cls, dt):
        """Test accuracy of integration with linear input."""
        sys, integrator = linear_input_system
        t_end = 1.0

        alg = algorithm_cls()
        sys.set_algorithm(alg)
        sys.initialize(t0=0.0)

        # Run simulation
        t = 0.0
        while t < t_end - 1e-12:
            step_dt = min(dt, t_end - t)
            alg.step(sys, t=t, dt=step_dt)
            t += step_dt

        # Analytical solution: y(t) = 0.5 * t^2 = 0.5
        y_computed = integrator.outputs["y"].get()
        y_analytical = 0.5

        # Euler method has O(dt) error for this problem
        assert np.isclose(y_computed, y_analytical, rtol=2 * dt), (
            f"{alg.name} with dt={dt}: y={y_computed}, expected {y_analytical}"
        )


# ============================================================================
# Test Algorithm Comparison on Dynamic System
# ============================================================================
class TestAlgorithmComparisonDynamic:
    """
    Compare algorithm results on a dynamic system with feedback.

    System: Reference decay
    y' = -k * y, y(0) = 1
    Analytical solution: y(t) = exp(-k * t)

    Implemented as:
    Gain(-k) -> Integrator(x0=1.0) -> feedback to Gain
    """

    @pytest.fixture
    def decay_system(self):
        """Create exponential decay system."""
        k = 0.5  # decay rate

        sys = System(name="ExponentialDecay")
        gain = SimpleGain(name="Gain", gain=-k)
        integrator = IntegratorComponent(name="Integrator", x0=1.0)

        sys.add_component(gain)
        sys.add_component(integrator)

        # Gain -> Integrator (derivative)
        sys.add_connection(Connection("Gain", "y", "Integrator", "u"))
        # Integrator -> Gain (feedback)
        sys.add_connection(Connection("Integrator", "y", "Gain", "u"))

        return sys, integrator, k

    @pytest.mark.parametrize("dt", [0.1, 0.01])
    @pytest.mark.parametrize(
        "algorithm_cls",
        [JacobiAlgorithm, GaussSeidelAlgorithm, IJCSAAlgorithm],
        ids=["Jacobi", "GaussSeidel", "IJCSA"],
    )
    def test_decay_accuracy(self, decay_system, algorithm_cls, dt):
        """Test accuracy of exponential decay simulation."""
        sys, integrator, k = decay_system
        t_end = 2.0

        alg = algorithm_cls()
        sys.set_algorithm(alg)
        sys.initialize(t0=0.0)

        # Run simulation
        t = 0.0
        while t < t_end - 1e-12:
            step_dt = min(dt, t_end - t)
            alg.step(sys, t=t, dt=step_dt)
            t += step_dt

        # Analytical solution: y(t) = exp(-k * t) = exp(-0.5 * 2) = exp(-1) ≈ 0.368
        y_computed = integrator.outputs["y"].get()
        y_analytical = np.exp(-k * t_end)

        # Forward Euler has O(dt) error
        assert np.isclose(y_computed, y_analytical, rtol=5 * dt), (
            f"{alg.name} with dt={dt}: y={y_computed}, expected {y_analytical}"
        )

    def test_algorithms_produce_similar_results(self, decay_system):
        """Test that all algorithms produce similar results."""
        _, _, k = decay_system
        t_end = 2.0
        dt = 0.01

        results = {}
        for alg_cls, name in [
            (JacobiAlgorithm, "Jacobi"),
            (GaussSeidelAlgorithm, "GaussSeidel"),
            (IJCSAAlgorithm, "IJCSA"),
        ]:
            # Create fresh system for each algorithm
            sys = System(name=f"Decay_{name}")
            gain = SimpleGain(name="Gain", gain=-k)
            integrator = IntegratorComponent(name="Integrator", x0=1.0)

            sys.add_component(gain)
            sys.add_component(integrator)
            sys.add_connection(Connection("Gain", "y", "Integrator", "u"))
            sys.add_connection(Connection("Integrator", "y", "Gain", "u"))

            alg = alg_cls()
            sys.set_algorithm(alg)
            sys.initialize(t0=0.0)

            # Run simulation
            t = 0.0
            while t < t_end - 1e-12:
                step_dt = min(dt, t_end - t)
                alg.step(sys, t=t, dt=step_dt)
                t += step_dt

            results[name] = integrator.outputs["y"].get()

        # All algorithms should produce similar results
        y_ref = results["GaussSeidel"]
        for name, y in results.items():
            assert np.isclose(y, y_ref, rtol=0.01), (
                f"{name} produced y={y}, reference {y_ref}"
            )


# ============================================================================
# Test Step Size Sensitivity
# ============================================================================
class TestStepSizeSensitivity:
    """Test algorithm sensitivity to step size."""

    def test_convergence_with_decreasing_dt(self):
        """Test that error decreases with decreasing step size."""
        t_end = 1.0

        errors = {}
        for dt in [0.1, 0.05, 0.025, 0.0125]:
            sys = System(name=f"Convergence_dt_{dt}")
            source = ConstantSource(name="Source", value=1.0)
            integrator = IntegratorComponent(name="Integrator", x0=0.0)

            sys.add_component(source)
            sys.add_component(integrator)
            sys.add_connection(Connection("Source", "y", "Integrator", "u"))

            alg = GaussSeidelAlgorithm()
            sys.set_algorithm(alg)
            sys.initialize(t0=0.0)

            # Run simulation
            t = 0.0
            while t < t_end - 1e-12:
                step_dt = min(dt, t_end - t)
                alg.step(sys, t=t, dt=step_dt)
                t += step_dt

            y_computed = integrator.outputs["y"].get()
            y_analytical = 1.0
            errors[dt] = abs(y_computed - y_analytical)

        # Error should decrease with smaller dt (or be effectively zero)
        dt_values = sorted(errors.keys(), reverse=True)
        for i in range(len(dt_values) - 1):
            dt_large = dt_values[i]
            dt_small = dt_values[i + 1]
            # Allow for floating point noise when errors are tiny
            if errors[dt_large] > 1e-12:
                assert errors[dt_small] <= errors[dt_large] + 1e-14, (
                    f"Error should decrease: err({dt_small})={errors[dt_small]} > err({dt_large})={errors[dt_large]}"
                )
