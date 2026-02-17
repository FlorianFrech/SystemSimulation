"""
Unit tests for FMUPendulum component.

Tests FMUPendulum construction, initialization, time stepping,
state management, snapshot/restore, and event handling.
"""

import sys
import numpy as np
import pytest

from syssimx.core.base import CoSimComponent
from syssimx.components.fmu import FMUComponent
from syssimx.core.port import PortSpec, PortState, PortType
from syssimx.utilities.units import ureg

# Skip entire module if fmpy is not available
pytest.importorskip("fmpy", reason="fmpy not installed")

from master_pendulum.components.fmu.fmu_pendulum import FMUPendulum


# ============================================================================
# Fixtures
# ============================================================================
@pytest.fixture(params=["Euler", "Cvode"], ids=["Euler", "Cvode"])
def solver(request):
    """Parametrize over available FMU solvers."""
    return request.param


@pytest.fixture
def pendulum(solver):
    """Create and return an uninitialized FMUPendulum."""
    return FMUPendulum(name="TestPendulum", solver=solver)


@pytest.fixture
def initialized_pendulum(pendulum):
    """Create, initialize, and return an FMUPendulum. Cleanup after test."""
    pendulum.initialize(t0=0.0)
    yield pendulum
    try:
        pendulum.reset()
    except Exception:
        pass


# ============================================================================
# Test FMUPendulum Construction
# ============================================================================
class TestFMUPendulumConstruction:
    """Test FMUPendulum creation and basic properties."""

    def test_construction(self, pendulum):
        assert pendulum.name == "TestPendulum"
        assert isinstance(pendulum, FMUPendulum)
        assert isinstance(pendulum, FMUComponent)
        assert isinstance(pendulum, CoSimComponent)

    def test_invalid_solver_raises(self):
        with pytest.raises(ValueError, match="Unsupported solver"):
            FMUPendulum(name="Bad", solver="InvalidSolver")

    def test_input_port_specs(self, pendulum):
        assert "torque" in pendulum.input_specs
        torque_spec = pendulum.input_specs["torque"]
        assert torque_spec.type == PortType.REAL
        assert torque_spec.direction == "in"

    def test_event_input_port_spec(self, pendulum):
        assert "omega_invert" in pendulum.input_specs
        spec = pendulum.input_specs["omega_invert"]
        assert spec.type == PortType.EVENT
        assert spec.direction == "in"

    def test_output_port_specs(self, pendulum):
        expected_outputs = {"q", "omega", "alpha"}
        assert expected_outputs.issubset(set(pendulum.output_specs.keys()))

        for name in expected_outputs:
            spec = pendulum.output_specs[name]
            assert spec.type == PortType.REAL
            assert spec.direction == "out"

    def test_output_units(self, pendulum):
        # Units should match the Modelica model description
        q_spec = pendulum.output_specs["q"]
        omega_spec = pendulum.output_specs["omega"]
        alpha_spec = pendulum.output_specs["alpha"]

        assert q_spec.unit is not None
        assert omega_spec.unit is not None
        assert alpha_spec.unit is not None

    def test_solver_attribute_stored(self, pendulum, solver):
        assert pendulum.solver == solver


# ============================================================================
# Test FMUPendulum Parameters
# ============================================================================
class TestFMUPendulumParameters:
    """Test parameter getting, setting, and validation."""

    def test_default_parameters_present(self, pendulum):
        params = pendulum.get_parameters()
        # Parameters from the Modelica model
        expected_params = {"m", "L", "q0", "omega0", "g", "inertia"}
        assert expected_params.issubset(set(params.keys()))

    def test_get_specific_parameter(self, pendulum):
        result = pendulum.get_parameters("m")
        assert "m" in result

    def test_get_unknown_parameter_raises(self, pendulum):
        with pytest.raises(KeyError, match="Unknown parameter"):
            pendulum.get_parameters("nonexistent")

    def test_set_parameter(self, pendulum):
        pendulum.set_parameters(m=50.0)
        params = pendulum.get_parameters("m")
        m_val = params["m"]
        mag = m_val.magnitude if hasattr(m_val, "magnitude") else m_val
        assert np.isclose(mag, 50.0)

    def test_set_unknown_parameter_raises(self, pendulum):
        with pytest.raises(KeyError, match="Unknown parameter"):
            pendulum.set_parameters(nonexistent=1.0)

    def test_set_parameter_wrong_type_raises(self, pendulum):
        with pytest.raises(TypeError):
            pendulum.set_parameters(m="not_a_number")


