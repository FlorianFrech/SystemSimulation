from typing import Dict, Any, Optional
import numpy as np

from SysSimX.components.multi_comp import MultiComponent, Hysteresis
from SysSimX.components.fmu_comp import FMUComponent
from MyModels.FEM.fem_pendulum import FEMPendulum
from MyModels.OpenSim.opensim_pendulum import OpenSimPendulum

class PendulumMultiComp(MultiComponent):
    """
    Multi pendulum model with automatic mode switching.
    
    Combines:
    - FEM: Continuum mechanics (NGSolve)
    - OpenSim: Rigid multi-body dynamics (Simbody)
    - EQB: Equation-based model (Modelica FMU)
    """

    def __init__(self,
                 fem_comp: Optional[FEMPendulum] = None,
                 opensim_comp: Optional[OpenSimPendulum] = None,
                 fmu_comp: Optional[FMUComponent] = None,
                 initial_mode: str = "OpenSim"):
        # Initialize base class
        super().__init__(name="Pendulum", initial_mode=initial_mode, group="Plant")
        
        # Store components
        self._fem_comp = fem_comp
        self._opensim_comp = opensim_comp
        self._fmu_comp = fmu_comp
        self._register_models()
        
        # Configure mode switching
        self.mode_selector = self._time_based_mode_selector
        self.hysteresis = Hysteresis(dwell_time=0.05)
        
        # Simulation end time (for mode selector)
        self._t_end = 1.0

        # Set the active component
        self.active_comp = self.models[self.active_mode]

        # Unify ports
        self._unify_ports()

    # ---- Model Registration ----
    def _register_models(self) -> None:
        """Register all available pendulum models."""
        self.models = {
            "FEM": self._fem_comp,
            "OpenSim": self._opensim_comp,
            "EQB": self._fmu_comp
        }

    # ---- State Adaptation ----
    def _adapt_state(self, state: Dict[str, Any], target_mode: str) -> Dict[str, Any]:
        """
        Translate state between component-specific formats.
        
        Standard format (FEM, OpenSim):
            {'q': {'value': ..., 'unit': 'rad'}, 'omega': {...}, 'torque': {...}}
        
        FMU format (initial conditions):
            {'q0': {'value': ..., 'unit': 'rad'}, 'omega0': {...}, 'torque': {...}}
        """
        if target_mode == "EQB":
            # FMU expects initial condition parameter names
            return {
                'q0': state['q'],
                'omega0': state['omega'],
                'torque': state.get('torque', {'value': 0.0, 'unit': 'N*m'})
            }
        # FEM and OpenSim use standard format
        return state

    # ---- Mode Selection Strategy ----
    def _time_based_mode_selector(self, t: float, state: Dict[str, Any]) -> str:
        """
        Cycle through modes in equal time intervals.
        """
        interval = self._t_end / 6
        
        if t < interval:
            return "FEM"
        elif t < 2 * interval:
            return "EQB"
        elif t < 3 * interval:
            return "FEM"
        elif t < 4 * interval:
            return "EQB"
        elif t < 5 * interval:
            return "OpenSim"
        else:
            return "FEM"

    # ----Initialization with Parameter Propagation ----
    def initialize(self, t0: float) -> None:
        # Call base class initialization (sets active component, unifies ports)
        """
        Initialize with parameter synchronization across models.
        
        Strategy:
        1. FEM provides master parameters (mass, inertia, geometry)
        2. Derive equivalent parameters for OpenSim and FMU
        3. Initialize all models with consistent parameters
        """
        # Initialize FEM first (master parameters)
        if "FEM" in self.models:
            self.models['FEM'].initialize(t0)
            self.models['FEM'].setup_simulation_diagnostics()
            
            # Extract master parameters
            use_gravity = self.models['FEM']._use_gravity
            with_contact = self.models['FEM']._with_contact
            q0 = np.deg2rad(self.models['FEM'].init_params.angular_position_deg)
            omega0 = self.models['FEM'].init_params.angular_velocity
            mass = self.models['FEM'].mass
            inertia = self.models['FEM'].inertia
            length = np.sqrt(inertia / mass)  # Equivalent length
            
            self._t_end = self.models['FEM'].sim_params.t_end
        else:
            # Default parameters if FEM not available
            use_gravity = False
            with_contact = False
            q0 = 0.0
            omega0 = 0.0
            mass = 1.0
            length = 0.4

        # Synchronize OpenSim parameters
        if "OpenSim" in self.models:
            self.models['OpenSim'].parameters['InitialConditions']['q0'] = q0
            self.models['OpenSim'].parameters['InitialConditions']['omega0'] = omega0
            self.models['OpenSim'].parameters['Model']['mass'] = mass
            self.models['OpenSim'].parameters['Model']['length'] = length
            self.models['OpenSim']._use_gravity = use_gravity
            self.models['OpenSim']._with_contact = with_contact
            self.models['OpenSim'].initialize(t0)

        # Synchronize FMU parameters
        if "EQB" in self.models:
            self.models["EQB"].parameters['q0'].start = q0
            self.models["EQB"].parameters['omega0'].start = omega0
            self.models["EQB"].parameters['m'].start = mass
            self.models["EQB"].parameters['L'].start = length
            self.models["EQB"].parameters['g'].start = 9.81 if use_gravity else 0.0
            self.models["EQB"].initialize(t0)

    # Delegate to base class and/or components of multi component   
    def _do_step_internal(self, t, dt):
        return super()._do_step_internal(t, dt)
    
    def _update_output_states(self, t):
        return super()._update_output_states(t)
    
    def get_state(self):
        return self.active_comp.get_state()
    
    def set_state(self, state, t):
        self.active_comp.set_state(state, t)

    def reset(self):
        for comp in self.models.values():
            comp.reset()