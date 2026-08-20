"""Test components for MultiComponent unit tests."""

from collections.abc import Callable
from typing import Any

from syssimx.core.base import CoSimComponent
from syssimx.core.multi_comp import ModeKey, MultiComponent
from syssimx.core.port import PortSpec, PortType


class MockSubComponent(CoSimComponent):
    """
    Simple mock component for testing MultiComponent.
    Tracks method calls and maintains simple state.
    """

    def __init__(self, name: str, gain: float = 1.0):
        super().__init__(name, label=name)
        self.gain = gain
        self._state = {"x": 0.0, "v": 0.0}
        self._step_count = 0

        # Track method calls for assertions
        self.call_log: list[str] = []

        # Define ports
        self.input_specs = {
            "u": PortSpec(name="u", type=PortType.REAL, unit="N", direction="in"),
        }
        self.output_specs = {
            "y": PortSpec(name="y", type=PortType.REAL, unit="m", direction="out"),
        }

    def _initialize_component(self, t0: float) -> None:
        self.call_log.append(f"initialize({t0})")
        self._state = {"x": 0.0, "v": 0.0}
        self._step_count = 0

    def _do_step_internal(self, t: float, dt: float) -> None:
        self.call_log.append(f"do_step({t}, {dt})")
        # Simple dynamics: x += v * dt, apply gain to input
        u = self.inputs["u"].get() or 0.0
        self._state["v"] += u * self.gain * dt
        self._state["x"] += self._state["v"] * dt
        self._step_count += 1

    def _update_output_states(
        self, t: float | None = None, event_names: list[str] | None = None
    ) -> None:
        self.outputs["y"].set(self._state["x"], t=t)

    def get_state(self) -> dict[str, Any]:
        self.call_log.append("get_state()")
        return self._state.copy()

    def set_state(self, state: dict[str, Any], t: float) -> None:
        self.call_log.append(f"set_state({state}, {t})")
        self._state = state.copy()

    def reset(self) -> None:
        self.call_log.append("reset()")
        self._state = {"x": 0.0, "v": 0.0}
        self._step_count = 0


class MockSubComponentAlt(MockSubComponent):
    """
    Alternative mock with different gain for testing mode switching.
    """

    def __init__(self, name: str):
        super().__init__(name, gain=2.0)


class MockSubComponentIncompatible(CoSimComponent):
    """
    Mock component with incompatible ports for testing validation.
    """

    def __init__(self, name: str):
        super().__init__(name, label=name)
        # Different port names - should fail validation
        self.input_specs = {
            "input_force": PortSpec(
                name="input_force", type=PortType.REAL, unit="N", direction="in"
            ),
        }
        self.output_specs = {
            "output_position": PortSpec(
                name="output_position", type=PortType.REAL, unit="m", direction="out"
            ),
        }

    def _initialize_component(self, t0: float) -> None:
        pass

    def _do_step_internal(self, t: float, dt: float) -> None:
        pass

    def get_state(self) -> dict[str, Any]:
        return {}

    def set_state(self, state: dict[str, Any], t: float) -> None:
        pass


class SimpleMultiComponent(MultiComponent):
    """
    Concrete MultiComponent implementation for testing.
    Uses two MockSubComponents with different gains.
    """

    def __init__(self, name: str, initial_mode: ModeKey = "A"):
        models = {
            "A": MockSubComponent(f"{name}_A", gain=1.0),
            "B": MockSubComponentAlt(f"{name}_B"),
        }
        super().__init__(name, models=models, initial_mode=initial_mode)
        self._unify_ports()

    def _adapt_state(self, state: dict[str, Any], target_mode: ModeKey) -> dict[str, Any]:
        # Simple pass-through adaptation (same state format)
        return state.copy()


class RampSubComponent(CoSimComponent):
    """Rollback-capable ramp model, for event-localized switching tests.

    Integrates ``y`` at a constant ``rate`` so that the time at which ``y``
    reaches a threshold is known analytically. This makes the placement of a
    localized switch checkable against a closed-form expectation.
    """

    def __init__(self, name: str, rate: float = 1.0):
        super().__init__(name, label=name)
        self.rate = rate
        self._y = 0.0
        self.input_specs = {
            "u": PortSpec(name="u", type=PortType.REAL, unit="N", direction="in"),
        }
        self.output_specs = {
            "y": PortSpec(name="y", type=PortType.REAL, unit="m", direction="out"),
        }

    def _initialize_component(self, t0: float) -> None:
        self._y = 0.0

    def _do_step_internal(self, t: float, dt: float) -> None:
        self._y += self.rate * dt

    def _update_output_states(
        self, t: float | None = None, event_names: list[str] | None = None
    ) -> None:
        self.outputs["y"].set(self._y, t=t)
        self._apply_event_ports(t, event_names)

    def get_state(self) -> dict[str, Any]:
        return {"y": self._y}

    def set_state(self, state: dict[str, Any], t: float) -> None:
        self._y = float(state["y"])

    def snapshot_state(self) -> dict[str, Any]:
        return {"y": self._y}

    def restore_state(self, snapshot: dict[str, Any], t: float) -> None:
        self._y = float(snapshot["y"])

    def reset(self) -> None:
        self._y = 0.0


