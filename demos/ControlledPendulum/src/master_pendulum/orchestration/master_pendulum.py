from typing import Any, Literal

import ipywidgets as widgets
import numpy as np
from IPython.display import display
from ipywidgets import HTML, HBox, Layout, VBox
from traitlets import Float, HasTraits, Unicode

from syssimx.core.multi_comp import Hysteresis, MultiComponent
from syssimx.core.port import PortType

from ..components import FEMPendulum, FMUPendulum, OpenSimPendulum

MODES: Literal["FEM", "OpenSim", "FMU"] = ("FEM", "OpenSim", "FMU")

def is_valid_mode(mode: str) -> bool:
    return mode in MODES

# ----------------------------------------------------------------------------
# Pendulum Monitoring State
# ----------------------------------------------------------------------------
class PendulumMonitoringState(HasTraits):
    """
    Observable state of the pendulum for monitoring.
    """

    # Simulation status
    time = Float(0.0)
    dt = Float(0.01)
    mode = Unicode("FEM")

    # Input signals
    tau = Float(0.0)

    # Output signals
    theta = Float(0.0)
    omega = Float(0.0)
    alpha = Float(0.0)

    # Optional: Contact
    gap = Float(0.0)


# ----------------------------------------------------------------------------
# Master Pendulum CoSimulation Component
# ----------------------------------------------------------------------------
class MasterPendulum(MultiComponent):

    def __init__(
        self,
        name: str = "MasterPendulum",
        initial_mode: Literal["FEM", "OpenSim", "FMU"] = "FMU",
        fmu_solver: Literal["cvode", "euler"] = "cvode",):

        # Check initial mode validity
        if not is_valid_mode(initial_mode):
            raise ValueError(f"{name}: Invalid initial mode '{initial_mode}'."
                             f" Must be one of {MODES}.")

        # Instantiate sub-components before delegating to the base class
        self.fmu = FMUPendulum(name="FMU_Pendulum", solver=fmu_solver)
        self.fem = FEMPendulum(name="FEM_Pendulum")
        self.opensim = OpenSimPendulum(name="OpenSim_Pendulum")

        super().__init__(
            name=name,
            models={
                "FEM": self.fem,
                "OpenSim": self.opensim,
                "FMU": self.fmu,
            },
            initial_mode=initial_mode,
            group="Plant",
        )

        self._unify_ports()
        self._initialize_ports_from_specs()

        # Aggregate parameters from all sub-components
        self.parameters.update({
            "FEM": self.fem.get_parameters(),
            "OpenSim": self.opensim.get_parameters(),
            "FMU": self.fmu.get_parameters(),
        })

        # Configure mode switching hysteresis
        self.hysteresis = Hysteresis(dwell_time=0.05)

        # Simulation parameters (set during initialization)
        self._t_end = 1.0
        self._with_contact = False
        self._animate = False

        # Monitoring state and widget references
        self.monitoring_state = PendulumMonitoringState()
        self._widget_links = []

    # ----------------------------------------------------------------------------
    # Initialization Logic (now uses base class with hooks)
    # ----------------------------------------------------------------------------
    def _initialize_component(self, t0: float) -> None:
        """
        Initialize sub-components with parameter synchronization across models.

        This override handles the special case where FEM must be initialized
        first to extract geometry-dependent parameters (mass, inertia, length)
        before synchronizing to other models.
        """
        # Initialize FEM first to get computed parameters
        if self.fem is not None:
            self.fem.set_parameters(**self.parameters.get("FEM", {}))
            self.fem.initialize(t0)
            self._t_end = self.fem.sim_params.t_end
            self._with_contact = self.fem._with_contact
            self._animate = self.fem.anim_params.animate

        # Synchronize parameters to other models
        self._sync_parameters_from_fem()

        # Initialize remaining sub-components
        for mode_key, comp in self.models.items():
            if comp is not None and mode_key != "FEM":
                comp.initialize(t0)

        # active_comp is already set by MultiComponent.__init__; only direct
        # feedthrough needs to be reflected on the wrapper.
        self.direct_feedthrough = self.active_comp.direct_feedthrough

        # Configure mode selector based on simulation type
        if self.mode_selector is None:
            if self._with_contact:
                self.mode_selector = self._gap_based_mode_selector
            else:
                self.mode_selector = self._time_based_mode_selector

    def _sync_parameters_from_fem(self) -> None:
        """Synchronize parameters from initialized FEM to other models."""
        if self.fem is None:
            return

        # Extract computed parameters from FEM
        theta_start = np.deg2rad(self.fem.init_params.angular_position_deg)
        omega_start = self.fem.init_params.angular_velocity
        self.use_gravity = self.fem._use_gravity
        length = self.fem._equivalent_length
        inertia = self.fem.inertia
        mass = self.fem.mass

        # Synchronize to OpenSim
        if self.opensim is not None:
            self.opensim.parameters["InitialConditions"]["theta_start"] = theta_start
            self.opensim.parameters["InitialConditions"]["omega_start"] = omega_start
            self.opensim.parameters["Model"]["mass"] = mass
            self.opensim.parameters["Model"]["length"] = length
            self.opensim.parameters["Model"]["inertia"] = inertia - mass * length**2
            self.opensim._use_gravity = self.use_gravity
            self.opensim._with_contact = self._with_contact

        # Synchronize to FMU
        if self.fmu is not None:
            parameters = {
                "theta_start": theta_start,
                "omega_start": omega_start,
                "m": mass,
                "L": length,
                "J": inertia,
                "g": 9.81 if self.use_gravity else 0.0,
            }
            self.fmu.set_parameters(**parameters)

    # ----------------------------------------------------------------------------
    # State Adaptation
    # ----------------------------------------------------------------------------
    def _adapt_state(self, state: dict[str, Any], target_mode: str) -> dict[str, Any]:
        """
        Translate state between component-specific formats.

        Standard format (FEM, OpenSim):
            {'theta': {'value': ..., 'unit': 'rad'}, 'omega': {...}, "tau": {...}}

        FMU format (initial conditions):
            {'theta_start': {'value': ..., 'unit': 'rad'}, 'omega_start': {...}, "tau": {...}}
        """
        if target_mode == "FMU":
            return {"theta_start": state["theta"], "omega_start": state["omega"], "tau": state["tau"]}
        return state

    # ----------------------------------------------------------------------------
    # Mode Selection Logic
    # ----------------------------------------------------------------------------
    def _time_based_mode_selector(self, t: float) -> str:
        """
        Cycle through modes 4 times within simulation time.
        Each complete cycle goes: FEM → FMU → OpenSim
        Total: 12 intervals (3 modes × 4 cycles)
        """
        interval = self._t_end / 12
        cycle_position = int(t / interval) % 3
        if cycle_position == 0:
            return "FEM"
        elif cycle_position == 1:
            return "OpenSim"
        else:
            return "FMU"

    def _gap_based_mode_selector(self, t: float) -> str:
        """
        Select mode based on the cached angular-position output.
        """
        theta_value = self.outputs["theta"].get()
        if theta_value is None:
            return self.active_mode  # not yet initialized; keep current mode
        theta = theta_value.magnitude if hasattr(theta_value, "magnitude") else float(theta_value)

        theta_abs_deg = abs(np.rad2deg(theta))

        if theta_abs_deg < np.rad2deg(0.075) and t <= 0.025:
            return self.active_mode  # Hysteresis: stay in current mode during initial transient

        # Mode selection based on angular position thresholds
        if theta_abs_deg > 15:
            return "FMU"
        elif theta_abs_deg > np.rad2deg(0.075):
            return "OpenSim"
        else:
            return "FEM"

    # ----------------------------------------------------------------------------
    # Update Output States (override to include monitoring and visualization)
    # ----------------------------------------------------------------------------
    def _update_output_states(
        self, t: float | None = None, event_names: list[str] | None = []
    ):
        super()._update_output_states(t, event_names=event_names)

        # 2) Update monitoring widgets (only if t is provided)
        if t is not None:
            dt = t - self.t if hasattr(self, "t") else 0.0
            self._update_monitoring(t, dt)

        # 3) Update FEM scene if not active (for visualization consistency)
        if self.active_mode != "FEM" and self.fem.anim_params.animate:
            theta = self.active_comp.get_outputs()["theta"]
            if t is not None:
                self.fem.update_scene(theta, t)

    # ----------------------------------------------------------------------------
    # Monitoring interface methods
    # ----------------------------------------------------------------------------
    def _initialize_widgets(self):
        self.widgets = {}
        # Input and output monitoring widgets
        for name, spec in self.input_specs.items():
            if spec.type == PortType.REAL:
                self.widgets[name] = widgets.FloatText(
                    value=0.0, description=f"{name} ({spec.unit}):", step=0.01, disabled=True
                )
        for name, spec in self.output_specs.items():
            if spec.type == PortType.REAL:
                self.widgets[name] = widgets.FloatText(
                    value=0.0, description=f"{name} ({spec.unit}):", step=0.01, disabled=True
                )
        # Additional simulation monitoring widgets
        self.widgets["time"] = widgets.FloatText(
            value=0,
            description=f"Time: t / {self.fem.sim_params.t_end} s",
            step=0.001,
            disabled=True,
        )

        self.widgets["dt"] = widgets.FloatText(
            value=self.fem.sim_params.tau,
            description="Time Step: dt in s",
            step=0.0001,
            disabled=True,
        )

        self.widgets["mode"] = widgets.Text(
            value=self.active_mode, description="Simulation Mode:", disabled=True
        )
        if self._with_contact:
            self.widgets["gap"] = widgets.FloatText(
                value=0.0, description="Min. Gap in m", step=0.0001, disabled=True
            )
        self._format_widgets()
        self._link_widgets_to_state()

    def _format_widgets(self):
        for w in self.widgets.values():
            w.layout.width = "300px"
            w.layout.margin = "5px"
            w.style.description_width = "150px"

            w.readout_format = ".5g"

            # Professional color scheme
            w.style.font_family = (
                "Inter"  # , -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
            )
            w.style.font_size = "13px"
            w.style.font_weight = "500"

            # Modern input field styling
            w.style.background = "white"
            w.style.border = "1px solid #e0e0e0"
            w.style.border_radius = "4px"
            w.style.padding = "8px 12px"

            # Text styling
            w.style.color = "#424242"
            w.style.description_color = "#757575"

    def _link_widgets_to_state(self):
        """
        Link widgets to monitoring state for automatic updates.
        """
        for link in self._widget_links:
            link.unlink()
        self._widget_links.clear()

        link_mappings = {
            "time": "time",
            "dt": "dt",
            "mode": "mode",
            "tau": "tau",
            "theta": "theta",
            "omega": "omega",
            "alpha": "alpha",
        }
        if self._with_contact:
            link_mappings["gap"] = "gap"

        for widget_name, state_attr in link_mappings.items():
            if widget_name in self.widgets:
                link = widgets.dlink(
                    (self.monitoring_state, state_attr), (self.widgets[widget_name], "value")
                )
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
        simulation_header = HTML(
            f"<div style='{header_style} text-align:center;'>Simulation Status</div>"
        )

        # Group widgets
        input_widgets = [
            self.widgets[name] for name in self.input_specs.keys() if name in self.widgets
        ]
        output_widgets = [
            self.widgets[name] for name in self.output_specs.keys() if name in self.widgets
        ]
        simulation_widgets = [self.widgets["time"], self.widgets["dt"], self.widgets["mode"]]
        if self._with_contact:
            simulation_widgets.append(self.widgets["gap"])

        # Create widget groups with padding
        input_box = VBox([input_header] + input_widgets, layout=Layout(margin="0 0 20px 10px"))
        output_box = VBox([output_header] + output_widgets, layout=Layout(margin="0 0 20px 10px"))
        simulation_box = VBox(
            [simulation_header] + simulation_widgets, layout=Layout(margin="0 0 20px 10px")
        )

        # Widget Box
        widget_box = HBox(
            [simulation_box, input_box, output_box], layout=Layout(justify_content="space-between")
        )

        # Create main container with sections
        self.monitoring_display = VBox(
            [
                main_header,
                widget_box,
            ],
            layout=Layout(
                padding="20px",
                border="1px solid #e0e0e0",
                border_radius="8px",
                background="#fafafa",
                width="fit-content",
                margin="0 auto",
                height="auto",
                box_shadow="0 4px 8px rgba(0, 0, 0, 0.1)",
            ),
        )

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
        self.monitoring_state.tau = state["tau"]["value"]
        self.monitoring_state.theta = state["theta"]["value"]
        self.monitoring_state.omega = state["omega"]["value"]
        self.monitoring_state.alpha = state["alpha"]["value"]

        if self._with_contact:
            self.monitoring_state.gap = self.fem._get_contact_gap_distance()

    def display_monitoring(self):
        """Display the monitoring interface."""
        display(self.monitoring_display)
        if self.fem is not None:
            display(self.scene_header)
            self.fem.initialize_scene()

    def __del__(self):
        for link in self._widget_links:
            link.unlink()
