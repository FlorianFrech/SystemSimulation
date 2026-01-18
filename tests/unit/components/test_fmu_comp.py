"""
Unit tests for syssimx.components.fmu.FMUComponent

Tests the FMUComponent class which wraps FMI 2.0 Co-Simulation FMUs.
Uses actual FMU fixtures: AngleEncoder, Pendulum, Reference.
"""

from pathlib import Path

import numpy as np
import pytest

from syssimx.components.fmu import FMUComponent
from syssimx.core.port import PortType
from syssimx.utilities.units import Quantity, ureg

# ============================================================================
# Fixtures
# ============================================================================
FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures" / "fmus"


@pytest.fixture
def pendulum_fmu_path():
    """Path to the Pendulum FMU fixture."""
    return str(FIXTURES_DIR / "Pendulum.fmu")


@pytest.fixture
def reference_fmu_path():
    """Path to the Reference FMU fixture."""
    return str(FIXTURES_DIR / "Reference.fmu")


@pytest.fixture
def angle_encoder_fmu_path():
    """Path to the AngleEncoder FMU fixture."""
    return str(FIXTURES_DIR / "AngleEncoder.fmu")


def _cleanup_fmu(comp):
    """Properly cleanup an FMU component (for tests that create their own)."""
    comp.reset()


@pytest.fixture
def pendulum(pendulum_fmu_path):
    """Create an initialized Pendulum FMUComponent."""
    comp = FMUComponent("Pendulum", fmu_path=pendulum_fmu_path, group="Plant")
    comp.initialize(t0=0.0)
    yield comp
    comp.reset()  # Now works correctly


@pytest.fixture
def reference(reference_fmu_path):
    """Create an initialized Reference FMUComponent."""
    comp = FMUComponent("Reference", fmu_path=reference_fmu_path, group="Input")
    comp.initialize(t0=0.0)
    yield comp
    comp.reset()


@pytest.fixture
def angle_encoder(angle_encoder_fmu_path):
    """Create an initialized AngleEncoder FMUComponent."""
    comp = FMUComponent("AngleEncoder", fmu_path=angle_encoder_fmu_path, group="Sensor")
    comp.initialize(t0=0.0)
    yield comp
    comp.reset()


# ============================================================================
# Test FMUComponent Construction
# ============================================================================
class TestFMUComponentConstruction:
    """Test FMUComponent construction and model description parsing."""

    def test_construction_basic(self, pendulum_fmu_path):
        """Test basic FMUComponent construction."""
        comp = FMUComponent("Pendulum", fmu_path=pendulum_fmu_path, group="Plant")

        assert comp.name == "Pendulum"
        assert comp.group == "Plant"
        assert comp._path == str(Path(pendulum_fmu_path).resolve())

    def test_construction_parses_inputs(self, pendulum_fmu_path):
        """Test that construction parses input ports from model description."""
        comp = FMUComponent("Pendulum", fmu_path=pendulum_fmu_path)

        assert "torque" in comp.input_specs
        assert comp.input_specs["torque"].name == "torque"
        assert comp.input_specs["torque"].direction == "in"
        assert comp.input_specs["torque"].type == PortType.REAL

    def test_construction_parses_outputs(self, pendulum_fmu_path):
        """Test that construction parses output ports from model description."""
        comp = FMUComponent("Pendulum", fmu_path=pendulum_fmu_path)

        assert "q" in comp.output_specs
        assert "omega" in comp.output_specs
        assert "alpha" in comp.output_specs
        assert comp.output_specs["q"].direction == "out"
        assert comp.output_specs["q"].type == PortType.REAL

    def test_construction_parses_parameters(self, pendulum_fmu_path):
        """Test that construction parses parameters from model description."""
        comp = FMUComponent("Pendulum", fmu_path=pendulum_fmu_path)

        assert "L" in comp.parameters
        assert "m" in comp.parameters
        assert "q0" in comp.parameters
        assert "omega0" in comp.parameters
        assert "g" in comp.parameters
        assert "inertia" in comp.parameters

    def test_construction_parses_units(self, pendulum_fmu_path):
        """Test that construction parses units from model description."""
        comp = FMUComponent("Pendulum", fmu_path=pendulum_fmu_path)

        # Input unit
        torque_unit = comp.input_specs["torque"].unit
        assert (1 * ureg(torque_unit)).is_compatible_with(ureg("N*m"))

        # Output units
        q_unit = comp.output_specs["q"].unit
        omega_unit = comp.output_specs["omega"].unit
        assert (1 * ureg(q_unit)).is_compatible_with(ureg("rad"))
        assert (1 * ureg(omega_unit)).is_compatible_with(ureg("rad/s"))

    def test_construction_builds_value_references(self, pendulum_fmu_path):
        """Test that value reference maps are built correctly."""
        comp = FMUComponent("Pendulum", fmu_path=pendulum_fmu_path)

        assert "torque" in comp._vrs_in_real
        assert "q" in comp._vrs_out_real
        assert "omega" in comp._vrs_out_real
        assert "alpha" in comp._vrs_out_real

    def test_construction_reference_no_inputs(self, reference_fmu_path):
        """Test construction of FMU with no inputs (Reference signal)."""
        comp = FMUComponent("Reference", fmu_path=reference_fmu_path)

        assert len(comp.input_specs) == 0
        assert "q_ref" in comp.output_specs

    def test_construction_invalid_path(self):
        """Test that invalid FMU path raises error."""
        with pytest.raises(FileNotFoundError):
            FMUComponent("Invalid", fmu_path="/nonexistent/path.fmu")


