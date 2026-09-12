"""The closed control loop every case-study notebook runs.

Setpoint, PID, drive, plant, and the sensor chain. Only the plant is exchanged
between cases, which is what makes the comparison like-for-like.
"""

from __future__ import annotations

from pathlib import Path

from syssimx import Connection, EventConnection, FMUComponent, System
from syssimx.core.base import CoSimComponent
from syssimx.system.algorithms import HybridAlgorithm

from .plant import PLANT_NAME, scalar_value
from .scenario import Scenario

__all__ = [
    "discover_fmus",
    "PIDController",
    "wall_contact_indicator",
    "declare_plant_feedthrough",
    "create_common_components",
    "assemble_system",
]

# The FEM plant must not be perturbed before its torque boundary is assembled,
# so the feedthrough map is declared rather than detected. System.initialize()
# needs it before it initializes pure-Python components.
PLANT_DIRECT_FEEDTHROUGH = {"theta": set(), "omega": set(), "alpha": {"tau"}}


def discover_fmus(repo_root: Path, platform_name: str) -> dict:
    """Map the tracked FMU artifacts, grouped by their directory."""
    fmu_dir = Path(repo_root) / "demos" / "ControlledPendulum" / "artifacts" / "fmus" / platform_name
    paths: dict = {}
    for entry in sorted(fmu_dir.iterdir()):
        if entry.is_dir():
            paths[entry.name] = {f.stem: f for f in sorted(entry.glob("*.fmu"))}
        else:
            paths[entry.stem] = entry
    return paths


class PIDController(FMUComponent):
    """PID whose integrator is reset by the `wall_hit` event."""

    def __init__(self, name: str, fmu_paths: dict):
        super().__init__(
            name=name,
            fmu_path=fmu_paths["Controllers"]["PIDControllerReset_euler"],
            group="Controller",
        )

    def _handle_events_internal(self, event_names, t):
        if "wall_hit" not in event_names:
            return
        self.set_inputs({"resetI": True})
        self.do_step(t, 0.0)  # apply the resetI input
        self.set_inputs({"resetI": False})


def wall_contact_indicator(comp) -> float:
    """Signed distance of the plant angle from the wall at theta = 0."""
    return scalar_value(comp.get_outputs()["theta"]) - 0.0


def declare_plant_feedthrough(component: CoSimComponent) -> CoSimComponent:
    component.direct_feedthrough = {
        name: set(inputs) for name, inputs in PLANT_DIRECT_FEEDTHROUGH.items()
    }
    return component


def create_common_components(fmu_paths: dict):
    setpoint = FMUComponent(
        name="Setpoint", fmu_path=fmu_paths["Trajectories"]["SetPoint"], group="Reference"
    )
    pid = PIDController("PID", fmu_paths)
    drive = FMUComponent(
        name="Drive", fmu_path=fmu_paths["Actuators"]["DriveDynamic"], group="Actuator"
    )
    angle_sensor = FMUComponent(
        name="Angle Sensor", fmu_path=fmu_paths["Sensors"]["AngleSensor"], group="Sensors"
    )
    angle_decoder = FMUComponent(
        name="Angle Decoder",
        fmu_path=fmu_paths["Sensors"]["AngleDecoder"],
        group="Signal Processing",
    )
    return setpoint, pid, drive, angle_sensor, angle_decoder


def assemble_system(
    plant: CoSimComponent,
    scenario: Scenario,
    fmu_paths: dict,
    *,
    case_name: str,
    detection_probe: bool = False,
) -> tuple[System, CoSimComponent]:
    """Wire the loop around `plant` and initialize it.

    Args:
        plant: The exchanged participant, already parameterised.
        scenario: Declares the horizon and the event tolerances.
        fmu_paths: Result of :func:`discover_fmus`.
        case_name: System name; also the label carried into the results.
        detection_probe: Register a constant, never-crossing indicator. Needed
            for a contact-free baseline that has no indicator of its own:
            without it `System` selects `GaussSeidelAlgorithm`, which takes no
            trial advance, and the switched case would be charged for detection
            work the reference never pays.

    Event indicators are registered **before** `System.initialize()` so their
    EVENT ports are created in the same pass as the other outputs and share the
    component's one time axis from the first sample.
    """
    setpoint, pid, drive, angle_sensor, angle_decoder = create_common_components(fmu_paths)

    if scenario.contact:
        plant.add_event_indicator("wall_hit", func=wall_contact_indicator, direction=-1)
    elif detection_probe:
        plant.add_event_indicator("detection_probe", func=lambda comp: 1.0, direction=0)

    system = System(name=case_name)
    for comp in (setpoint, pid, drive, plant, angle_decoder, angle_sensor):
        system.add_component(comp)

    for connection in (
        Connection("Setpoint", "theta_ref", "PID", "theta_ref"),
        Connection(plant.name, "theta", "Angle Sensor", "theta"),
        Connection("Angle Sensor", "v_out", "Angle Decoder", "v_in"),
        Connection("Angle Decoder", "theta", "PID", "theta_meas"),
        Connection("PID", "u", "Drive", "u_control"),
        Connection("Drive", "torque", plant.name, "tau"),
        Connection(plant.name, "omega", "Drive", "omega"),
    ):
        system.add_connection(connection)

    if scenario.contact:
        system.add_event_connection(
            EventConnection(plant.name, "wall_hit", plant.name, "omega_invert")
        )
        system.add_event_connection(EventConnection(plant.name, "wall_hit", "PID", "resetI"))

    system.initialize(t0=scenario.t0)

    # Set after initialize(): that is when the algorithm instance exists.
    if isinstance(system.algorithm, HybridAlgorithm):
        system.algorithm.tol_time = scenario.event_tol_time
        system.algorithm.tol_value = scenario.event_tol_value
        system.algorithm.record_internal_steps = False
        system.algorithm.raise_on_missed_event = scenario.raise_on_missed_event

    return system, plant
