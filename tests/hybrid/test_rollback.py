from typing import Any, Dict
from pathlib import Path
import numpy as np
import pytest

from SysSimX.core.base import CoSimComponent
from SysSimX.core.port import PortSpec, PortType
from SysSimX.components.fmu_comp import FMUComponent
from SysSimX.utilities.units import Quantity

# -------------------------------------------------------------------
# Rollback Test Component
# -------------------------------------------------------------------
class RollbackComponent(CoSimComponent):
    """
    Simple component with a state variable that evolves linearly.
    x(t) = x0 + v * t
    Used for testing event indicators, zero-crossing detection, and rollback.
    """
    
    def __init__(self, name: str, x0: float = 0.0, velocity: float = 1.0):
        super().__init__(name)
        self.x0 = x0
        self.v = velocity
        self.x = x0
        self._t0 = None
        
    def _initialize_component(self, t0: float) -> None:
        self._t0 = t0
        self.x = self.x0
        
        self.output_specs = {
            "x": PortSpec(name="x", type=PortType.REAL, direction="out", unit="m", description="State variable")
        }
        self._initialize_ports_from_specs()
        
    def _do_step_internal(self, t: float, dt: float) -> None:
        self.x = self.x0 + self.v * (t + dt - self._t0)
        
    def _update_output_states(self, t: float) -> None:
        self.outputs["x"].set(Quantity(self.x, "m"), t=t)
        
    def set_state(self, state: Dict[str, Any], t: float) -> None:
        if "x" in state:
            val = state["x"]
            self.x = val.magnitude if isinstance(val, Quantity) else val
            
    def get_state(self) -> Dict[str, Any]:
        return {"x": Quantity(self.x, "m")}
    
        # Rollback support
    def snapshot_state(self):
        """Create a snapshot of the current component state."""
        state = {
            "x": self.x,
            "v": self.v,
            "t": self.t,
            "_t0": self._t0
        }
        return state

    def restore_state(self, snapshot, t):
        """Restore component to a previous state from snapshot."""
        self.x = snapshot["x"]
        self.v = snapshot["v"]
        self.t = t
        self._t0 = snapshot["_t0"]
    
    def reset(self) -> None:
        super().reset()
        self.x = self.x0
        self._t0 = None
        self.inputs = {}
        self.outputs = {}

# -------------------------------------------------------------------
# Non-Rollback Test Component    
# -------------------------------------------------------------------
class NonRollbackComponent(CoSimComponent):
    """
    Simple component that does NOT support rollback.
    Used to test that supports_rollback returns False appropriately.
    """
    
    def __init__(self, name: str, value: float = 1.0):
        super().__init__(name)
        self.value = value
        
    def _initialize_component(self, t0: float) -> None:
        self.output_specs = {
            "y": PortSpec(name="y", type=PortType.REAL, direction="out", unit="1", description="Output")
        }
        self._initialize_ports_from_specs()
        
    def _do_step_internal(self, t: float, dt: float) -> None:
        self.value += dt
        
    def _update_output_states(self, t: float) -> None:
        self.outputs["y"].set(Quantity(self.value, "1"), t=t)
        
    def set_state(self, state: Dict[str, Any], t: float) -> None:
        if "value" in state:
            val = state["value"]
            self.value = val.magnitude if isinstance(val, Quantity) else val
            
    def get_state(self) -> Dict[str, Any]:
        return {"value": Quantity(self.value, "1")}
    
    def reset(self) -> None:
        super().reset()
        self.value = 1.0
        self.inputs = {}
        self.outputs = {}

