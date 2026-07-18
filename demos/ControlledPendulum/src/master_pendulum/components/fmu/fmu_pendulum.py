import sys
from pathlib import Path
from typing import Literal

from syssimx.components.fmu import FMUComponent
from syssimx.core.port import PortSpec, PortType

PLATFORM = sys.platform
SOLVERS = Literal["euler", "cvode"]

# ----------------------------------------------------------------------------
# FMU Pendulum Component
# ----------------------------------------------------------------------------
class FMUPendulum(FMUComponent):
    """
    FMU-based pendulum component with rollback support.
    """

    def __init__(self, name, group="Plant", solver: SOLVERS = "cvode"):
        # Select FMU based on solver choice
        try:
            fmu_path = Path(__file__).parents[4]/ f"artifacts/fmus/{PLATFORM}/Plants/Pendulum_{solver}.fmu"
        except KeyError:
             raise ValueError(f"Unsupported platform '{PLATFORM}'. No FMU available for this platform.")
        self.solver = solver

        # Initialize base class
        super().__init__(name, fmu_path, group)

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
        state = {"mode": "FMU"}
        if self.solver == "euler":
            state["fmu_state"] = self._instance.getFMUState()
        elif self.solver == "cvode":
            current_state = super().get_state()
            state.update(current_state)
        return state

    def restore_state(self, snapshot, t):
        if snapshot.get("mode", "") != "FMU":
            raise ValueError(
                f"[{self.name}] Incompatible snapshot mode, got '{snapshot.get('mode', '')}'."
            )
        self.t = t
        if self.solver == "euler":
            self._instance.setFMUState(snapshot["fmu_state"])
            self._apply_parameters_starts()

        elif self.solver == "cvode":
            theta_start = snapshot["theta"]["value"]
            omega_start = snapshot["omega"]["value"]
            self.set_parameters(**{"theta_start": theta_start, "omega_start": omega_start})
            self.reinitialize_instance(t)
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

    def _update_output_states(
        self, t: float | None = None, event_names: list[str] | None = None
    ):
        super()._update_output_states(t)
        self._apply_event_ports(t, event_names)