# ============================================================================
# Test FMUPendulum Initialization
# ============================================================================
class TestFMUPendulumInitialization:
    """Test FMUPendulum initialization."""

    def test_initialization(self, initialized_pendulum):
        pend = initialized_pendulum
        assert pend._is_initialized is True

        # Check ports are created
        assert "torque" in pend.inputs
        assert isinstance(pend.inputs["torque"], PortState)

        expected_outputs = {"q", "omega", "alpha"}
        for name in expected_outputs:
            assert name in pend.outputs
            assert isinstance(pend.outputs[name], PortState)

    def test_initial_output_values(self, initialized_pendulum):
        pend = initialized_pendulum
        outputs = pend.get_outputs()

        q_val = outputs["q"]
        omega_val = outputs["omega"]

        q_mag = q_val.magnitude if hasattr(q_val, "magnitude") else q_val
        omega_mag = omega_val.magnitude if hasattr(omega_val, "magnitude") else omega_val

        # Default initial conditions: theta0=0, omega0=0
        assert np.isclose(q_mag, 0.0, atol=1e-10)
        assert np.isclose(omega_mag, 0.0, atol=1e-10)

    def test_macro_state_initialized(self, initialized_pendulum):
        pend = initialized_pendulum
        assert pend._curr_macro_state is not None
        assert pend._prev_macro_state is None
        assert pend._prev_macro_dt is None
        assert np.isclose(pend._prev_macro_t, 0.0)

    def test_custom_initial_conditions(self, solver):
        pend = FMUPendulum(name="CustomIC", solver=solver)
        pend.set_parameters(q0=0.5, omega0=1.0)
        pend.initialize(t0=0.0)
        try:
            outputs = pend.get_outputs()
            q_mag = outputs["q"].magnitude if hasattr(outputs["q"], "magnitude") else outputs["q"]
            omega_mag = (
                outputs["omega"].magnitude
                if hasattr(outputs["omega"], "magnitude")
                else outputs["omega"]
            )
            assert np.isclose(q_mag, 0.5, atol=1e-6)
            assert np.isclose(omega_mag, 1.0, atol=1e-6)
        finally:
            pend.reset()

    def test_double_initialization_prevented(self, initialized_pendulum):
        pend = initialized_pendulum
        outputs_before = pend.get_outputs()

        # Second initialize should be a no-op
        pend.initialize(t0=5.0)

        outputs_after = pend.get_outputs()
        assert pend.t == 0.0  # Should not change

        for name in ("q", "omega"):
            v_before = outputs_before[name]
            v_after = outputs_after[name]
            m_before = v_before.magnitude if hasattr(v_before, "magnitude") else v_before
            m_after = v_after.magnitude if hasattr(v_after, "magnitude") else v_after
            assert np.isclose(m_before, m_after)


# ============================================================================
# Test FMUPendulum Input Setting
# ============================================================================
class TestFMUPendulumInputs:
    """Test setting inputs on the FMU pendulum."""

    def test_set_torque_input(self, initialized_pendulum):
        pend = initialized_pendulum
        pend.set_inputs({"torque": 1.0 * ureg("N*m")}, t=0.0)

        torque_val = pend.inputs["torque"].get()
        mag = torque_val.magnitude if hasattr(torque_val, "magnitude") else torque_val
        assert np.isclose(mag, 1.0)

    def test_set_unknown_input_raises(self, initialized_pendulum):
        pend = initialized_pendulum
        with pytest.raises(KeyError):
            pend.set_inputs({"nonexistent": 1.0}, t=0.0)

    def test_set_torque_zero(self, initialized_pendulum):
        pend = initialized_pendulum
        pend.set_inputs({"torque": 0.0 * ureg("N*m")}, t=0.0)

        torque_val = pend.inputs["torque"].get()
        mag = torque_val.magnitude if hasattr(torque_val, "magnitude") else torque_val
        assert np.isclose(mag, 0.0)


