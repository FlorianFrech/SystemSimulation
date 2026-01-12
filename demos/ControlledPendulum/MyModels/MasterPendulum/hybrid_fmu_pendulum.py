from typing import Any, Dict, Optional, List
from pathlib import Path

from SysSimX.core.base import CoSimComponent
from SysSimX.core.port import PortSpec, PortType
from SysSimX.core.events import Event

from SysSimX.system.connection import Connection, EventConnection
from SysSimX.system.system import System

from SysSimX.components.fmu_comp import FMUComponent


#----------------------------------------------------------------------------
# Hybrid FMU Pendulum Component
#----------------------------------------------------------------------------  
class Pendulum(FMUComponent):
    """
    FMU-based pendulum component with rollback support.
    """
    def __init__(self, name, group = "Pendulum", solver: str = "Cvode"):
        # Select FMU based on solver choice
        if solver == "Euler":
            fmu_path = Path.cwd().parent / "FMUs" / "Pendulum_Euler.fmu"
        elif solver == "Cvode":
            fmu_path = Path.cwd().parent / "FMUs" / "Pendulum_Cvode.fmu"
        self.solver = solver
        
        # Initialize base class
        super().__init__(name, fmu_path, group)

        # Add event input port for omega inversion
        self.input_specs.update({
            'omega_invert': PortSpec('omega_invert', PortType.EVENT, "in")
        })

    # Snapshot and restore state methods for rollback
    def snapshot_state(self):
        if self.solver == "Euler":
            return self._instance.getFMUState()
        elif self.solver == "Cvode":
            return super().get_state()

    def restore_state(self, snapshot, t):
        self.t = t
        if self.solver == "Euler":
            self._instance.setFMUState(snapshot)
        elif self.solver == "Cvode":        
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

    # Handle events: invert omega on wall hit
    def _handle_events_internal(self, event_names, t):
        if "wall_hit" not in event_names:
            return
        restitution = 1
        output = self.get_outputs()
        q0 = output['q'].magnitude
        omega0 = -restitution * output['omega'].magnitude

        self._instance.reset()
        self._instance.instantiate()
        self._instance.setupExperiment(startTime=t)
        self._instance.enterInitializationMode()
        self.set_parameters(**{'q0': q0, 'omega0': omega0})
        self._apply_parameters_starts()
        self._apply_input_starts()
        self._instance.exitInitializationMode()

        self._update_output_states(t, event_names)
        self._record_outputs(t)
    
    def _update_output_states(self, t: Optional[float]=None, event_names: Optional[List[str]]=[]):
        super()._update_output_states(t)
        if event_names:
            for event_name in event_names:
                if event_name in self.output_specs.keys():
                    self.outputs[event_name].set(value=True, t=t)
        else:
            for out_port in self.outputs.values():
                if out_port.spec.type == PortType.EVENT:
                    out_port.set(value=False, t=t)