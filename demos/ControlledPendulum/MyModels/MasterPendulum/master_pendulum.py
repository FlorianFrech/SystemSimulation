from typing import Dict, Any, Optional, List
import numpy as np

from SysSimX.core.base import CoSimComponent
from SysSimX.core.port import PortType
from SysSimX.core.multi_comp import MultiComponent, Hysteresis
from SysSimX.components.fmu_comp import FMUComponent
from SysSimX.core.events import Event, EventIndicator
from MyModels.EQB.hybrid_fmu_pendulum import Pendulum as EQBPendulum
from MyModels.FEM.fem_pendulum import FEMPendulum
from MyModels.OpenSim.opensim_pendulum import OpenSimPendulum

from IPython.display import display, Markdown
import ipywidgets as widgets
from ipywidgets import Layout, HBox, VBox, HTML
from traitlets import HasTraits, Float, Unicode

#----------------------------------------------------------------------------
# Pendulum Monitoring State
#----------------------------------------------------------------------------  
class PendulumMonitoringState(HasTraits):
    """
    Observable state of the pendulum for monitoring.
    """
    # Simulation status
    time = Float(0.0)
    dt = Float(0.01)
    mode = Unicode('FEM')
    
    # Input signals
    torque = Float(0.0)
    
    # Output signals
    q = Float(0.0)
    omega = Float(0.0)
    alpha = Float(0.0)
    
    # Optional: Contact
    gap = Float(0.0)