# ============================================================================
# Test FMUPendulum Time Stepping
# ============================================================================
class TestFMUPendulumTimeStepping:
    """Test time stepping behavior."""

    def test_do_step_advances_time(self, initialized_pendulum):
        pend = initialized_pendulum
        pend.set_inputs({"torque": 0.0 * ureg("N*m")}, t=0.0)
        pend.do_step(t=0.0, dt=0.01)
        assert np.isclose(pend.t, 0.01)

    def test_do_step_updates_macro_history(self, initialized_pendulum):
        pend = initialized_pendulum
        pend.set_inputs({"torque": 0.0 * ureg("N*m")}, t=0.0)

        assert pend._prev_macro_state is None
        pend.do_step(t=0.0, dt=0.01)

        assert pend._prev_macro_state is not None
        assert pend._curr_macro_state is not None
        assert np.isclose(pend._prev_macro_dt, 0.01)
        assert np.isclose(pend._prev_macro_t, 0.0)

    def test_free_fall_produces_motion(self, solver):
        """A pendulum released from a nonzero angle should move under gravity."""
        pend = FMUPendulum(name="FreeFall", solver=solver)
        pend.set_parameters(q0=0.3)  # 0.3 rad initial angle
        pend.initialize(t0=0.0)
        try:
            pend.set_inputs({"torque": 0.0 * ureg("N*m")}, t=0.0)

            # Take several steps
            t = 0.0
            dt = 0.001
            for _ in range(100):
                pend.do_step(t=t, dt=dt)
                t += dt

            outputs = pend.get_outputs()
            q_mag = outputs["q"].magnitude if hasattr(outputs["q"], "magnitude") else outputs["q"]
            omega_mag = (
                outputs["omega"].magnitude
                if hasattr(outputs["omega"], "magnitude")
                else outputs["omega"]
            )

            # Pendulum should have moved: angle changed and velocity nonzero
            assert not np.isclose(q_mag, 0.3, atol=1e-6), "Angle should have changed"
            assert not np.isclose(omega_mag, 0.0, atol=1e-6), "Velocity should be nonzero"
        finally:
            pend.reset()

    def test_torque_produces_acceleration(self, initialized_pendulum):
        """A constant torque on a pendulum at rest should produce angular acceleration."""
        pend = initialized_pendulum
        torque_value = 5.0  # N*m
        pend.set_inputs({"torque": torque_value * ureg("N*m")}, t=0.0)

        pend.do_step(t=0.0, dt=0.01)

        outputs = pend.get_outputs()
        omega_mag = (
            outputs["omega"].magnitude
            if hasattr(outputs["omega"], "magnitude")
            else outputs["omega"]
        )
        # With torque applied, omega should be nonzero after a step
        assert abs(omega_mag) > 0.0, "Torque should produce angular velocity"

    def test_multiple_steps_consistency(self, initialized_pendulum):
        """Multiple steps should produce monotonically advancing time."""
        pend = initialized_pendulum
        pend.set_inputs({"torque": 0.0 * ureg("N*m")}, t=0.0)

        times = [0.0]
        t = 0.0
        dt = 0.01
        for _ in range(10):
            pend.do_step(t=t, dt=dt)
            t += dt
            times.append(pend.t)

        # Times should be strictly increasing
        for i in range(1, len(times)):
            assert times[i] > times[i - 1]


