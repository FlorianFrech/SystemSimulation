from typing import Any, Literal

import numpy as np
from IPython.display import display

from syssimx.core.multi_comp import MultiComponent

from ..components import FEMPendulum, FMUPendulum, OpenSimPendulum
from ..monitoring import PendulumMonitor, PendulumMonitoringState

MODES: tuple[str, ...] = ("FEM", "OpenSim", "FMU")

def is_valid_mode(mode: str) -> bool:
    return mode in MODES

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

        # Simulation parameters (set during initialization)
        self._t_end = 1.0
        self._with_contact = False
        self._animate = False

        # Monitoring: the observable state exists from construction (the step
        # loop writes to it); the widget panel is created lazily in
        # setup_monitoring().
        self.monitoring_state = PendulumMonitoringState()
        self._monitor: PendulumMonitor | None = None

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
            return self.active_mode  # Stay in the initial model during the transient

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
        self, t: float | None = None, event_names: list[str] | None = None
    ):
        super()._update_output_states(t, event_names=event_names)

        if self.in_trial:
            return

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
    def setup_monitoring(self) -> None:
        """Create the shared monitoring panel bound to ``monitoring_state``."""
        self._monitor = PendulumMonitor(
            self.input_specs,
            self.output_specs,
            t_end=self.fem.sim_params.t_end,
            tau=self.fem.sim_params.tau,
            mode=self.active_mode,
            with_contact=self._with_contact,
            state=self.monitoring_state,
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
        """Display the monitoring interface and initialize the FEM scene."""
        if self._monitor is None:
            self.setup_monitoring()
        self._monitor.display()
        if self.fem is not None:
            display(self._monitor.scene_header)
            self.fem.initialize_scene()

    def reset(self) -> None:
        """Restore the orchestration and observer state of a fresh instance."""
        if self._monitor is not None:
            self._monitor.close()
        super().reset()
        self.mode_selector = None
        self._t_end = 1.0
        self._with_contact = False
        self._animate = False
        self.monitoring_state = PendulumMonitoringState()
        self._monitor = None

    def __del__(self):
        if self._monitor is not None:
            self._monitor.close()