class SwitchableMultiComponent(MultiComponent):
    """Rollback-capable MultiComponent used for switch-indicator tests.

    Both modes are :class:`RampSubComponent` instances with different rates,
    so the active mode is identifiable from the output slope, and state
    transfer carries ``y`` across a switch unchanged.
    """

    def __init__(self, name: str, initial_mode: ModeKey = "SLOW"):
        models = {
            "SLOW": RampSubComponent(f"{name}_SLOW", rate=1.0),
            "FAST": RampSubComponent(f"{name}_FAST", rate=4.0),
        }
        super().__init__(name, models=models, initial_mode=initial_mode)
        self._unify_ports()

    def _adapt_state(self, state: dict[str, Any], target_mode: ModeKey) -> dict[str, Any]:
        return state.copy()


class SignalSubComponent(CoSimComponent):
    """Rollback-capable model that follows a prescribed continuous signal."""

    def __init__(self, name: str, signal: Callable[[float], float]):
        super().__init__(name, label=name)
        self.signal = signal
        self._time = 0.0
        self._y = 0.0
        self.input_specs = {}
        self.output_specs = {
            "y": PortSpec(name="y", type=PortType.REAL, unit="m", direction="out")
        }

    def _initialize_component(self, t0: float) -> None:
        self._time = t0
        self._y = float(self.signal(t0))

    def _do_step_internal(self, t: float, dt: float) -> None:
        self._time = t + dt
        self._y = float(self.signal(self._time))

    def _update_output_states(
        self, t: float | None = None, event_names: list[str] | None = None
    ) -> None:
        self.outputs["y"].set(self._y, t=t)
        self._apply_event_ports(t, event_names)

    def get_state(self) -> dict[str, Any]:
        return {"time": self._time, "y": self._y}

    def set_state(self, state: dict[str, Any], t: float) -> None:
        self._time = float(state["time"])
        self._y = float(state["y"])

    def snapshot_state(self) -> dict[str, float]:
        return {"time": self._time, "y": self._y}

    def restore_state(self, snapshot: dict[str, float], t: float) -> None:
        self._time = float(snapshot["time"])
        self._y = float(snapshot["y"])


class RegionMultiComponent(MultiComponent):
    """Three reusable models for region-identity and localization tests."""

    def __init__(
        self,
        name: str = "RegionPlant",
        signal: Callable[[float], float] = lambda t: t,
        initial_mode: ModeKey = "A",
    ):
        models = {
            mode: SignalSubComponent(f"{name}_{mode}", signal) for mode in ("A", "B", "C")
        }
        super().__init__(name, models=models, initial_mode=initial_mode)
        self._unify_ports()

    def _adapt_state(self, state: dict[str, Any], target_mode: ModeKey) -> dict[str, Any]:
        return state.copy()


class IncompatibleMultiComponent(MultiComponent):
    """
    MultiComponent with incompatible sub-components for testing validation.
    """

    def __init__(self, name: str):
        models = {
            "A": MockSubComponent(f"{name}_A"),
            "B": MockSubComponentIncompatible(f"{name}_B"),
        }
        super().__init__(name, models=models, initial_mode="A")

    def _adapt_state(self, state: dict[str, Any], target_mode: ModeKey) -> dict[str, Any]:
        return state.copy()


class EmptyMultiComponent(MultiComponent):
    """
    MultiComponent that registers no models. Construction must fail.
    """

    def __init__(self, name: str):
        # Empty models map; MultiComponent.__init__ rejects this with ValueError.
        super().__init__(name, models={}, initial_mode="A")

    def _adapt_state(self, state: dict[str, Any], target_mode: ModeKey) -> dict[str, Any]:
        return state.copy()


class UnitMismatchComponent(CoSimComponent):
    """
    Component with specific unit requirements for testing unit mismatch handling in MultiComponent.
    """

    def __init__(self, name: str, unit: str):
        super().__init__(name, label=name)
        self.input_specs = {
            "u": PortSpec(name="u", type=PortType.REAL, unit=unit, direction="in"),
        }
        self.output_specs = {
            "y": PortSpec(name="y", type=PortType.REAL, unit="m", direction="out"),
        }

    def _initialize_component(self, t0: float) -> None:
        return None

    def _do_step_internal(self, t: float, dt: float) -> None:
        return None

    def _update_output_states(
        self, t: float | None = None, event_names: list[str] | None = None
    ) -> None:
        return None

    def get_state(self) -> dict[str, Any]:
        return {}

    def set_state(self, state: dict[str, Any], t: float) -> None:
        return None


class UnitMismatchMultiComponent(MultiComponent):
    """
    MultiComponent with sub-components that have incompatible units for testing unit mismatch handling.
    """

    def __init__(self, name: str):
        models = {
            "A": UnitMismatchComponent(f"{name}_A", unit="N"),
            "B": UnitMismatchComponent(f"{name}_B", unit="N*m"),
        }
        super().__init__(name, models=models, initial_mode="A")
        self._unify_ports()

    def _adapt_state(self, state: dict[str, Any], target_mode: ModeKey) -> dict[str, Any]:
        return state.copy()
