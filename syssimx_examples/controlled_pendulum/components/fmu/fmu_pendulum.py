import sys
from pathlib import Path
from typing import Literal

from syssimx.components.fmu import FMUComponent
from syssimx.core.port import PortSpec, PortType

PLATFORM = sys.platform
SOLVERS = Literal["euler", "cvode"]
SUPPORTED_SOLVERS = ("euler", "cvode")


def repository_fmu_path(solver: SOLVERS, platform: str = PLATFORM) -> Path:
    """Return the FMU shipped in a source checkout for ``solver``.

    FMU binaries remain case-study artifacts and are deliberately excluded
    from the Python wheel. Installed-package users must therefore pass
    ``fmu_path`` explicitly.
    """
    if solver not in SUPPORTED_SOLVERS:
        raise ValueError(f"Unsupported FMU solver '{solver}'. Choose from {SUPPORTED_SOLVERS}.")

    repository_root = Path(__file__).resolve().parents[4]
    return (
        repository_root
        / "demos"
        / "ControlledPendulum"
        / "artifacts"
        / "fmus"
        / platform
        / "Plants"
        / f"Pendulum_{solver}.fmu"
    )


# ----------------------------------------------------------------------------
# FMU Pendulum Component
# ----------------------------------------------------------------------------
class FMUPendulum(FMUComponent):
    """
    FMU-based pendulum component with rollback support.
    """

    def __init__(
        self,
        name: str,
        group: str = "Plant",
        solver: SOLVERS = "cvode",
        fmu_path: str | Path | None = None,
    ):
        if solver not in SUPPORTED_SOLVERS:
            raise ValueError(f"Unsupported FMU solver '{solver}'. Choose from {SUPPORTED_SOLVERS}.")
        resolved_fmu_path = Path(fmu_path) if fmu_path is not None else repository_fmu_path(solver)
        if not resolved_fmu_path.is_file():
            raise FileNotFoundError(
                f"Controlled-pendulum FMU not found at '{resolved_fmu_path}'. "
                "The binary artifacts are not included in the SysSimX wheel; "
                "pass fmu_path explicitly or run from a source checkout."
            )
        self.solver = solver

        # Initialize base class
        super().__init__(name, resolved_fmu_path, group)

        # Add event input port for omega inversion
        self.input_specs.update({"omega_invert": PortSpec("omega_invert", PortType.EVENT, "in")})

    def _do_step_internal(self, t, dt):
        t_right = t + dt
        while t < t_right:
            step_size = min(1e-4, t_right - t)
            super()._do_step_internal(t, step_size)
            t += step_size
            # self._update_output_states(t)
            # self._record_outputs(t)

    # Snapshot and restore state methods for rollback
    def snapshot_state(self):
        """Capture the reconstructible physical state of the pendulum FMU.

        The checked-in FMUs do not advertise native FMI state support. Their
        checkpoints therefore preserve physical variables and inputs while
        deliberately discarding solver-internal history.
        """
        state = super().get_state()
        state["mode"] = "FMU"
        return state

    def restore_state(self, snapshot, t):
        """Rebuild an instance from a physical checkpoint at ``t``."""
        if snapshot.get("mode", "") != "FMU":
            raise ValueError(
                f"[{self.name}] Incompatible snapshot mode, got '{snapshot.get('mode', '')}'."
            )
        theta_start = snapshot["theta"]["value"]
        omega_start = snapshot["omega"]["value"]
        for name, value in snapshot.items():
            if name in self.inputs and isinstance(value, dict) and "value" in value:
                self.inputs[name].set(value["value"], t=t)
        self.set_parameters(**{"theta_start": theta_start, "omega_start": omega_start})
        self.reinitialize_instance(t)
        self.t = t
        self._update_output_states(t)
        self._record_outputs(t)

    # Handle events: invert omega on wall hit
    def _handle_events_internal(self, event_names, t):
        if "wall_hit" not in event_names:
            return
        restitution = 1
        output = self.get_outputs()
        omega_start = -restitution * output["omega"].magnitude

        self.set_parameters(**{"theta_start": 0, "omega_start": omega_start})
        self.reinitialize_instance(t)

    def _update_output_states(self, t: float | None = None, event_names: list[str] | None = None):
        super()._update_output_states(t)
        self._apply_event_ports(t, event_names)