# -------------------------------------------------------------------
# FMU Pendulum Component with Rollback Support
# -------------------------------------------------------------------
class Pendulum(FMUComponent):
    """
    FMU-based pendulum component with rollback support.
    """
    def __init__(self, name, group = None):
        fmu_path = Path(__file__).parent.parent / "test_data" / "FMUs" / "Pendulum.fmu"
        super().__init__(name, fmu_path, group)

    def snapshot_state(self):
        """Create a snapshot of the current component state."""
        state = super().get_state()
        state["t"] = self.t
        return state

    def restore_state(self, snapshot, t):
        """Restore component to a previous state from snapshot."""
        self.t = t
        q0 = snapshot['q']['value']
        omega0 = snapshot['omega']['value']
        self._instance.reset()
        self._instance.instantiate()
        self._instance.setupExperiment(startTime=t)
        self._instance.enterInitializationMode()
        self.set_parameters(**{'q0': q0, 'omega0': omega0})
        self._apply_parameters_starts()
        self._apply_input_starts()
        self._instance.exitInitializationMode()

        self._update_output_states(t)
        self._record_outputs(t)
        
# -------------------------------------------------------------------
# Test Cases Simple Components
# -------------------------------------------------------------------
def test_rollback_support():
    rollback_comp = RollbackComponent('RollbackComp', x0=0.0, velocity=1.0)
    non_rollback_comp = NonRollbackComponent('NonRollbackComp', value=1.0)
    
    rollback_comp.initialize(t0=0.0)
    non_rollback_comp.initialize(t0=0.0)
    
    assert rollback_comp.supports_rollback
    assert not non_rollback_comp.supports_rollback

def test_snapshot_not_implemented():
    comp = NonRollbackComponent(name="NonRollback")
    comp.initialize(t0=0.0)
    
    with pytest.raises(NotImplementedError):
        comp.snapshot_state()

def test_restore_not_implemented():
    comp = NonRollbackComponent(name="NonRollback")
    comp.initialize(t0=0.0)
    
    with pytest.raises(NotImplementedError):
        comp.restore_state({}, t=0.0)

def test_rollback_functionality():
    comp = RollbackComponent('RollbackComp', x0=0.0, velocity=2.0)
    comp.initialize(t0=0.0)
    
    # Take initial snapshot
    snapshot1 = comp.snapshot_state()
    
    # Advance simulation
    comp._do_step_internal(t=0.0, dt=1.0)
    comp._update_output_states(t=1.0)
    
    # Take second snapshot
    snapshot2 = comp.snapshot_state()
    
    # Advance simulation again
    comp._do_step_internal(t=1.0, dt=1.0)
    comp._update_output_states(t=2.0)
    
    # Restore to first snapshot
    comp.restore_state(snapshot1, t=0.0)
    assert np.isclose(comp.x, 0.0)
    assert np.isclose(comp.t, 0.0)

    # Restore to second snapshot
    comp.restore_state(snapshot2, t=1.0)
    assert np.isclose(comp.x, 2.0)
    assert np.isclose(comp.t, 1.0)

def test_rollback_with_event_indicators():
    comp = RollbackComponent(name="Hybrid", x0=-2.0, velocity=1.0)
    comp.initialize(t0=0.0)
    
    # Add event indicator
    comp.add_event_indicator(
        name="x_zero",
        func=lambda c: c.x,
        direction=1
    )
    
    comp.do_step(t=0.0, dt=1.0)  # x = -1.0
    snapshot = comp.snapshot_state()
    indicators_at_snapshot = comp.evaluate_event_indicators()
    
    comp.do_step(t=1.0, dt=2.0)  # x = 1.0 (crosses zero)
    
    # Restore
    comp.restore_state(snapshot, t=1.0)
    indicators_after_restore = comp.evaluate_event_indicators()
    
    # Event indicators should evaluate to same values after restore
    assert abs(indicators_at_snapshot["x_zero"] - indicators_after_restore["x_zero"]) < 1e-10

# -------------------------------------------------------------------
# Test Cases Complex Components
# -------------------------------------------------------------------
def test_fmu_rollback_support():
    test_file_path = Path(__file__)
    pendulum = Pendulum(name="Pendulum")
    pendulum.initialize(t0=0.0)
    assert pendulum.supports_rollback