# ============================================================================
# Test FMUPendulum State Get/Set
# ============================================================================
class TestFMUPendulumState:
    """Test state serialization and restoration."""

    def test_get_state_returns_dict(self, initialized_pendulum):
        state = initialized_pendulum.get_state()
        assert isinstance(state, dict)

        # Should contain model variables
        assert "q" in state or "theta" in state
        assert "omega" in state

    def test_get_state_contains_values(self, initialized_pendulum):
        state = initialized_pendulum.get_state()
        for var_name, attr in state.items():
            assert "value" in attr, f"State variable '{var_name}' missing 'value'"

    def test_get_macro_history(self, initialized_pendulum):
        pend = initialized_pendulum
        history = pend.get_macro_history()
        assert "current" in history
        assert "previous" in history
        assert "dt" in history
        assert "t" in history

    def test_get_macro_history_after_step(self, initialized_pendulum):
        pend = initialized_pendulum
        pend.set_inputs({"torque": 0.0 * ureg("N*m")}, t=0.0)
        pend.do_step(t=0.0, dt=0.01)

        history = pend.get_macro_history()
        assert history["previous"] is not None
        assert np.isclose(history["dt"], 0.01)
        assert np.isclose(history["t"], 0.0)


# ============================================================================
# Test FMUPendulum Snapshot and Restore (Rollback)
# ============================================================================
class TestFMUPendulumSnapshotRestore:
    """Test snapshot and restore functionality for rollback."""

    def test_supports_rollback(self, initialized_pendulum):
        # FMUPendulum implements snapshot_state/restore_state
        assert initialized_pendulum.supports_rollback

    def test_snapshot_returns_dict_with_mode(self, initialized_pendulum):
        snapshot = initialized_pendulum.snapshot_state()
        assert isinstance(snapshot, dict)
        assert snapshot.get("mode") == "EQB"

    def test_snapshot_restore_preserves_state(self, solver):
        """Snapshot at t1, advance to t2, restore to t1 — state should match."""
        pend = FMUPendulum(name="Rollback", solver=solver)
        pend.set_parameters(q0=0.2)
        pend.initialize(t0=0.0)
        try:
            pend.set_inputs({"torque": 0.0 * ureg("N*m")}, t=0.0)

            # Advance to t=0.05
            t = 0.0
            dt = 0.01
            for _ in range(5):
                pend.do_step(t=t, dt=dt)
                t += dt

            # Snapshot at t=0.05
            outputs_at_snapshot = pend.get_outputs()
            q_snapshot = (
                outputs_at_snapshot["q"].magnitude
                if hasattr(outputs_at_snapshot["q"], "magnitude")
                else outputs_at_snapshot["q"]
            )
            omega_snapshot = (
                outputs_at_snapshot["omega"].magnitude
                if hasattr(outputs_at_snapshot["omega"], "magnitude")
                else outputs_at_snapshot["omega"]
            )
            snapshot = pend.snapshot_state()
            t_snapshot = pend.t

            # Advance further to t=0.10
            for _ in range(5):
                pend.do_step(t=t, dt=dt)
                t += dt

            # Verify state has changed
            outputs_after = pend.get_outputs()
            q_after = (
                outputs_after["q"].magnitude
                if hasattr(outputs_after["q"], "magnitude")
                else outputs_after["q"]
            )
            assert not np.isclose(q_after, q_snapshot, atol=1e-8), "State should have changed"

            # Restore to snapshot
            pend.restore_state(snapshot, t=t_snapshot)

            # Verify state matches snapshot
            outputs_restored = pend.get_outputs()
            q_restored = (
                outputs_restored["q"].magnitude
                if hasattr(outputs_restored["q"], "magnitude")
                else outputs_restored["q"]
            )
            omega_restored = (
                outputs_restored["omega"].magnitude
                if hasattr(outputs_restored["omega"], "magnitude")
                else outputs_restored["omega"]
            )

            assert np.isclose(q_restored, q_snapshot, atol=1e-4), (
                f"q mismatch after restore: {q_restored} vs {q_snapshot}"
            )
            assert np.isclose(omega_restored, omega_snapshot, atol=1e-4), (
                f"omega mismatch after restore: {omega_restored} vs {omega_snapshot}"
            )
            assert np.isclose(pend.t, t_snapshot)
        finally:
            pend.reset()

    def test_restore_invalid_mode_raises(self, initialized_pendulum):
        snapshot = {"mode": "INVALID"}
        with pytest.raises(ValueError, match="Incompatible snapshot mode"):
            initialized_pendulum.restore_state(snapshot, t=0.0)