# ============================================================================
# Test FMUComponent Initialization
# ============================================================================
class TestFMUComponentInitialization:
    """Test FMUComponent initialization lifecycle."""

    def test_initialize_creates_instance(self, pendulum_fmu_path):
        """Test that initialize creates FMU instance."""
        comp = FMUComponent("Pendulum", fmu_path=pendulum_fmu_path)
        assert comp._instance is None

        comp.initialize(t0=0.0)

        assert comp._instance is not None
        # Note: Don't reset here - terminate properly
        comp._instance.terminate()
        comp._instance.freeInstance()
        comp._instance = None

    def test_initialize_creates_ports(self, pendulum_fmu_path):
        """Test that initialize creates port states from specs."""
        comp = FMUComponent("Pendulum", fmu_path=pendulum_fmu_path)
        comp.initialize(t0=0.0)

        assert "torque" in comp.inputs
        assert "q" in comp.outputs
        assert "omega" in comp.outputs
        comp._instance.terminate()
        comp._instance.freeInstance()
        comp._instance = None

    def test_initialize_sets_time(self, pendulum_fmu_path):
        """Test that initialize sets the component time."""
        comp = FMUComponent("Pendulum", fmu_path=pendulum_fmu_path)
        comp.initialize(t0=1.5)

        assert comp.t == 1.5
        comp._instance.terminate()
        comp._instance.freeInstance()
        comp._instance = None

    def test_initialize_records_initial_outputs(self, pendulum):
        """Test that initialize records initial output values."""
        history = pendulum.get_history()

        assert "q" in history
        assert len(history["q"]["time"]) >= 1
        assert history["q"]["time"][0] == 0.0


