from typing import Dict, Any, Optional
import numpy as np

from SysSimX.components.multi_comp import MultiComponent, Hysteresis
from SysSimX.components.fmu_comp import FMUComponent
from MyModels.FEM.fem_pendulum import FEMPendulum
from MyModels.OpenSim.opensim_pendulum import OpenSimPendulum

from IPython.display import display, Markdown
import ipywidgets as widgets
from ipywidgets import Layout, HBox, VBox, HTML

from time import sleep

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
                 initial_mode: str = "FEM"):
        # Initialize base class
        super().__init__(name="Pendulum", initial_mode=initial_mode, group="Plant")
        
        # Store components
        self._fem_comp = fem_comp
        self._opensim_comp = opensim_comp
        self._fmu_comp = fmu_comp
        self._register_models()
        
        # Configure mode switching
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
        Cycle through modes 4 times within simulation time.
        Each complete cycle goes: FEM → EQB → OpenSim
        Total: 12 intervals (3 modes × 4 cycles)
        """
        #return "OpenSim"
        interval = self._t_end / 12
        cycle_position = int(t / interval) % 3
        if cycle_position == 0:
            return "FEM"
        elif cycle_position == 1:
            return "EQB"
        else:
            return "OpenSim"
        
    def _gap_based_mode_selector(self, t: float, state: Dict[str, Any]) -> str:
        # 1) Get current angular position
        q = self.get_state()['q']['value']
        # 2) Update scene / gf_u of FEM Pendulum if FEM not active
        if self.active_mode != 'FEM':
            self._fem_comp.update_scene(q, self.t)
        # 3) Retrieve the current gap distance
        gap = self._fem_comp._get_contact_gap_distance()
        if gap < 0.01: return 'FEM'
        else: return 'OpenSim' 

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

            # Extract master parameters
            use_gravity = self.models['FEM']._use_gravity
            self._with_contact = self.models['FEM']._with_contact
            q0 = np.deg2rad(self.models['FEM'].init_params.angular_position_deg)
            omega0 = self.models['FEM'].init_params.angular_velocity
            mass = self.models['FEM'].mass
            inertia = self.models['FEM'].inertia
            length = np.sqrt(inertia / mass)  # Equivalent length
            
            self._t_end = self.models['FEM'].sim_params.t_end
        else:
            # Default parameters if FEM not available
            use_gravity = False
            self._with_contact = False
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
            self.models['OpenSim']._with_contact = self._with_contact
            self.models['OpenSim'].initialize(t0)

        # Synchronize FMU parameters
        if "EQB" in self.models:
            self.models["EQB"].parameters['q0'].start = q0
            self.models["EQB"].parameters['omega0'].start = omega0
            self.models["EQB"].parameters['m'].start = mass
            self.models["EQB"].parameters['L'].start = length
            self.models["EQB"].parameters['g'].start = 9.81 if use_gravity else 0.0
            self.models["EQB"].initialize(t0)
        
        if self._with_contact:
            self.mode_selector = self._gap_based_mode_selector
        else:
            self.mode_selector = self._time_based_mode_selector
        
        self.setup_simulation_monitoring()

    # Delegate to base class and/or components of multi component   
    def _do_step_internal(self, t, dt):
        super()._do_step_internal(t, dt)
        # Update Scene of FEM Pendulum if FEM Pendulum is not active
        if self.active_mode != "FEM":
            q = self.active_comp.get_outputs()['q']
            self._fem_comp.update_scene(q, t+dt)
            sleep(0.1)
        self._update_monitoring()
        return 
    
    def _update_output_states(self, t):
        return super()._update_output_states(t)
    
    def get_state(self):
        return self.active_comp.get_state()
    
    def set_state(self, state, t):
        self.active_comp.set_state(state, t)

    def reset(self):
        for comp in self.models.values():
            comp.reset()

    # ---- Simulation Monitoring ----
    def setup_simulation_monitoring(self):
        header = HTML("<h1 style='color:#1565c0; font-family:sans-serif; margin-bottom:10px; text-align:center;'>Simulation Diagnostics</h1>")

        state  = self.get_state()
        theta  = state['q']['value']
        omega  = state['omega']['value']
        alpha  = state['alpha']['value']
        torque = state['torque']['value']

        self._widget_time   = self._fem_comp.w_time
        self._widget_tau    = self._fem_comp.w_tau
        self._widget_mode   = widgets.Text(value=self.active_mode, description="Mode:", disabled=True)
        self._widget_ref    = widgets.FloatText(value=0.0, description='Ref. pos in deg', step=0.001, disabled=True)
        self._widget_theta  = widgets.FloatText(value=np.rad2deg(theta), description='Ang. Pos: θ in deg', step=0.001, disabled=True)
        self._widget_omega  = widgets.FloatText(value=omega, description='Ang. Vel: ω in rad/s', step=0.01, disabled=True)
        self._widget_alpha  = widgets.FloatText(value=alpha, description='Ang. Acc: α in rad/s²', step=0.01, disabled=True)
        self._widget_torque = widgets.FloatText(value=torque, description='Torque: Mz in Nm', step=0.01, disabled=True)
        self._widget_gap    = self._fem_comp.w_gap

        self._widgets = [self._widget_time, self._widget_tau,
                         self._widget_mode, self._widget_ref,
                         self._widget_theta, self._widget_omega,
                         self._widget_alpha, self._widget_torque,
                         self._widget_gap]

        h_box_time = HBox([self._widget_time, self._widget_tau])
        h_box_mode = HBox([self._widget_mode, self._widget_ref])
        h_box_state1 = HBox([self._widget_theta, self._widget_omega])
        h_box_state2 = HBox([self._widget_alpha, self._widget_torque])
        h_box_contact = HBox([self._widget_gap])
        if self._with_contact:
            self._hboxes = [h_box_time, h_box_mode, h_box_state1, h_box_state2, h_box_contact]
        else:
            self._hboxes = [h_box_time, h_box_mode, h_box_state1, h_box_state2]

        for w in self._widgets:
            w.layout.width = '450px'
            w.layout.margin = '8px 0px 8px 0px'
            w.layout.align_self = 'center'
            w.layout.display = 'flex'
            w.layout.flex_direction = 'column'
            w.style.description_width = '200px'
            w.style.font_weight = 'bold'
            w.style.font_size = '12px'
            w.style.background = '#f5f7fa'
            w.style.border = '1px solid #cfd8dc'
            w.style.border_radius = '8px'
            w.style.padding = '6px 12px'
            w.style.color = '#263238'
            w.style.text_align = 'right'

        # Create a vertical box layout to hold all widgets
        vbox = VBox([header] + self._hboxes,
                    layout=Layout(
                        width='920px',
                        display='flex',
                        flex_direction='column',
                        justify_content='center',
                        align_items='stretch',
                        margin='0 auto',
                        align_self='center'
                    ))

        display(vbox)

        if "FEM" in self.models:
            self._fem_comp.initialize_scene()
    
    def _update_monitoring(self):
        state  = self.get_state()
        theta  = state['q']['value']
        omega  = state['omega']['value']
        alpha  = state['alpha']['value']
        torque = state['torque']['value']

        self._widget_time.value = self.t
        self._widget_mode.value = self.active_mode
        self._widget_ref.value = np.rad2deg(0)
        self._widget_theta.value = np.rad2deg(theta)
        self._widget_omega.value = omega
        self._widget_alpha.value = alpha
        self._widget_torque.value = torque

        if self._with_contact:
            gap = self._fem_comp._get_contact_gap_distance()
            self._widget_gap.value = gap