# ============================================================================
# Test FMUPendulum Event Handling
# ============================================================================
class TestFMUPendulumEventHandling:
    """Test event handling (omega inversion on wall hit)."""

    def test_wall_hit_inverts_omega(self, solver):
        """Handling a 'wall_hit' event should invert the angular velocity."""
        pend = FMUPendulum(name="EventTest", solver=solver)
        pend.set_parameters(q0=0.0, omega0=2.0)
        pend.initialize(t0=0.0)
        try:
            pend.set_inputs({"torque": 0.0 * ureg("N*m")}, t=0.0)

            # Take a step so omega is nonzero
            pend.do_step(t=0.0, dt=0.01)

            outputs_before = pend.get_outputs()
            omega_before = (
                outputs_before["omega"].magnitude
                if hasattr(outputs_before["omega"], "magnitude")
                else outputs_before["omega"]
            )

            # Handle wall_hit event
            pend.handle_event(["wall_hit"], t=0.01)

            outputs_after = pend.get_outputs()
            omega_after = (
                outputs_after["omega"].magnitude
                if hasattr(outputs_after["omega"], "magnitude")
                else outputs_after["omega"]
            )

            # Omega should be inverted (with restitution=1)
            assert np.isclose(omega_after, -omega_before, atol=1e-3), (
                f"omega should be inverted: {omega_after} vs {-omega_before}"
            )
        finally:
            pend.reset()

    def test_non_wall_hit_event_is_noop(self, initialized_pendulum):
        """Handling an event that is not 'wall_hit' should not change state."""
        pend = initialized_pendulum
        pend.set_inputs({"torque": 0.0 * ureg("N*m")}, t=0.0)
        pend.do_step(t=0.0, dt=0.01)

        outputs_before = pend.get_outputs()
        pend._handle_events_internal(["some_other_event"], t=0.01)
        outputs_after = pend.get_outputs()

        for name in ("q", "omega"):
            v_before = outputs_before[name]
            v_after = outputs_after[name]
            m_before = v_before.magnitude if hasattr(v_before, "magnitude") else v_before
            m_after = v_after.magnitude if hasattr(v_after, "magnitude") else v_after
            assert np.isclose(m_before, m_after), (
                f"{name} changed on non-wall_hit event: {m_before} vs {m_after}"
            )


# ============================================================================
# Test FMUPendulum Output State Updates
# ============================================================================
class TestFMUPendulumOutputStates:
    """Test _update_output_states including event port behavior."""

    def test_event_ports_default_to_false(self, initialized_pendulum):
        pend = initialized_pendulum
        pend._update_output_states(t=0.0, event_names=[])

        for out_port in pend.outputs.values():
            if out_port.spec.type == PortType.EVENT:
                assert out_port.get() is False

    def test_event_ports_set_true_on_event(self, initialized_pendulum):
        pend = initialized_pendulum
        # omega_invert is an input event port; check if there are output event ports
        event_output_names = [
            name
            for name, spec in pend.output_specs.items()
            if spec.type == PortType.EVENT
        ]
        if event_output_names:
            pend._update_output_states(t=0.0, event_names=event_output_names)
            for name in event_output_names:
                assert pend.outputs[name].get() is True


# ============================================================================
# Test FMUPendulum Reset
# ============================================================================
class TestFMUPendulumReset:
    """Test reset and cleanup."""

    def test_reset_clears_instance(self, initialized_pendulum):
        pend = initialized_pendulum
        assert pend._is_initialized is True

        pend.reset()

        assert pend._is_initialized is False
        assert pend._instance is None

    def test_reinitialize_after_reset(self, solver):
        """Component should be usable again after reset + initialize."""
        pend = FMUPendulum(name="ResetTest", solver=solver)
        pend.initialize(t0=0.0)
        pend.set_inputs({"torque": 0.0 * ureg("N*m")}, t=0.0)
        pend.do_step(t=0.0, dt=0.01)
        pend.reset()

        # Reinitialize
        pend.initialize(t0=0.0)
        outputs = pend.get_outputs()
        assert "q" in outputs or "theta" in outputs
        pend.reset()