#----------------------------------------------------------------------------
# Master Pendulum CoSimulation Component
#----------------------------------------------------------------------------  
class MasterPendulum(MultiComponent):
    """
    Master Pendulum CoSimulation Component.
    Contains at least one of the following sub-components:
    - FEM: Continuum mechanics (NGSolve)
    - OpenSim: Rigid multi-body dynamics (Simbody)
    - EQB: Equation-based model (Modelica FMU)
    """

    def __init__(self,
                 fem_comp: Optional[FEMPendulum] = None,
                 opensim_comp: Optional[OpenSimPendulum] = None,
                 fmu_comp: Optional[EQBPendulum] = None,
                 initial_mode: str = "EQB"):
        # Initialize base class
        super().__init__(name="Pendulum", initial_mode=initial_mode, group="Plant")
        
        # Store components
        if fem_comp is None and opensim_comp is None and fmu_comp is None:
            raise ValueError("At least one pendulum component must be provided.")
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

        # Create monitoring state
        self.monitoring_state = PendulumMonitoringState()

        # Store widget references
        self._widget_links = []

    #----------------------------------------------------------------------------
    # Model Registration
    #---------------------------------------------------------------------------- 
    def _register_models(self) -> None:
        """Register all available pendulum models."""
        self.models = {
                        "FEM": self._fem_comp,
                        "OpenSim": self._opensim_comp,
                        "EQB": self._fmu_comp
                    }

    #----------------------------------------------------------------------------
    # State Adaptation
    #---------------------------------------------------------------------------- 
    def _adapt_state(self, state: Dict[str, Any], target_mode: str) -> Dict[str, Any]:
        """
        Translate state between component-specific formats.
        
        Standard format (FEM, OpenSim):
            {'q': {'value': ..., 'unit': 'rad'}, 'omega': {...}, 'torque': {...}}
        
        FMU format (initial conditions):
            {'q0': {'value': ..., 'unit': 'rad'}, 'omega0': {...}, 'torque': {...}}
        """        
        if target_mode == "EQB":
            return {
                'q0': state['q'],
                'omega0': state['omega'],
                'torque': state['torque']
            }
        return state

    #----------------------------------------------------------------------------
    # Mode Selection Logic
    #---------------------------------------------------------------------------- 
    def _time_based_mode_selector(self, t: float, state: Dict[str, Any]) -> str:
        """
        Cycle through modes 4 times within simulation time.
        Each complete cycle goes: FEM → EQB → OpenSim
        Total: 12 intervals (3 modes × 4 cycles)
        """
        interval = self._t_end / 12
        cycle_position = int(t / interval) % 3
        if cycle_position == 0:
            return "OpenSim"
        elif cycle_position == 1:
            return "FEM"
        else:
            return "EQB"
        
    def _gap_based_mode_selector(self, t: float, state: Dict[str, Any]) -> str:      
        # Get current angular position from active component
        current_state = self.get_state()
        q = current_state['q']['value']

        #return 'EQB'  # TEMPORARY OVERRIDE FOR TESTING

        if t < 0.7:
            return 'EQB'
        
        # Handle Quantity objects (with units)
        if hasattr(q, 'magnitude'):
            q = q.magnitude
        
        # Convert to degrees for threshold comparison
        q_deg = np.rad2deg(q)
        
        # Use absolute value for symmetric contact detection
        q_abs = abs(q_deg)
        
        # Mode selection based on angular position thresholds
        if q_abs > 15:
            return 'EQB'
        elif q_abs > 5:
            return 'OpenSim'
        else:
            return 'FEM'

    #----------------------------------------------------------------------------
    # Initialization Logic
    #---------------------------------------------------------------------------- 
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
            self._t_end = self.models['FEM'].sim_params.t_end
            
            use_gravity = self.models['FEM']._use_gravity
            self._with_contact = self.models['FEM']._with_contact
            self._animate = self.models['FEM'].anim_params.animate
           
            q0 = np.deg2rad(self.models['FEM'].init_params.angular_position_deg)
            omega0 = self.models['FEM'].init_params.angular_velocity
            
            length = self.models['FEM']._equivalent_length
            inertia = self.models['FEM'].inertia
            mass = self.models['FEM'].mass
            
        else:
            # Default parameters if FEM not available
            use_gravity = False
            self._with_contact = False
            q0 = 0.0
            omega0 = 0.0
            mass = 1.0
            length = 0.4
            inertia = 0.01

        # Synchronize OpenSim parameters
        if "OpenSim" in self.models:
            self.models['OpenSim'].parameters['InitialConditions']['q0'] = q0
            self.models['OpenSim'].parameters['InitialConditions']['omega0'] = omega0
            self.models['OpenSim'].parameters['Model']['mass'] = mass
            self.models['OpenSim'].parameters['Model']['length'] = length
            self.models['OpenSim'].parameters['Model']['inertia'] = inertia - mass * length**2
            self.models['OpenSim']._use_gravity = use_gravity
            self.models['OpenSim']._with_contact = self._with_contact
            self.models['OpenSim'].initialize(t0)

        # Synchronize FMU parameters
        if "EQB" in self.models:
            self.models["EQB"].parameters['q0'].start = q0
            self.models["EQB"].parameters['omega0'].start = omega0
            self.models["EQB"].parameters['m'].start = mass
            self.models["EQB"].parameters['L'].start = length
            self.models["EQB"].parameters['inertia'].start = inertia
            self.models["EQB"].parameters['g'].start = 9.81 if use_gravity else 0.0
            self.models["EQB"].initialize(t0)
        
        if self._with_contact:
            self.mode_selector = self._gap_based_mode_selector
        else:
            self.mode_selector = self._time_based_mode_selector
        
        ### TESTING ONLY ###
        self.mode_selector = self._gap_based_mode_selector
        
        self.setup_monitoring()

    #----------------------------------------------------------------------------
    # Setup Event Detection
    #----------------------------------------------------------------------------
    def setup_event_detection(self) -> None:
        """
        Setup event indicators that work across all models.
        Call this AFTER initialize().
        """
        def wall_contact_indicator(comp: CoSimComponent) -> float:
            """Universal event indicator that works for any sub-component."""
            # Access through component's outputs (unified interface)
            q = comp.get_outputs().get('q')
            if hasattr(q, 'magnitude'):
                q = q.magnitude
            return q - 0.0  # Wall at q=0
        
        # Add to all models that support rollback
        event_name = 'wall_hit'
        direction = -1  # Detect falling edge (approaching from positive q)
        
        for mode, comp in self.models.items():
            if comp and comp.supports_rollback:
                comp.add_event_indicator(event_name, wall_contact_indicator, direction)
        
        # Subscribe to the event
        event = Event(name=event_name, source=self.name, direction=direction)
        self.subscribe_event(event)
        
    #----------------------------------------------------------------------------
    # Time Stepping Logic
    #----------------------------------------------------------------------------  
    def _update_output_states(self, t: Optional[float]=None, event_names: Optional[List[str]]=[]):
        super()._update_output_states(t, event_names=event_names)

        # 2) Update monitoring widgets (only if t is provided)
        if t is not None:
            dt = t - self.t if hasattr(self, 't') else 0.0
            self._update_monitoring(t, dt)
        
        # 3) Update FEM scene if not active (for visualization consistency)
        if self.active_mode != "FEM" and self._fem_comp.anim_params.animate:
            q = self.active_comp.get_outputs()['q']
            if t is not None:
                self._fem_comp.update_scene(q, t)

    #----------------------------------------------------------------------------
    # Monitoring interface methods
    #----------------------------------------------------------------------------
    def _initialize_widgets(self):
        self.widgets = {}
        # Input and output monitoring widgets
        for name, spec in self.input_specs.items():
            if spec.type == PortType.REAL:
                self.widgets[name] = widgets.FloatText(value=0.0,
                                                        description=f'{name} ({spec.unit}):',
                                                        step=0.01,
                                                        disabled=True)
        for name, spec in self.output_specs.items():
            if spec.type == PortType.REAL:
                self.widgets[name] = widgets.FloatText(value=0.0,
                                                        description=f'{name} ({spec.unit}):',
                                                        step=0.01,
                                                        disabled=True)
        # Additional simulation monitoring widgets
        self.widgets['time'] = widgets.FloatText(value=0,
                                        description=f'Time: t / {self._fem_comp.sim_params.t_end} s',
                                        step=0.001,
                                        disabled=True)

        self.widgets['dt']  = widgets.FloatText(value=self._fem_comp.sim_params.tau,
                                        description='Time Step: dt in s',
                                        step=0.0001,
                                        disabled=True)
        
        self.widgets['mode'] = widgets.Text(value=self.active_mode,
                                             description='Simulation Mode:',
                                             disabled=True)
        if self._with_contact:
            self.widgets['gap']  = widgets.FloatText(value=0.0,
                                            description='Min. Gap in m',
                                            step=0.0001,
                                            disabled=True)
        self._format_widgets()
        self._link_widgets_to_state()
    
    def _format_widgets(self):
        for w in self.widgets.values():
            w.layout.width = '300px'
            w.layout.margin = '5px'
            w.style.description_width = '150px'
            
            w.readout_format = '.5g'
            
            # Professional color scheme
            w.style.font_family = 'Inter' #, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
            w.style.font_size = '13px'
            w.style.font_weight = '500'
            
            # Modern input field styling
            w.style.background = 'white'
            w.style.border = '1px solid #e0e0e0'
            w.style.border_radius = '4px'
            w.style.padding = '8px 12px'
            
            # Text styling
            w.style.color = '#424242'
            w.style.description_color = '#757575'

    def _link_widgets_to_state(self):
        """
        Link widgets to monitoring state for automatic updates.
        """
        for link in self._widget_links:
            link.unlink()
        self._widget_links.clear()

        link_mappings = {
            'time': 'time',
            'dt': 'dt',
            'mode': 'mode',
            'torque': 'torque',
            'q': 'q',
            'omega': 'omega',
            'alpha': 'alpha',
        }
        if self._with_contact:
            link_mappings['gap'] = 'gap'
        
        for widget_name, state_attr in link_mappings.items():
            if widget_name in self.widgets:
                link = widgets.dlink((self.monitoring_state, state_attr),
                                     (self.widgets[widget_name], 'value'))
                self._widget_links.append(link)
                
    def setup_monitoring(self) -> None:
        """Setup monitoring interface with grouped widgets."""
        self._initialize_widgets()
        
        # Create styled headers
        main_header = HTML(
            "<h3 style='color:#1565c0; font-family:Inter, sans-serif; margin:15px 0 20px 0; "
            "text-align:center; font-weight:600; border-bottom:2px solid #1565c0; padding-bottom:10px;'>"
            "Pendulum Monitoring</h3>"
        )
        
        # Group headers with modern styling
        header_style = (
            "color:#424242; font-family:Inter, sans-serif; font-size:14px; "
            "font-weight:600; margin:15px 0 8px 0; padding:8px 12px; "
            "background:linear-gradient(to right, #f5f5f5, #ffffff); "
            "border-left:4px solid #1565c0; border-radius:4px;"
        )
        
        input_header = HTML(f"<div style='{header_style} text-align:center;'>Input Signals</div>")
        output_header = HTML(f"<div style='{header_style} text-align:center;'>Output Signals</div>")
        simulation_header = HTML(f"<div style='{header_style} text-align:center;'>Simulation Status</div>")
        
        # Group widgets
        input_widgets = [self.widgets[name] for name in self.input_specs.keys() if name in self.widgets]
        output_widgets = [self.widgets[name] for name in self.output_specs.keys() if name in self.widgets]
        simulation_widgets = [self.widgets['time'], self.widgets['dt'], self.widgets['mode']]
        if self._with_contact:
            simulation_widgets.append(self.widgets['gap'])
        
        # Create widget groups with padding
        input_box = VBox([input_header] + input_widgets, layout=Layout(margin='0 0 20px 10px'))
        output_box = VBox([output_header] + output_widgets, layout=Layout(margin='0 0 20px 10px'))
        simulation_box = VBox([simulation_header] + simulation_widgets, layout=Layout(margin='0 0 20px 10px'))
        
        # Widget Box
        widget_box = HBox([simulation_box, input_box, output_box],
                          layout=Layout(justify_content='space-between'))

        # Create main container with sections
        self.monitoring_display = VBox([
            main_header,
            widget_box,
        ], layout=Layout(
            padding='20px',
            border='1px solid #e0e0e0',
            border_radius='8px',
            background='#fafafa',
            width='fit-content',
            margin='0 auto',
            height='auto',
            box_shadow='0 4px 8px rgba(0, 0, 0, 0.1)',
        ))
        
        # Stress visualization header
        self.scene_header = HTML(
            "<h3 style='color:#1565c0; font-family:Inter, sans-serif; margin:15px 0 20px 0; "
            "text-align:center; font-weight:600; border-bottom:2px solid #1565c0; padding-bottom:10px;'>"
            "Stress Visualization (N/m²)</h3>"
        )
    
    def _update_monitoring(self, t: float, dt: float) -> None:
        """Update monitoring widgets with current values."""
        state = self.get_state()
        self.monitoring_state.time = t + dt
        self.monitoring_state.dt = dt
        self.monitoring_state.mode = self.active_mode
        self.monitoring_state.torque = state['torque']['value']
        self.monitoring_state.q = state['q']['value']
        self.monitoring_state.omega = state['omega']['value']
        self.monitoring_state.alpha = state['alpha']['value']
        
        if self._with_contact:
            self.monitoring_state.gap = self._fem_comp._get_contact_gap_distance()

    def display_monitoring(self):
        """Display the monitoring interface."""
        display(self.monitoring_display)
        if self._fem_comp is not None:
            display(self.scene_header)
            self._fem_comp.initialize_scene()

    def __del__(self):
        for link in self._widget_links:
            link.unlink()