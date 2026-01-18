from typing import Any

from syssimx.core.base import CoSimComponent
from syssimx.core.port import PortSpec, PortType
from syssimx.utilities.units import Quantity


# ============================================================================
# Hybrid Source Component for Unit Tests
# ============================================================================
class HybridSource(CoSimComponent):
    """
    Hybrid component with linearly evolving state variable:

    `x(t) = x0 + v * (t - t0)`

     - `x`: State variable (output) (position)
     - `x0`: Initial state at time `t0` (initial position)
     - `v`: Constant rate of change (velocity)
     - `t0`: Initial time

    Supports snapshot and restore of state, and can be used as event source.
    """

    def __init__(self, name: str, x0: float = 0.0, v: float = 1.0, t0: float = 0.0):
        super().__init__(name, group="Event Source")
        self.x0 = x0
        self.v = v
        self.t0 = t0
        self.output_specs.update({"x": PortSpec(name="x", type=PortType.REAL, direction="out")})

    def _initialize_component(self, t0: float) -> None:
        self.x = self.x0

    def _do_step_internal(self, t: float, dt: float) -> None:
        self.x = self.x0 + self.v * (t + dt - self.t0)

    def _update_output_states(self, t: float | None = None) -> None:
        self.outputs["x"].set(self.x, t=t)

    def set_state(self, state: dict[str, Any], t: float) -> None:
        if "x" in state:
            self.x = state["x"]

    def get_state(self) -> dict[str, Any]:
        return {"x": self.x}

    def snapshot_state(self):
        return {"t": self.t, "x": self.x, "v": self.v, "t0": self.t0}

    def restore_state(self, snapshot, t) -> None:
        self.t = snapshot["t"]
        self.t0 = snapshot["t0"]
        self.x = snapshot["x"]
        self.v = snapshot["v"]

    def reset(self) -> None:
        super().reset()
        self.x = self.x0
        self.inputs.clear()
        self.outputs.clear()


# ============================================================================
# Hybrid Combi Component for Unit Tests
# ============================================================================
class HybridCombi(CoSimComponent):
    """
    Hybrid component with linearly evolving state variable:

    `x(t) = x0 + v * (t - t0)`

     - `x`: State variable (output) (position)
     - `x0`: Initial state at time `t0` (initial position)
     - `v`: Constant rate of change (velocity)
     - `t0`: Initial time

    Can be used as a combinational component. Supports snapshot and restore of state
    for acting as event source in hybrid simulations.
    Can be also used as event listener, as it supports event handling.
    Upon receiving an event named 'v_double', it doubles its velocity `v`.
    """

    def __init__(self, name: str, x0: float = 0.0, v: float = 1.0, t0: float = 0.0):
        super().__init__(name, group="Combi")
        self.x0 = x0
        self.v_prev = v
        self.v_curr = v
        self.t0 = t0
        self.v_changed = False  # flag for velocity change
        self.input_specs.update(
            {"v_double": PortSpec(name="v_double", type=PortType.EVENT, direction="in")}
        )
        self.output_specs.update(
            {
                "x": PortSpec(name="x", type=PortType.REAL, direction="out"),
            }
        )

    def _initialize_component(self, t0: float) -> None:
        self.x = self.x0

    def _do_step_internal(self, t: float, dt: float) -> None:
        self.x = self.x0 + self.v_curr * (t + dt - self.t0)

    def _update_output_states(
        self, t: float | None = None, event_names: list[str] | None = []
    ) -> None:
        self.outputs["x"].set(self.x, t=t)

    def set_state(self, state: dict[str, Any], t: float) -> None:
        if "x" in state:
            val = state["x"]
            self.x = val.magnitude if isinstance(val, Quantity) else val

    def get_state(self) -> dict[str, Any]:
        return {"x": self.x, "v": self.v_curr}

    def snapshot_state(self):
        return {
            "t": self.t,
            "x": self.x,
            "v": self.v_curr,
            "v_prev": self.v_prev,
            "v_changed": self.v_changed,
            "t0": self.t0,
        }

    def _handle_events_internal(self, event_names, t):
        if "v_double" in event_names:  # Fixed condition
            self.t0 = t
            self.x0 = self.x
            self.v_prev = self.v_curr
            self.v_curr = 2 * self.v_curr
            self.v_changed = True
            print(
                f"{self.name} handled event at t={t:.4f}: v doubled from {self.v_prev} to {self.v_curr}"
            )

        if "v_change" in event_names:
            self.v_changed = False  # reset flag after event handled

    def restore_state(self, snapshot, t) -> None:
        self.t = t
        self.t0 = snapshot["t0"]
        self.x = snapshot["x"]
        self.v_curr = snapshot["v"]
        self.v_prev = snapshot.get("v_prev", self.v_curr)
        self.v_changed = snapshot.get("v_changed", False)

    def reset(self) -> None:
        super().reset()
        self.x = self.x0
        self.inputs.clear()
        self.outputs.clear()


