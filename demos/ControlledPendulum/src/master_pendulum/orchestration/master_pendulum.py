import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
from IPython.display import display

from syssimx.core.multi_comp import MultiComponent
from syssimx.utilities.units import ureg

from ..components import FEMPendulum, FMUPendulum, OpenSimPendulum
from ..monitoring import PendulumMonitor, PendulumMonitoringState

MODES: tuple[str, ...] = ("FEM", "OpenSim", "FMU")
PENDULUM_DIRECT_FEEDTHROUGH = {
    "theta": frozenset(),
    "omega": frozenset(),
    "alpha": frozenset({"tau"}),
}


def _state_scalar(state: Mapping[str, Any], name: str, expected_unit: str) -> float:
    """Read one finite physical scalar and normalize it to ``expected_unit``."""
    try:
        entry = state[name]
        raw_value = entry["value"]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"Pendulum state requires '{name}.value'.") from exc

    if hasattr(raw_value, "to"):
        value = float(raw_value.to(expected_unit).magnitude)
    else:
        source_unit = entry.get("unit", expected_unit)
        value = float(ureg.Quantity(raw_value, source_unit).to(expected_unit).magnitude)
    if not math.isfinite(value):
        raise ValueError(f"Pendulum state '{name}' must be finite.")
    return value


@dataclass(frozen=True)
class PendulumState:
    """Canonical physical state shared by every pendulum backend."""

    theta: float
    omega: float
    tau: float

    @classmethod
    def from_mapping(cls, state: Mapping[str, Any]) -> "PendulumState":
        """Normalize a backend state mapping to radians, seconds, and N·m."""
        return cls(
            theta=_state_scalar(state, "theta", "rad"),
            omega=_state_scalar(state, "omega", "rad/s"),
            tau=_state_scalar(state, "tau", "N*m"),
        )


@dataclass(frozen=True)
class PendulumTransferTolerances:
    """Absolute continuity limits for a backend state transfer."""

    theta: float = 1e-8
    omega: float = 1e-8
    tau: float = 1e-10

    def __post_init__(self) -> None:
        for name, value in vars(self).items():
            if not math.isfinite(value) or value < 0.0:
                raise ValueError(f"Transfer tolerance '{name}' must be finite and nonnegative.")


@dataclass(frozen=True)
class PendulumTransferReport:
    """Immutable continuity evidence for one prepared backend transfer."""

    source_mode: str
    target_mode: str
    time: float
    source: PendulumState
    target: PendulumState

    @property
    def theta_error(self) -> float:
        return abs(self.target.theta - self.source.theta)

    @property
    def omega_error(self) -> float:
        return abs(self.target.omega - self.source.omega)

    @property
    def tau_error(self) -> float:
        return abs(self.target.tau - self.source.tau)

    def violations(self, tolerances: PendulumTransferTolerances) -> tuple[str, ...]:
        """Return names of canonical quantities outside their continuity limits."""
        errors = {
            "theta": self.theta_error,
            "omega": self.omega_error,
            "tau": self.tau_error,
        }
        return tuple(name for name, error in errors.items() if error > getattr(tolerances, name))


@dataclass(frozen=True)
class MasterPendulumSwitchConfig:
    """Angle-region policy for the three master-pendulum models.

    Breakpoints and hysteresis bands are expressed in radians. Passing
    ``None`` instead of this configuration keeps one model active.
    """

    breakpoints: tuple[float, ...] = (0.075, np.deg2rad(15.0))
    modes: tuple[str, ...] = MODES
    bands: tuple[float, ...] = (0.005, np.deg2rad(1.0))


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
        fmu_solver: Literal["cvode", "euler"] = "cvode",
        switch_config: MasterPendulumSwitchConfig | None = MasterPendulumSwitchConfig(),
        transfer_tolerances: PendulumTransferTolerances = PendulumTransferTolerances(),
    ):

        # Check initial mode validity
        if not is_valid_mode(initial_mode):
            raise ValueError(
                f"{name}: Invalid initial mode '{initial_mode}'. Must be one of {MODES}."
            )

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
        self.direct_feedthrough = {
            output: set(inputs) for output, inputs in PENDULUM_DIRECT_FEEDTHROUGH.items()
        }

        self.switch_config = switch_config
        self.transfer_tolerances = transfer_tolerances
        if switch_config is not None:
            self.set_switch_regions(
                key=self._absolute_theta,
                breakpoints=switch_config.breakpoints,
                modes=switch_config.modes,
                band=switch_config.bands,
            )

        # Aggregate parameters from all sub-components
        self.parameters.update(
            {
                "FEM": self.fem.get_parameters(),
                "OpenSim": self.opensim.get_parameters(),
                "FMU": self.fmu.get_parameters(),
            }
        )

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
            return {
                "theta_start": state["theta"],
                "omega_start": state["omega"],
                "tau": state["tau"],
            }
        return state

    def _build_transfer_report(
        self,
        source_state: dict[str, Any],
        target_state: dict[str, Any],
        source_mode: str,
        target_mode: str,
        t: float,
    ) -> PendulumTransferReport:
        """Validate canonical continuity before committing backend identity."""
        report = PendulumTransferReport(
            source_mode=source_mode,
            target_mode=target_mode,
            time=t,
            source=PendulumState.from_mapping(source_state),
            target=PendulumState.from_mapping(target_state),
        )
        violations = report.violations(self.transfer_tolerances)
        if violations:
            raise RuntimeError(
                f"{self.name}: State transfer {source_mode} -> {target_mode} at t={t:.9g} "
                f"violates continuity tolerances for {list(violations)}."
            )
        return report

    # ----------------------------------------------------------------------------
    # Region Signal
    # ----------------------------------------------------------------------------
    @staticmethod
    def _absolute_theta(component: MultiComponent) -> float:
        """Return the absolute cached angular position in radians."""
        if "theta" not in component.outputs:
            raise RuntimeError(f"{component.name}: Switching signal 'theta' is unavailable.")
        theta_value = component.outputs["theta"].get()
        if theta_value is None:
            raise RuntimeError(f"{component.name}: Switching signal 'theta' is not initialized.")
        theta = getattr(theta_value, "magnitude", theta_value)
        return abs(float(theta))

    # ----------------------------------------------------------------------------
    # Update Output States (override to include monitoring and visualization)
    # ----------------------------------------------------------------------------
    def _update_output_states(self, t: float | None = None, event_names: list[str] | None = None):
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
        self._t_end = 1.0
        self._with_contact = False
        self._animate = False
        self.monitoring_state = PendulumMonitoringState()
        self._monitor = None

    def __del__(self):
        if self._monitor is not None:
            self._monitor.close()