# ============================================================================
# Test FMUComponent Parameters
# ============================================================================
class TestFMUComponentParameters:
    """Test FMUComponent parameter handling."""

    def test_set_parameters_before_init(self, pendulum_fmu_path):
        """Test setting parameters before initialization."""
        comp = FMUComponent("Pendulum", fmu_path=pendulum_fmu_path)
        comp.set_parameters(L=0.5, q0=0.1)
        comp.initialize(t0=0.0)

        # Verify parameters were applied
        L_vr = comp.parameters["L"].valueReference
        q0_vr = comp.parameters["q0"].valueReference
        assert comp._instance.getReal([L_vr])[0] == 0.5
        assert comp._instance.getReal([q0_vr])[0] == 0.1
        comp._instance.terminate()
        comp._instance.freeInstance()
        comp._instance = None

    def test_set_parameters_affects_initial_state(self, pendulum_fmu_path):
        """Test that initial condition parameters affect initial state."""
        comp = FMUComponent("Pendulum", fmu_path=pendulum_fmu_path)
        initial_angle = np.deg2rad(30)
        comp.set_parameters(q0=initial_angle, omega0=0.0)
        comp.initialize(t0=0.0)

        outputs = comp.get_outputs()
        assert np.isclose(outputs["q"].magnitude, initial_angle, atol=1e-6)
        comp._instance.terminate()
        comp._instance.freeInstance()
        comp._instance = None

    def test_reference_frequency_parameter(self, reference_fmu_path):
        """Test setting frequency parameter on Reference FMU."""
        comp = FMUComponent("Reference", fmu_path=reference_fmu_path)
        comp.set_parameters(frequency=0.5, amplitude=0.2)
        comp.initialize(t0=0.0)

        freq_vr = comp.parameters["frequency"].valueReference
        amp_vr = comp.parameters["amplitude"].valueReference
        assert comp._instance.getReal([freq_vr])[0] == 0.5
        assert comp._instance.getReal([amp_vr])[0] == 0.2
        comp._instance.terminate()
        comp._instance.freeInstance()
        comp._instance = None


# ============================================================================
# Test FMUComponent Input/Output
# ============================================================================
class TestFMUComponentIO:
    """Test FMUComponent input and output handling."""

    def test_set_inputs_float(self, pendulum):
        """Test setting inputs with float values."""
        pendulum.set_inputs({"torque": 5.0}, t=0.0)

        torque_vr = pendulum._vrs_in_real["torque"]
        assert pendulum._instance.getReal([torque_vr])[0] == 5.0

    def test_set_inputs_quantity(self, pendulum):
        """Test setting inputs with Quantity values."""
        torque = Quantity(10.0, ureg("N*m"))
        pendulum.set_inputs({"torque": torque}, t=0.0)

        torque_vr = pendulum._vrs_in_real["torque"]
        assert pendulum._instance.getReal([torque_vr])[0] == 10.0

    def test_set_inputs_updates_port_state(self, pendulum):
        """Test that set_inputs updates port state."""
        pendulum.set_inputs({"torque": 7.5}, t=0.5)

        port = pendulum.inputs["torque"]
        assert port.value.magnitude == 7.5
        assert port.t_last == 0.5

    def test_get_outputs_returns_quantities(self, pendulum):
        """Test that get_outputs returns Quantity values."""
        outputs = pendulum.get_outputs()

        assert isinstance(outputs["q"], Quantity)
        assert isinstance(outputs["omega"], Quantity)
        assert outputs["q"].is_compatible_with(ureg("rad"))
        assert outputs["omega"].is_compatible_with(ureg("rad/s"))

    def test_get_outputs_reference(self, reference):
        """Test get_outputs for Reference FMU (no inputs)."""
        outputs = reference.get_outputs()

        assert "q_ref" in outputs
        assert isinstance(outputs["q_ref"], Quantity)

    def test_angle_encoder_io(self, angle_encoder):
        """Test AngleEncoder input/output (voltage encoding)."""
        # Set input angle
        angle_encoder.set_inputs({"q": 0.1}, t=0.0)
        angle_encoder.do_step(t=0.0, dt=0.001)

        outputs = angle_encoder.get_outputs()
        assert "U_q" in outputs
        assert isinstance(outputs["U_q"], Quantity)
        assert outputs["U_q"].is_compatible_with(ureg("V"))