# ============================================================================
# Hybrid Listener Component for Unit Tests
# ============================================================================
class HybridListener(CoSimComponent):
    """
    Hybrid component with linearly evolving state variable:

    `x(t) = x0 + v * (t - t0)`

     - `x`: State variable (output) (position)
     - `x0`: Initial state at time `t0` (initial position)
     - `v`: Constant rate of change (velocity)
     - `t0`: Initial time

    The component can be used as an event listener. Upon receiving events named
    'v_invert' or 'v_double', it inverts or doubles its velocity `v`, respectively.

    Does not support snapshot and restore of state, and can thus not be used as event source.
    """

    def __init__(
        self,
        name: str,
        x0: float = 0.0,
        v: float = 1.0,
        t0: float = 0.0,
        use_event_annotations: bool = False,
    ):
        super().__init__(name, group="Listener")
        self.x0 = x0
        self.v = v
        self.t0 = t0

        if use_event_annotations:
            self.event_annotations.update(
                {
                    "v_invert": {"modifies": {"v"}, "type": "RMW"},
                    "v_double": {"modifies": {"v"}, "type": "RMW"},
                }
            )

            self.event_commutativity.update(
                {
                    ("v_invert", "v_double"): True,
                }
            )

        self.input_specs.update(
            {
                "v_invert": PortSpec(name="v_invert", type=PortType.EVENT, direction="in"),
                "v_double": PortSpec(name="v_double", type=PortType.EVENT, direction="in"),
            }
        )
        self.output_specs.update(
            {
                "x": PortSpec(name="x", type=PortType.REAL, direction="out"),
                "v": PortSpec(name="v", type=PortType.REAL, direction="out"),
            }
        )

    def _initialize_component(self, t0: float) -> None:
        self.x = self.x0

    def _do_step_internal(self, t: float, dt: float) -> None:
        self.x = self.x0 + self.v * (t + dt - self.t0)

    def _update_output_states(
        self, t: float | None = None, event_names: list | None = None
    ) -> None:
        self.outputs["x"].set(self.x, t=t)
        self.outputs["v"].set(self.v, t=t)

    def set_state(self, state: dict[str, Any], t: float) -> None:
        if "x" in state:
            self.x = state["x"]
        if "v" in state:
            self.v = state["v"]

    def get_state(self) -> dict[str, Any]:
        return {"x": self.x, "v": self.v}

    def _handle_events_internal(self, event_names, t):
        v_invert_events = set(["Trigger_1", "Trigger_2", "v_invert"])
        v_double_events = set(["v_double"])

        if v_invert_events.intersection(event_names):
            self.t0 = t
            self.x0 = self.x
            self.v = -self.v
            print(f"{self.name} handled event at t={t:.4f}: v inverted from {-self.v} to {self.v}")
        elif v_double_events.intersection(event_names):
            self.t0 = t
            self.x0 = self.x
            self.v = 2.0 * self.v
            print(
                f"{self.name} handled event at t={t:.4f}: v doubled from {self.v / 2.0} to {self.v}"
            )

    def reset(self) -> None:
        super().reset()
        self.x = self.x0
        self._t0 = None
        self.inputs = {}
        self.outputs = {}
