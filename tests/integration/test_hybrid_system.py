from typing import Any

from syssimx.core.base import CoSimComponent
from syssimx.core.events import Event
from syssimx.core.port import PortSpec, PortType
from syssimx.system.connection import EventConnection
from syssimx.system.system import System
from syssimx.utilities.units import Quantity


# -------------------------------------------------------------------
# Hybrid Source Component
# -------------------------------------------------------------------
class HybridSource(CoSimComponent):
    """
    Simple component with a state variable that evolves linearly.
    x(t) = x0 + v * t
    Used for testing event indicators and zero-crossing detection.
    """

    def __init__(self, name: str, x0: float = 0.0, velocity: float = 1.0):
        super().__init__(name, group="Source")
        self.x0 = x0
        self.v = velocity
        self.x = x0
        self._t0 = None

    def _initialize_component(self, t0: float) -> None:
        self._t0 = t0
        self.x = self.x0

        self.output_specs.update(
            {
                "x": PortSpec(
                    name="x", type=PortType.REAL, direction="out", unit="m", description="Position"
                ),
                "v": PortSpec(
                    name="v",
                    type=PortType.REAL,
                    direction="out",
                    unit="m/s",
                    description="Velocity",
                ),
            }
        )
        self._initialize_ports_from_specs()

    def _do_step_internal(self, t: float, dt: float) -> None:
        self.x = self.x0 + self.v * (t + dt - self._t0)

    def _update_output_states(self, t: float | None = None) -> None:
        self.outputs["x"].set(Quantity(self.x, "m"), t=t)
        self.outputs["v"].set(Quantity(self.v, "m/s"), t=t)

    def set_state(self, state: dict[str, Any], t: float) -> None:
        if "x" in state:
            val = state["x"]
            self.x = val.magnitude if isinstance(val, Quantity) else val

    def get_state(self) -> dict[str, Any]:
        return {"x": Quantity(self.x, "m")}

    def snapshot_state(self):
        snapshot = {"t": self.t, "x": self.x, "v": self.v}
        return snapshot

    def restore_state(self, snapshot) -> None:
        self.t = snapshot["t"]
        self.x = snapshot["x"]
        self.v = snapshot["v"]

    def reset(self) -> None:
        super().reset()
        self.x = self.x0
        self._t0 = None
        self.inputs = {}
        self.outputs = {}


# -------------------------------------------------------------------
# Hybrid Listener Component
# -------------------------------------------------------------------
class HybridListener(CoSimComponent):
    """
    Simple component with a state variable that evolves linearly.
    x(t) = x0 + v * t
    Used for testing event indicators and zero-crossing detection.
    """

    def __init__(self, name: str, x0: float = 0.0, velocity: float = 1.0):
        super().__init__(name, group="Listener")
        self.v = velocity
        self.x = x0

    def _initialize_component(self, t0: float) -> None:
        self.output_specs.update(
            {
                "x": PortSpec(
                    name="x",
                    type=PortType.REAL,
                    direction="out",
                    unit="m",
                    description="State variable",
                )
            }
        )
        self.input_specs.update(
            {
                "vel_invert": PortSpec(
                    name="vel_invert",
                    type=PortType.EVENT,
                    direction="in",
                    description="Event input to switch velocity",
                )
            }
        )
        self._initialize_ports_from_specs()

    def _do_step_internal(self, t: float, dt: float) -> None:
        self.x += self.v * dt

    def _update_output_states(self, t: float | None = None) -> None:
        self.outputs["x"].set(Quantity(self.x, "m"), t=t)

    def set_state(self, state: dict[str, Any], t: float) -> None:
        if "x" in state:
            val = state["x"]
            self.x = val.magnitude if isinstance(val, Quantity) else val

    def get_state(self) -> dict[str, Any]:
        return {"x": Quantity(self.x, "m")}

    def snapshot_state(self):
        snapshot = {"t": self.t, "x": self.x, "v": self.v}
        return snapshot

    def restore_state(self, snapshot) -> None:
        self.t = snapshot["t"]
        self.x = snapshot["x"]
        self.v = snapshot["v"]

    def _handle_events_internal(self, event_names, t):
        self.v = -self.v

    def reset(self) -> None:
        super().reset()
        self.x = self.x0
        self._t0 = None
        self.inputs = {}
        self.outputs = {}


# -------------------------------------------------------------------
# Helper Functions
# -------------------------------------------------------------------

X_0_SRC = -0.66
VELOCITY_SRC = 2.0
X_0_LIST = 0.0
VELOCITY_LIST = 1.0


def event_indicator_function(comp: HybridSource) -> float:
    return comp.x


def setup_hybrid_system():
    src_comp = HybridSource(name="Source", x0=X_0_SRC, velocity=VELOCITY_SRC)

    event = Event(name="trigger", source=src_comp.name, direction=1)
    src_comp.initialize(t0=0.0)
    src_comp.add_event_indicator(event.name, event_indicator_function, direction=event.direction)

    listener_comp = HybridListener(name="Listener", x0=X_0_LIST, velocity=VELOCITY_LIST)
    listener_comp.initialize(t0=0.0)
    listener_comp.subscribe_event(event=event)

    system = System(name="Hybrid Test System")
    system.add_component(src_comp)
    system.add_component(listener_comp)
    connection = EventConnection(
        src_comp=src_comp.name,
        src_port=src_comp.output_specs["trigger"].name,
        dst_comp=listener_comp.name,
        dst_port=listener_comp.input_specs["vel_invert"].name,
    )
    system.add_event_connection(connection)

    system.initialize(t0=0.0)

    return system, src_comp, listener_comp, event


# -------------------------------------------------------------------
# Hybrid System Test Cases
# -------------------------------------------------------------------
# def test_hybrid_system_setup():
#     system, src_comp, listener_comp, event = setup_hybrid_system()
#     system.initialize(t0=0.0)

#     event_targets_by_source_target = {('Source', 'trigger'): ['Listener']}

#     assert system._event_targets_by_source == event_targets_by_source_target
#     assert system.event_sources == [src_comp]
#     assert system.event_listeners == [listener_comp]
#     assert system.continuous_only == []
#     assert isinstance(system.algorithm, HybridAlgorithm)

# def test_hybrid_system_run():
#     system, src_comp, listener_comp, event = setup_hybrid_system()

#     system.run(t0=0.0, tf=1.0, dt = 0.01)

#     event_history = system.history.get_all_event_histories()
#     assert (src_comp.name, event.name) in event_history
#     event_times = event_history[(src_comp.name, event.name)]
#     assert len(event_times) == 1
#     event_time = event_times[0]
#     expected_event_time = (0.0 - X_0_SRC) / VELOCITY_SRC
#     assert np.isclose(event_time, expected_event_time, atol=1e-6)
