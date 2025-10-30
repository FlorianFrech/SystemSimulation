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
    """
    Implements a multi component for the pendulum model consisting of
     - equation-based Modelica Pendulum as FMUComponents
     - rigid-multi-body OpenSim model as OpenSimComponent
     - netgen/NGSolve 2D FEM pendulum model as FEMComponent
    This is examplary for a user defined class that defines the switching rule
    and state synchronization for interchangable components
    """
    models: Dict[str, Optional[CoSimComponent]]
    active_mode: str = ""
    active_comp: CoSimComponent = None

    #----------------------------------------------------------------------------
    # Construction and Initialization
    #----------------------------------------------------------------------------
    def __init__(self, 
                 fem_comp: FEMPendulum = None,
                 opensim_comp: OpenSimPendulum = None,
                 fmu_comp: FMUComponent = None):
        super().__init__(name="Pendulum", group="Plant")

        self.models = {
            "FEM": fem_comp,
            "OpenSim": opensim_comp,
            "EQB": fmu_comp
        }

        self.active_key = "OpenSim"
        self.active_comp = self.models[self.active_key]

        self._check_port_specs()

    #----------------------------------------------------------------------------
    # Construction and Initialization
    #----------------------------------------------------------------------------
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
        self.models["EQB"].parameters['q0'].start = q0
        self.models["EQB"].parameters['omega0'].start = omega0
        self.models["EQB"].parameters['m'].start = mass
        self.models["EQB"].parameters['L'].start = length
        self.models["EQB"].parameters['g'].start = 9.81 if use_gravity else 0.0
        self.models["EQB"].initialize(t0)

        self._t_end = self.models['FEM'].sim_params.t_end

        self._update_output_states(t0)

    #----------------------------------------------------------------------------
    # Inputs / Outputs Handling
    #----------------------------------------------------------------------------
    def set_inputs(self, signals, t = None):
        for comp in self.models.values():
            comp.set_inputs(signals, t)
        #self.active_comp.set_inputs(signals, t)
    
    def get_outputs(self):
        return {name: out_port.get() for name, out_port in self.outputs.items() if out_port.get() is not None }
    
    def _update_output_states(self, t: float):
        state = self.get_state()
        q = state['q']['value'] * ureg(state['q']['unit'])
        omega = state['omega']['value'] * ureg(state['omega']['unit'])
        alpha = state['alpha']['value'] * ureg('rad/s**2')
        self.outputs['q'].set(q, t=t)
        self.outputs['omega'].set(omega, t)
        self.outputs['alpha'].set(alpha, t)

    #----------------------------------------------------------------------------
    # State Handling
    #----------------------------------------------------------------------------
    def set_state(self, state: Dict[str, Any], t: float):
        self.active_comp.set_state(state, t)

    def get_state(self):
        if self.active_comp is not None:
            return self.active_comp.get_state()
        return None
    
    #----------------------------------------------------------------------------
    # Lifecycle
    # ---------------------------------------------------------------------------
    def reset(self):
        for model in self.models.values():
            model.reset()

    #----------------------------------------------------------------------------
    # Core: Switching of the active component and synchronizing from active to new
    # ---------------------------------------------------------------------------
    def do_step(self, t, dt):        
        #self.active_comp.do_step(t, dt)
        #Check for mode switch
        self.new_key = self._time_dependent_model_selection(t)
        if self.new_key != self.active_key:
            self.synch_model(t)
        self.active_comp.do_step(t, dt)
        self._update_output_states(t+dt)
    
    def check_and_switch(self, t:float) -> None:
        self.new_key = self._time_dependent_model_selection(t)
        if self.new_key != self.active_key:
            self.synch_model(t)

    def synch_model(self, t):
        print(60 * "-")
        print(f"Switch from {self.active_key} to {self.new_key} at time {t:.3f}s")
        state = self.active_comp.get_state()
            
        # Print state for debugging
        print(f"  1) State: q={state['q']['value']:.4f} rad, w={state['omega']['value']:.4f} rad/s, a={state['torque']['value']:.4f} rad/s²")
        
        if self.new_key == "EQB":
            # FMU expects initial condition format with specific parameter names
            fmu_state = {
                'q0': state['q'],          # Pass the full dict with value and unit
                'omega0': state['omega'],  # Pass the full dict with value and unit  
                'torque': state['torque']  # Current torque
            }
            self.models["EQB"].set_state(fmu_state, t)
        elif self.new_key == "OpenSim":
            # OpenSim may need consistent sign convention
            opensim_state = {
                'q': state['q'],
                'omega': state['omega'],
                'torque': state['torque']  # Keep same sign for now
            }
            self.models['OpenSim'].set_state(opensim_state, t)
        else:
            # FEM and other models use standard format
            self.models[self.new_key].set_state(state, t)
        self.active_key = self.new_key
        self.active_comp = self.models[self.active_key]
        state = self.active_comp.get_state()
        print(f"  2) State: q={state['q']['value']:.4f} rad, w={state['omega']['value']:.4f} rad/s, a={state['torque']['value']:.4f} rad/s²")

    def _time_dependent_model_selection(self, t: float) -> str:
        # split simulation into 6 equal intervals so each mode appears twice
        interval = self._t_end / 6
        if t < interval:
            return "FEM"
        elif t < 2 * interval:
            return "EQB"
        elif t < 3 * interval:
            return "OpenSim"
        elif t < 4 * interval:
            return "EQB"
        elif t < 5 * interval:
            return "OpenSim"
        else:
            return "FEM"