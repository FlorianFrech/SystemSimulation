"""Hybrid test components for unit tests."""

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
        self, t: float | None = None, event_names: list[str] | None = None
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

    def snapshot_state(self):
        snapshot = {"t": self.t, "x": self.x, "v": self.v, "t0": self.t0}
        return snapshot

    def restore_state(self, snapshot, t) -> None:
        self.t = snapshot["t"]
        self.x = snapshot["x"]
        self.v = snapshot["v"]
        self.t0 = snapshot["t0"]

    def reset(self) -> None:
        super().reset()
        self.x = self.x0
        self._t0 = None
        self.inputs = {}
        self.outputs = {}


class NoRollbackComponent(CoSimComponent):
    """
    Component that does not support rollback.
    """

    def __init__(self, name: str):
        super().__init__(name, group="NoRollback")

    @property
    def supports_rollback(self) -> bool:
        return False

    def _initialize_component(self, t0: float) -> None:
        pass

    def _do_step_internal(self, t: float, dt: float) -> None:
        pass

    def _update_output_states(
        self, t: float | None = None, event_names: list[str] | None = None
    ) -> None:
        pass

    def set_state(self, state: dict[str, Any], t: float) -> None:
        pass

    def get_state(self) -> dict[str, Any]:
        return {}


# ============================================================================
# Micro-Stepping Source for Internal-Hint Regression Tests
# ============================================================================
class MicroSteppingSource(CoSimComponent):
    """Falls linearly through zero and reports its own crossing bracket.

    Sub-steps internally at ``micro_dt`` and calls ``report_internal_event()``
    on the sub-step that crosses, exactly as ``FEMPendulum`` does when its
    contact gap closes.

    The defaults are chosen so that a macro step of ``1e-3`` also straddles the
    crossing at its endpoints. Both sources of information therefore agree,
    which is the case in which the hint bracket used to be discarded as a
    duplicate and the event lost entirely.
    """

    def __init__(
        self,
        name: str,
        y0: float = 5.5e-4,
        rate: float = -1.0,
        micro_dt: float = 1e-4,
        bounce: bool = False,
    ):
        super().__init__(name, group="Event Source")
        self.y0 = y0
        self.rate0 = rate
        self.rate = rate
        self.micro_dt = micro_dt
        self.bounce = bounce
        self._y = y0
        self.output_specs.update({"y": PortSpec(name="y", type=PortType.REAL, direction="out")})

    def _initialize_component(self, t0: float) -> None:
        self._y = self.y0
        self.rate = self.rate0

    def _do_step_internal(self, t: float, dt: float) -> None:
        t_now = t
        t_end = t + dt
        while t_now < t_end - 1e-15:
            step = min(self.micro_dt, t_end - t_now)
            y_before = self._y
            self._y += self.rate * step
            t_now += step
            if y_before > 0.0 >= self._y:
                self.report_internal_event(
                    event_name="zero",
                    t_before=t_now - step,
                    t_after=t_now,
                    indicator_before=y_before,
                    indicator_after=self._y,
                )
                if self.bounce:
                    # Return to the positive side inside the same macro step,
                    # the way a penalty contact repels the pendulum. The macro
                    # endpoints then show no sign change and the reported
                    # bracket is the only evidence of the crossing.
                    self.rate = -self.rate

    def _update_output_states(
        self, t: float | None = None, event_names: list[str] | None = None
    ) -> None:
        self.outputs["y"].set(self._y, t=t)

    def get_state(self) -> dict[str, Any]:
        return {"y": self._y}

    def set_state(self, state: dict[str, Any], t: float) -> None:
        self._y = float(state["y"])

    def snapshot_state(self) -> dict[str, Any]:
        return {"y": self._y, "rate": self.rate}

    def restore_state(self, snapshot: dict[str, Any], t: float) -> None:
        self._y = float(snapshot["y"])
        self.rate = float(snapshot["rate"])
        self.t = t

    def reset(self) -> None:
        super().reset()
        self._y = self.y0
        self.rate = self.rate0


# ============================================================================
# Stale-Input Pair for the HYB-01 Accepted-Trajectory Guard
# ============================================================================
class FlippingSource(CoSimComponent):
    """Emits ``+1`` until its first step, then ``-1`` forever.

    Upstream half of the pair that reproduces the trial/accepted trajectory
    mismatch: the value an event source reads during detection is not the value
    it reads during the accepted advance.
    """

    def __init__(self, name: str):
        super().__init__(name, group="Upstream")
        self._v = 1.0
        self.output_specs.update({"v": PortSpec(name="v", type=PortType.REAL, direction="out")})

    def _initialize_component(self, t0: float) -> None:
        self._v = 1.0

    def _do_step_internal(self, t: float, dt: float) -> None:
        if dt > 0.0:
            self._v = -1.0

    def _update_output_states(
        self, t: float | None = None, event_names: list[str] | None = None
    ) -> None:
        self.outputs["v"].set(self._v, t=t)

    def get_state(self) -> dict[str, Any]:
        return {"v": self._v}

    def set_state(self, state: dict[str, Any], t: float) -> None:
        self._v = float(state["v"])

    def snapshot_state(self) -> dict[str, Any]:
        return {"v": self._v}

    def restore_state(self, snapshot: dict[str, Any], t: float) -> None:
        self._v = float(snapshot["v"])
        self.t = t


class InputEchoSource(CoSimComponent):
    """Copies its input to its output, and carries the event indicator.

    Declaring ``y`` as direct feedthrough on ``u`` puts this component in a
    later generation than its upstream, so the accepted advance re-reads the
    input after the upstream has stepped while detection does not. The
    indicator therefore changes sign on the accepted trajectory only.
    """

    def __init__(self, name: str, y0: float = 1.0):
        super().__init__(name, group="Event Source")
        self.y0 = y0
        self._y = y0
        self.input_specs.update({"u": PortSpec(name="u", type=PortType.REAL, direction="in")})
        self.output_specs.update({"y": PortSpec(name="y", type=PortType.REAL, direction="out")})
        self.direct_feedthrough = {"y": {"u"}}

    def _initialize_component(self, t0: float) -> None:
        self._y = self.y0

    def _do_step_internal(self, t: float, dt: float) -> None:
        value = self.inputs["u"].get()
        if value is not None:
            self._y = float(getattr(value, "magnitude", value))

    def _update_output_states(
        self, t: float | None = None, event_names: list[str] | None = None
    ) -> None:
        self.outputs["y"].set(self._y, t=t)

    def get_state(self) -> dict[str, Any]:
        return {"y": self._y}

    def set_state(self, state: dict[str, Any], t: float) -> None:
        self._y = float(state["y"])

    def snapshot_state(self) -> dict[str, Any]:
        return {"y": self._y}

    def restore_state(self, snapshot: dict[str, Any], t: float) -> None:
        self._y = float(snapshot["y"])
        self.t = t