def test_fmu_rollback_functionality():
    # 1) Initialize Pendulum FMU
    pendulum = Pendulum(name="Pendulum")
    pendulum.set_parameters(q0=np.deg2rad(45.0), omega0=0.0)
    pendulum.initialize(t0=0.0)

    # 2) Take initial snapshot
    snapshot1 = pendulum.snapshot_state()
    outputs_initial = pendulum.get_outputs()
    initial_q = outputs_initial['q']
    initial_omega = outputs_initial['omega']
    assert np.isclose(initial_q, np.deg2rad(45.0))
    assert np.isclose(initial_omega, 0.0)

    # 3) Advance simulation
    pendulum.do_step(t=0.0, dt=1.0)
    snapshot2 = pendulum.snapshot_state()
    outputs_1 = pendulum.get_outputs()
    q_after_step1 = outputs_1['q']
    omega_after_step1 = outputs_1['omega']
    assert not np.isclose(q_after_step1, initial_q)
    assert not np.isclose(omega_after_step1, initial_omega)

    # 4) Advance simulation again
    pendulum.do_step(t=1.0, dt=1.0)
    outputs_2 = pendulum.get_outputs()
    q_after_step2 = outputs_2['q']
    omega_after_step2 = outputs_2['omega']
    assert not np.isclose(q_after_step2, q_after_step1)
    assert not np.isclose(omega_after_step2, omega_after_step1)

    # 5) Restore to first snapshot
    pendulum.restore_state(snapshot1, t=0.0)
    restored_q1 = pendulum.get_outputs()['q']
    restored_omega1 = pendulum.get_outputs()['omega']
    assert np.isclose(pendulum.t, 0.0)
    assert np.isclose(restored_q1, initial_q)
    assert np.isclose(restored_omega1, initial_omega)

    # 6) Restore to second snapshot
    pendulum.restore_state(snapshot2, t=1.0)
    outputs_2 = pendulum.get_outputs()
    restored_q2 = outputs_2['q']
    restored_omega2 = outputs_2['omega']
    assert np.isclose(restored_q2, q_after_step1)
    assert np.isclose(restored_omega2, omega_after_step1)

def test_fmu_rollback_and_continue():
    
    # First simulation run
    pendulum1 = Pendulum(name="Pendulum1")
    pendulum1.set_parameters(q0=np.deg2rad(30.0), omega0=0.0)
    pendulum1.initialize(t0=0.0)
    pendulum1.do_step(t=0.0, dt=0.5)
    pendulum1.do_step(t=0.5, dt=0.5)
    q_reference = pendulum1.get_outputs()['q']
    omega_reference = pendulum1.get_outputs()['omega']
    
    # Second simulation with rollback
    pendulum2 = Pendulum(name="Pendulum2")
    pendulum2.set_parameters(q0=np.deg2rad(30.0), omega0=0.0)
    pendulum2.initialize(t0=0.0)
    
    # Take snapshot, advance, then rollback and re-advance
    snapshot_t0 = pendulum2.snapshot_state()
    pendulum2.do_step(t=0.0, dt=2.0)  # Wrong step
    pendulum2.restore_state(snapshot_t0, t=0.0)  # Rollback
    pendulum2.do_step(t=0.0, dt=0.5)  # Correct step
    pendulum2.do_step(t=0.5, dt=0.5)  # Correct step
    
    # Results should match
    q_rollback = pendulum2.get_outputs()['q']
    omega_rollback = pendulum2.get_outputs()['omega']
    
    assert np.isclose(q_reference, q_rollback, rtol=1e-6), \
        f"Angle mismatch: reference={q_reference}, rollback={q_rollback}"
    assert np.isclose(omega_reference, omega_rollback, rtol=1e-6), \
        f"Velocity mismatch: reference={omega_reference}, rollback={omega_rollback}"