# ============================================================================
# Test FMUComponent Stepping
# ============================================================================
class TestFMUComponentStepping:
    """Test FMUComponent time stepping."""

    def test_do_step_advances_time(self, pendulum):
        """Test that do_step advances component time."""
        assert pendulum.t == 0.0

        pendulum.do_step(t=0.0, dt=0.1)

        assert pendulum.t == 0.1

    def test_do_step_changes_state(self, pendulum_fmu_path):
        """Test that do_step changes dynamic state (pendulum swings)."""
        comp = FMUComponent("Pendulum", fmu_path=pendulum_fmu_path)
        comp.set_parameters(q0=np.deg2rad(30), omega0=0.0)
        comp.initialize(t0=0.0)

        initial_omega = comp.get_outputs()["omega"].magnitude

        # Apply no torque, let gravity act
        comp.set_inputs({"torque": 0.0}, t=0.0)
        comp.do_step(t=0.0, dt=0.1)

        final_omega = comp.get_outputs()["omega"].magnitude

        # Pendulum should have gained angular velocity due to gravity
        assert not np.isclose(initial_omega, final_omega)
        comp._instance.terminate()
        comp._instance.freeInstance()
        comp._instance = None

    def test_do_step_with_torque_input(self, pendulum):
        """Test that torque input affects pendulum dynamics."""
        # Start at equilibrium, apply torque
        initial_omega = pendulum.get_outputs()["omega"].magnitude
        assert np.isclose(initial_omega, 0.0)

        pendulum.set_inputs({"torque": 10.0}, t=0.0)
        pendulum.do_step(t=0.0, dt=0.1)

        final_omega = pendulum.get_outputs()["omega"].magnitude
        # Torque should cause angular acceleration
        assert not np.isclose(final_omega, 0.0)

    def test_do_step_records_history(self, pendulum):
        """Test that do_step records output history."""
        pendulum.do_step(t=0.0, dt=0.1)
        pendulum.do_step(t=0.1, dt=0.1)

        history = pendulum.get_history()
        # Should have initial + 2 steps = 3 time points
        assert len(history["q"]["time"]) == 3

    def test_reference_evolves_over_time(self, reference):
        """Test that Reference signal evolves (sinusoidal output)."""
        initial_ref = reference.get_outputs()["q_ref"].magnitude

        # Step through time
        for i in range(10):
            reference.do_step(t=i * 0.1, dt=0.1)

        final_ref = reference.get_outputs()["q_ref"].magnitude

        # Reference should have changed (unless at same phase)
        # At t=1.0, sin(2*pi*0.25*1.0) = sin(pi/2) = 1
        assert not np.isclose(initial_ref, final_ref)


# ============================================================================
# Test FMUComponent Direct Feedthrough
# ============================================================================
class TestFMUComponentDirectFeedthrough:
    """Test FMUComponent direct feedthrough detection."""

    def test_angle_encoder_has_direct_feedthrough(self, angle_encoder_fmu_path):
        """Test that AngleEncoder has direct feedthrough (algebraic)."""
        comp = FMUComponent("AngleEncoder", fmu_path=angle_encoder_fmu_path)

        # AngleEncoder: U_q depends directly on q (no dynamics)
        # Check if direct_feedthrough is detected
        assert "U_q" in comp.direct_feedthrough
        if comp.direct_feedthrough["U_q"]:
            assert "q" in comp.direct_feedthrough["U_q"]

    def test_reference_no_direct_feedthrough(self, reference_fmu_path):
        """Test that Reference has no direct feedthrough (no inputs)."""
        comp = FMUComponent("Reference", fmu_path=reference_fmu_path)

        # Reference has no inputs, so no direct feedthrough possible
        for deps in comp.direct_feedthrough.values():
            assert len(deps) == 0

    def test_evaluate_outputs_with_direct_feedthrough(self, angle_encoder):
        """Test evaluate_outputs for component with direct feedthrough."""
        # AngleEncoder should be able to evaluate outputs without stepping
        outputs = angle_encoder.evaluate_outputs({"q": 0.2}, t=0.0)

        assert "U_q" in outputs


