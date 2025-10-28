from __future__ import annotations
from typing import Dict, Any, Optional, Callable, Tuple
from enum import Enum

import numpy as np

from SysSimX.core.base import CoSimComponent
from SysSimX.core.multi_comp import MultiComponent
from SysSimX.components.fmu_comp import FMUComponent
from MyModels.FEM.fem_pendulum import FEMPendulum
from MyModels.OpenSim.opensim_pendulum import OpenSimPendulum
from SysSimX.core.port import PortSpec, PortState, PortType
from SysSimX.utilities.units import ureg, Quantity

class PendulumMultiComp(CoSimComponent):
    models: Dict[str, CoSimComponent] = {}
    active_mode: str = ""
    active_comp: CoSimComponent = None

    def __init__(self, 
                 fem_comp: FEMPendulum = None,
                 opensim_comp: OpenSimPendulum = None,
                 fmu_comp: FMUComponent = None):
        super().__init__(name="Pendulum", group="Plant")

        self.models = {
            "FEM": fem_comp,
            "OpenSim": opensim_comp,
            "FMU": fmu_comp
        }

        self.active_key = "OpenSim"
        self.active_comp = self.models[self.active_key]

        self._check_port_specs()

    def _check_port_specs(self):
        """
        Ensure all models have consistent port specifications.
        """
        # Check input and output specs
        self.input_specs = self.active_comp.input_specs
        self.output_specs = self.active_comp.output_specs

        self.inputs = {name: PortState(spec) for name, spec in self.input_specs.items()}
        self.outputs = {name: PortState(spec) for name, spec in self.output_specs.items()}
        
        # TODO: Implement thorough checks across all models

    def initialize(self, t0):
        # Initialize FEM model
        self.models['FEM'].initialize(t0)
        self.models['FEM'].setup_simulation_diagnostics()

        # Get master parameters from FEM model
        use_gravity = self.models['FEM']._use_gravity
        with_contact = self.models['FEM']._with_contact

        q0 = np.deg2rad(self.models['FEM'].init_params.angular_position_deg)
        omega0 = self.models['FEM'].init_params.angular_velocity
        mass = self.models['FEM'].mass
        inertia = self.models['FEM'].inertia

        # Calculate equivalent parameters for other models
        length = np.sqrt(inertia / mass)

        # Set parameters for OpenSim model
        self.models['OpenSim'].parameters['InitialConditions']['q0'] = q0
        self.models['OpenSim'].parameters['InitialConditions']['omega0'] = omega0
        self.models['OpenSim'].parameters['Model']['mass'] = mass
        self.models['OpenSim'].parameters['Model']['length'] = length
        self.models['OpenSim']._use_gravity = use_gravity
        self.models['OpenSim']._with_contact = with_contact
        self.models['OpenSim'].initialize(t0)

        # Set parameters for FMU model
        self.models['FMU'].parameters['q0'].start = q0
        self.models['FMU'].parameters['omega0'].start = omega0
        self.models['FMU'].parameters['m'].start = mass
        self.models['FMU'].parameters['L'].start = length
        self.models['FMU'].parameters['g'].start = 9.81 if use_gravity else 0.0
        self.models['FMU'].initialize(t0)

        self._t_end = self.models['FEM'].sim_params.t_end
    
    def set_inputs(self, signals, t = None):
        self.active_comp.set_inputs(signals, t)

    def get_state(self):
        self.active_comp.get_state()

    def set_state(self, state: Dict[str, Any], t: float):
        self.active_comp.set_state(state, t)

    def reset(self):
        for model in self.models.values():
            model.reset()

    def do_step(self, t, dt):
        # Check for mode switch
        self.new_key = time_dependent_model_selection(t, self._t_end)
        if self.new_key != self.active_key:
            self.synch_model(t)
            self.active_key = self.new_key
            self.active_comp = self.models[self.active_key]
        
        self.active_comp.do_step(t, dt)


    def synch_model(self, t):
        print(f"Switch from {self.active_key} to {self.new_key} at time {t:.3f}s")
        state = self.active_comp.get_state()
        if self.new_key == "FMU":
            fmu_state = {
                'q0': state['q'],
                'omega0': state['omega'],
                'torque': state['torque']
            }
            self.models['FMU'].set_state(fmu_state, t)
        elif self.new_key == "OpenSim":
            opensim_state = {
                'q': state['q'],
                'omega': state['omega'],
                'torque': {'value': state['torque']['value'] * -1}
            }
            self.models['OpenSim'].set_state(opensim_state, t)
        else:
            self.models[self.new_key].set_state(state, t)

    def get_outputs(self):
        return self.active_comp.get_outputs()
        
def time_dependent_model_selection(t: float, t_end: float) -> str:
    # split simulation into 6 equal intervals so each mode appears twice
    interval = t_end / 6
    if t < interval:
        return "FMU"
    elif t < 2 * interval:
        return "OpenSim"
    elif t < 3 * interval:
        return "FEM"
    elif t < 4 * interval:
        return "OpenSim"
    elif t < 5 * interval:
        return "FMU"
    else:
        return "OpenSim"
    