# ============================================================================
# Test FMUPendulum Physical Consistency
# ============================================================================
class TestFMUPendulumPhysics:
    """Sanity checks for physical behavior of the pendulum model."""

    def test_small_angle_period_approximation(self, solver):
        """For small angles, the pendulum period should approximate 2π√(I/mgL)."""
        m = 40.0
        L = 0.6
        inertia = 20.0
        g = 9.81
        theta0 = 0.05  # Small angle (rad)

        pend = FMUPendulum(name="PhysicsTest", solver=solver)
        pend.set_parameters(m=m, L=L, inertia=inertia, g=g, q0=theta0, omega0=0.0)
        pend.initialize(t0=0.0)
        try:
            pend.set_inputs({"torque": 0.0 * ureg("N*m")}, t=0.0)

            # Expected period: T = 2π√(I / (m*g*L))
            T_expected = 2 * np.pi * np.sqrt(inertia / (m * g * L))

            # Simulate for one full period
            t = 0.0
            dt = 1e-4
            n_steps = int(T_expected / dt)
            angles = []

            for _ in range(n_steps):
                pend.do_step(t=t, dt=dt)
                t += dt
                outputs = pend.get_outputs()
                q_val = outputs["q"]
                q_mag = q_val.magnitude if hasattr(q_val, "magnitude") else q_val
                angles.append(q_mag)

            # After one period, angle should return close to initial value
            final_angle = angles[-1]
            assert np.isclose(final_angle, theta0, atol=0.01), (
                f"After one period ({T_expected:.3f}s), angle should return near "
                f"initial: got {final_angle:.4f}, expected ~{theta0}"
            )
        finally:
            pend.reset()

    def test_zero_torque_preserves_energy(self, solver):
        """Total energy should be approximately conserved with zero external torque."""
        m = 40.0
        L = 0.6
        inertia = 20.0
        g = 9.81
        q0 = 0.3

        pend = FMUPendulum(name="EnergyTest", solver=solver)
        pend.set_parameters(m=m, L=L, inertia=inertia, g=g, q0=q0, omega0=0.0)
        pend.initialize(t0=0.0)
        try:
            pend.set_inputs({"torque": 0.0 * ureg("N*m")}, t=0.0)

            def total_energy(q, omega):
                kinetic = 0.5 * inertia * omega**2
                potential = m * g * L * (1 - np.cos(q))
                return kinetic + potential

            outputs = pend.get_outputs()
            q0 = outputs["q"].magnitude if hasattr(outputs["q"], "magnitude") else outputs["q"]
            w0 = (
                outputs["omega"].magnitude
                if hasattr(outputs["omega"], "magnitude")
                else outputs["omega"]
            )
            E0 = total_energy(q0, w0)

            t = 0.0
            dt = 1e-4
            for _ in range(1000):
                pend.do_step(t=t, dt=dt)
                t += dt

            outputs = pend.get_outputs()
            q_f = outputs["q"].magnitude if hasattr(outputs["q"], "magnitude") else outputs["q"]
            w_f = (
                outputs["omega"].magnitude
                if hasattr(outputs["omega"], "magnitude")
                else outputs["omega"]
            )
            E_f = total_energy(q_f, w_f)

            # Energy should be conserved within tolerance (numerical dissipation allowed)
            rel_error = abs(E_f - E0) / max(abs(E0), 1e-12)
            assert rel_error < 0.05, (
                f"Energy not conserved: E0={E0:.6f}, Ef={E_f:.6f}, rel_error={rel_error:.4f}"
            )
        finally:
            pend.reset()