# ============================================================================
# Test FMUComponent State Management
# ============================================================================
class TestFMUComponentState:
    """Test FMUComponent state get/set functionality."""

    def test_get_state(self, pendulum_fmu_path):
        """Test getting component state."""
        comp = FMUComponent("Pendulum", fmu_path=pendulum_fmu_path)
        comp.set_parameters(q0=0.5, omega0=0.1)
        comp.initialize(t0=0.0)

        state = comp.get_state()

        assert "q" in state
        assert "omega" in state
        assert "value" in state["q"]
        assert "unit" in state["q"]
        assert np.isclose(state["q"]["value"], 0.5)
        assert np.isclose(state["omega"]["value"], 0.1)
        comp._instance.terminate()
        comp._instance.freeInstance()
        comp._instance = None

    def test_set_state(self, pendulum):
        """Test setting component state."""
        new_state = {
            "q0": {
                "value": 0.3,
                "unit": "rad",
            },  # only parameters can be set: q0 as initial condition
            "omega0": {
                "value": -0.2,
                "unit": "rad/s",
            },  # only parameters can be set: omega0 as initial condition
        }
        pendulum.set_state(new_state, t=0.5)

        outputs = pendulum.get_outputs()
        assert np.isclose(outputs["q"].magnitude, 0.3, atol=1e-3)
        assert np.isclose(outputs["omega"].magnitude, -0.2, atol=1e-3)


# ============================================================================
# Test FMUComponent Reset
# ============================================================================
class TestFMUComponentReset:
    """Test FMUComponent reset functionality."""

    def test_reset_clears_instance(self, pendulum):
        """Test that reset clears the FMU instance."""
        assert pendulum._instance is not None

        pendulum.reset()

        assert pendulum._instance is None

    def test_reset_clears_history(self, pendulum):
        """Test that reset clears history."""
        pendulum.do_step(t=0.0, dt=0.1)
        assert len(pendulum.get_history()["q"]["time"]) > 0

        pendulum.reset()

        # History object exists but values are cleared
        assert all(len(ph._timestamps) == 0 for ph in pendulum.history._port_histories.values())

    def test_reset_clears_ports(self, pendulum):
        """Test that reset clears input/output ports."""
        assert len(pendulum.inputs) > 0
        assert len(pendulum.outputs) > 0

        pendulum.reset()

        assert len(pendulum.inputs) == 0
        assert len(pendulum.outputs) == 0

    def test_reset_allows_reinit(self, pendulum_fmu_path):
        """Test that component can be reinitialized after reset."""
        comp = FMUComponent("Pendulum", fmu_path=pendulum_fmu_path)
        comp.initialize(t0=0.0)
        comp.do_step(t=0.0, dt=0.1)
        comp.reset()

        # Should be able to initialize again
        comp.initialize(t0=0.0)
        assert comp._instance is not None
        assert comp.t == 0.0
        assert "q" in comp.outputs
        _cleanup_fmu(comp)

    def test_soft_reset_preserves_instance(self, pendulum):
        """Test that soft_reset keeps FMU instance alive."""
        instance_before = pendulum._instance

        pendulum.soft_reset(t0=0.0)

        assert pendulum._instance is instance_before

    def test_soft_reset_clears_history(self, pendulum):
        """Test that soft_reset clears history."""
        pendulum.do_step(t=0.0, dt=0.1)
        assert len(pendulum.get_history()["q"]["time"]) > 0

        pendulum.soft_reset(t0=0.0)

        # Should have just the initial recording
        assert len(pendulum.get_history()["q"]["time"]) == 1

    def test_soft_reset_resets_time(self, pendulum):
        """Test that soft_reset resets component time."""
        pendulum.do_step(t=0.0, dt=0.5)
        assert pendulum.t == 0.5

        pendulum.soft_reset(t0=0.0)

        assert pendulum.t == 0.0

    def test_soft_reset_restores_initial_state(self, pendulum_fmu_path):
        """Test that soft_reset restores initial conditions."""
        comp = FMUComponent("Pendulum", fmu_path=pendulum_fmu_path)
        initial_angle = np.deg2rad(30)
        comp.set_parameters(q0=initial_angle, omega0=0.0)
        comp.initialize(t0=0.0)

        # Step forward - state changes
        comp.set_inputs({"torque": 0.0}, t=0.0)
        for i in range(10):
            comp.do_step(t=i * 0.1, dt=0.1)

        q_after_stepping = comp.get_outputs()["q"].magnitude
        assert not np.isclose(q_after_stepping, initial_angle, atol=0.01)

        # Soft reset - should restore initial state
        comp.soft_reset(t0=0.0)

        q_after_reset = comp.get_outputs()["q"].magnitude
        assert np.isclose(q_after_reset, initial_angle, atol=1e-6)
        _cleanup_fmu(comp)


