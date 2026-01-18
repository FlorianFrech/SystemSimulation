"""
Test components for MultiComponent unit tests.
Simple mock components that implement the CoSimComponent interface.
"""

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
        super().__init__(name, initial_mode=initial_mode)

    def _register_models(self) -> None:
        self.models = {
            "A": MockSubComponent(f"{self.name}_A", gain=1.0),
            "B": MockSubComponentAlt(f"{self.name}_B"),
        }

    def _adapt_state(self, state: dict[str, Any], target_mode: ModeKey) -> dict[str, Any]:
        # Simple pass-through adaptation (same state format)
        return state.copy()


class IncompatibleMultiComponent(MultiComponent):
    """
    MultiComponent with incompatible sub-components for testing validation.
    """

    def __init__(self, name: str):
        super().__init__(name, initial_mode="A")

    def _register_models(self) -> None:
        self.models = {
            "A": MockSubComponent(f"{self.name}_A"),
            "B": MockSubComponentIncompatible(f"{self.name}_B"),
        }

    def _adapt_state(self, state: dict[str, Any], target_mode: ModeKey) -> dict[str, Any]:
        return state.copy()


class EmptyMultiComponent(MultiComponent):
    """
    MultiComponent that registers no models (for error testing).
    """

    def __init__(self, name: str):
        super().__init__(name, initial_mode="A")

    def _register_models(self) -> None:
        self.models = {}  # Empty!

    def _adapt_state(self, state: dict[str, Any], target_mode: ModeKey) -> dict[str, Any]:
        return state.copy()