# ============================================================================
# Test FMUComponent History
# ============================================================================
class TestFMUComponentHistory:
    """Test FMUComponent history recording."""

    def test_history_records_all_outputs(self, pendulum):
        """Test that history records all output ports."""
        pendulum.do_step(t=0.0, dt=0.1)

        history = pendulum.get_history()

        assert "q" in history
        assert "omega" in history
        assert "alpha" in history

    def test_history_time_values_correct(self, pendulum):
        """Test that history time values are correct."""
        pendulum.do_step(t=0.0, dt=0.1)
        pendulum.do_step(t=0.1, dt=0.1)
        pendulum.do_step(t=0.2, dt=0.1)

        history = pendulum.get_history()
        times = history["q"]["time"]

        assert np.isclose(times[0], 0.0)
        assert np.isclose(times[1], 0.1)
        assert np.isclose(times[2], 0.2)
        assert np.isclose(times[3], 0.3)

    def test_get_history_arrays(self, pendulum):
        """Test get_history_arrays returns numpy arrays."""
        pendulum.do_step(t=0.0, dt=0.1)

        t_arr, data = pendulum.get_history_arrays()

        assert isinstance(t_arr, np.ndarray)
        assert isinstance(data["q"], np.ndarray)
        assert len(t_arr) == len(data["q"])


# ============================================================================
# Integration-style Tests (Multi-step simulation)
# ============================================================================
class TestFMUComponentSimulation:
    """Integration-style tests for FMUComponent simulation."""

    def test_pendulum_free_oscillation(self, pendulum_fmu_path):
        """Test free oscillation of pendulum (no damping)."""
        comp = FMUComponent("Pendulum", fmu_path=pendulum_fmu_path)
        comp.set_parameters(q0=np.deg2rad(10), omega0=0.0)
        comp.initialize(t0=0.0)

        dt = 0.01
        t = 0.0
        for _ in range(100):
            comp.set_inputs({"torque": 0.0}, t=t)
            comp.do_step(t=t, dt=dt)
            t += dt

        # After 1 second, pendulum should have oscillated
        history = comp.get_history()
        q_values = history["q"]["values"]

        # Check that oscillation occurred (max > initial, min < initial)
        initial_q = np.deg2rad(10)
        assert np.max(q_values) > initial_q * 0.5
        assert np.min(q_values) < initial_q * 0.5
        comp._instance.terminate()
        comp._instance.freeInstance()
        comp._instance = None

    def test_reference_sinusoidal_output(self, reference_fmu_path):
        """Test that Reference produces sinusoidal output."""
        comp = FMUComponent("Reference", fmu_path=reference_fmu_path)
        comp.set_parameters(frequency=1.0, amplitude=1.0, mean=0.0)
        comp.initialize(t0=0.0)

        dt = 0.01
        t = 0.0
        for _ in range(100):
            comp.do_step(t=t, dt=dt)
            t += dt

        history = comp.get_history()
        q_ref_values = history["q_ref"]["values"]

        # At 1Hz, in 1 second we should see a full oscillation
        assert np.max(q_ref_values) > 0.9  # Close to amplitude
        assert np.min(q_ref_values) < -0.9
        comp._instance.terminate()
        comp._instance.freeInstance()
        comp._instance = None
