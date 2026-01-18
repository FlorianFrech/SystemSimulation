from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from .base import CoSimComponent
from .events import InternalEventInfo
from .port import PortType

# -------------------------------------------------------------------
# Type Aliases
# -------------------------------------------------------------------
ModeKey = str  # e.g., "FEM", "OpenSim", "EQB"


# -------------------------------------------------------------------
# State Adapter Protocol (for incompatible component interfaces)
# -------------------------------------------------------------------
class StateAdapter(Protocol):
    """Adapter to translate state between components with different interfaces."""

    def adapt_state(
        self, source_state: dict[str, Any], target_component: CoSimComponent
    ) -> dict[str, Any]:
        """Convert state from source format to target component's expected format."""
        ...


# -------------------------------------------------------------------
# Hysteresis for Mode Switching
# -------------------------------------------------------------------
class Hysteresis:
    """Prevents chattering by enforcing minimum dwell time between switches."""

    def __init__(self, dwell_time: float = 0.01):
        self.dwell_time = dwell_time
        self.last_switch_time = 0.0
        self.last_mode: ModeKey = ""

    def can_switch(self, t: float, proposed_mode: ModeKey) -> bool:
        """Check if sufficient time has passed since last switch."""
        if proposed_mode == self.last_mode:
            return False  # Already in this mode
        return (t - self.last_switch_time) >= self.dwell_time

    def record_switch(self, t: float, new_mode: ModeKey):
        """Record a mode switch."""
        self.last_switch_time = t
        self.last_mode = new_mode


# -------------------------------------------------------------------
# Abstract MultiComponent Base Class
# -------------------------------------------------------------------
class MultiComponent(CoSimComponent):
    """
    Abstract base for components that wrap multiple interchangeable sub-components.

    Subclass Responsibilities:
    1. Override `_register_models()` to populate `self.models`
    2. Override `_adapt_state()` for component-specific state translation
    3. (Optional) Set `self.mode_selector` for custom switching logic
    4. (Optional) Set `self.hysteresis` for chattering prevention

    Base Class Handles:
    - Port unification (ensures all models have compatible ports)
    - Mode switching with hysteresis
    - State synchronization between models
    - Input/output delegation to active component
    """

    def __init__(self, name: str, initial_mode: ModeKey, group: str | None = None):
        super().__init__(name, label=name, group=group)

        # Model registry: {mode_key: component}
        self.models: dict[ModeKey, CoSimComponent] = {}

        # Active component tracking
        self.active_mode: ModeKey = initial_mode
        self.active_comp: CoSimComponent | None = None

        # Mode selection strategy (default: never switch)
        self.mode_selector: Callable[[float, dict[str, Any]], ModeKey] | None = None

        # Hysteresis for switching (default: no hysteresis)
        self.hysteresis: Hysteresis | None = None

        # State adapters (optional): {mode_key: adapter}
        self.state_adapters: dict[ModeKey, StateAdapter] = {}

        # List of synchronization events (for logging/debugging)
        self.sync_events: list = []

        # Flag to prevent mode switching during event detection
        self._allow_mode_switching: bool = True

        # Previous and current state for synchronization
        self._prev_state: dict[str, Any] | None = None
        self._curr_state: dict[str, Any] | None = None

    # -------------------------------------------------------------------
    # Registration and Adaptation Hooks
    # -------------------------------------------------------------------
    def _register_models(self) -> None:
        """
        Register all sub-components in self.models.

        Example:
            self.models = {
                "FEM": FEMPendulum(...),
                "OpenSim": OpenSimPendulum(...),
                "EQB": FMUComponent(...)
            }
        """
        raise NotImplementedError(f"{self.name}: Subclass must implement _register_models()")

    def _adapt_state(self, state: dict[str, Any], target_mode: ModeKey) -> dict[str, Any]:
        """
        Adapt state from current component to target component format.
        """
        raise NotImplementedError(f"{self.name}: Subclass must implement _adapt_state()")

    def _require_active_comp(self) -> CoSimComponent:
        """Return active component or raise if not initialized."""
        if self.active_comp is None:
            raise RuntimeError(f"{self.name}: Active component not initialized")
        return self.active_comp

    # -------------------------------------------------------------------
    # Initialization Logic
    # -------------------------------------------------------------------
    def _initialize_component(self, t0: float) -> None:
        """
        Initialize all sub-components and set up port unification.
        """
        # Step 1: Register models (subclass responsibility)
        self._register_models()

        if not self.models:
            raise RuntimeError(f"{self.name}: No models registered in _register_models()")

        # Step 2: Validate initial mode
        if self.active_mode not in self.models:
            raise ValueError(
                f"{self.name}: Initial mode '{self.active_mode}' not in models: {list(self.models.keys())}"
            )

        # Step 3: Initialize all sub-components
        for mode_key, comp in self.models.items():
            if comp is not None:
                comp.initialize(t0)

        # Step 4: Set active component
        self.active_comp = self.models[self.active_mode]

        # Step 5: Unify ports (adopt active component's port specs)
        self._unify_ports()

    # -------------------------------------------------------------------
    # Port Unification and Validation
    # -------------------------------------------------------------------
    def _unify_ports(self) -> None:
        """
        Adopt port specifications from active component and validate compatibility.
        """
        # Adopt active component's port specs
        active_comp = self._require_active_comp()
        self.input_specs = active_comp.input_specs.copy()
        self.output_specs = active_comp.output_specs.copy()

        # Create port states
        self._initialize_ports_from_specs()

        # Validate: all models must have compatible ports
        for mode_key, comp in self.models.items():
            if comp is None:
                continue

            # Check inputs
            for name, spec in self.input_specs.items():
                if name not in comp.input_specs:
                    raise ValueError(f"{self.name}: Model '{mode_key}' missing input port '{name}'")
                # TODO: Add unit compatibility check

            # Check outputs
            for name, spec in self.output_specs.items():
                if name not in comp.output_specs:
                    raise ValueError(
                        f"{self.name}: Model '{mode_key}' missing output port '{name}'"
                    )

    # -------------------------------------------------------------------
    # Time Stepping with Mode Switching
    # -------------------------------------------------------------------
    def _do_step_internal(self, t: float, dt: float) -> None:
        """
        Execute time step with potential mode switching.
        """
        # Step 1: Check if mode switch is needed
        if self._allow_mode_switching and self.mode_selector is not None:
            state = self.get_state()
            proposed_mode = self.mode_selector(t, state)

            # Apply hysteresis if configured
            if self.hysteresis is not None:
                if not self.hysteresis.can_switch(t, proposed_mode):
                    proposed_mode = self.active_mode

            # Perform switch if mode changed
            if proposed_mode != self.active_mode:
                self._switch_mode(proposed_mode, t)

        # Step 2: Execute active component's time step
        self._require_active_comp().do_step(t, dt)

    # -------------------------------------------------------------------
    # Mode Switching with State Synchronization
    # -------------------------------------------------------------------
    def _switch_mode(self, new_mode: ModeKey, t: float) -> None:
        """
        Switch from active_comp to new mode with state synchronization.
        """
        if new_mode not in self.models:
            raise ValueError(f"{self.name}: Unknown mode '{new_mode}'")
        # Store synchronization event
        synch_event: dict[str, Any] = {}
        synch_event["time"] = t
        synch_event["from_mode"] = self.active_mode
        synch_event["to_mode"] = new_mode
        print(f"[{self.name}] Switching: {self.active_mode} to {new_mode} @ t={t:.4f}s")

        # Step 1: Get current state
        synch_event["retrieved"] = self._require_active_comp().get_state()

        # Step 2: Adapt state for new component (subclass hook)
        adapted_state = self._adapt_state(synch_event["retrieved"], new_mode)

        # Step 3: Set state in new component
        new_comp = self.models[new_mode]
        if new_comp is None:
            raise RuntimeError(f"{self.name}: Model '{new_mode}' is not initialized")
        new_comp.set_state(adapted_state, t)

        # Step 4: Update active component
        self.active_mode = new_mode
        self.active_comp = new_comp

        # Step 4.5: Check state consistency (debugging)
        has_state = self._require_active_comp().get_state()
        synch_event["now"] = has_state
        self.sync_events.append(synch_event)

        # Step 5: Record switch in hysteresis
        if self.hysteresis is not None:
            self.hysteresis.record_switch(t, new_mode)

    # -------------------------------------------------------------------
    # Input/Output Delegation
    # -------------------------------------------------------------------
    def set_inputs(self, signals: dict[str, Any], t: float | None = None) -> None:
        """Delegate to all models (for state synchronization) or just active."""
        for comp in self.models.values():
            if comp is not None:
                comp.set_inputs(signals, t)

    def _update_output_states(
        self, t: float | None = None, event_names: list[str] | None = None
    ) -> None:
        """Copy outputs from active component to self.outputs."""
        active_comp = self._require_active_comp()
        for name in self.output_specs.keys():
            value = active_comp.outputs[name].get()
            if value is not None:
                self.outputs[name].set(value, t=t)
        if event_names:
            for event_name in event_names:
                if event_name in self.output_specs.keys():
                    self.outputs[event_name].set(value=True, t=t)
        else:
            for out_port in self.outputs.values():
                if out_port.spec.type == PortType.EVENT:
                    out_port.set(value=False, t=t)

    # -------------------------------------------------------------------
    # State Management Delegation
    # -------------------------------------------------------------------
    def set_state(self, state: dict[str, Any], t: float) -> None:
        """Delegate to active component (with optional adaptation)."""
        adapted_state = self._adapt_state(state, self.active_mode)
        self._require_active_comp().set_state(adapted_state, t)

    def get_state(self) -> dict[str, Any]:
        """Get state from active component."""
        return self._require_active_comp().get_state()

    # -------------------------------------------------------------------
    # Hybrid Capabilities Delegation
    # -------------------------------------------------------------------
    def add_event_indicator(self, name: str, func: Callable, direction: int = 0) -> None:
        """
        Add event indicator to ALL sub-components for consistency.
        """
        for comp in self.models.values():
            if comp is not None and comp.supports_rollback:
                comp.add_event_indicator(name, func, direction)

        # Also add to self for port management
        super().add_event_indicator(name, func, direction)

    def evaluate_event_indicators(self) -> dict[str, float]:
        """Delegate to active component."""
        active_comp = self.active_comp
        if active_comp and active_comp.has_state_events:
            return active_comp.evaluate_event_indicators()
        return {}

    def detect_event_crossings(
        self, previous: dict[str, float], current: dict[str, float], sign_tolerance: float = 1e-10
    ) -> list[str]:
        """Delegate to active component."""
        active_comp = self.active_comp
        if active_comp and active_comp.has_state_events:
            return active_comp.detect_event_crossings(previous, current, sign_tolerance)
        return []

    def snapshot_state(self):
        return self._require_active_comp().snapshot_state()

    def restore_state(self, snapshot, t) -> None:
        self._require_active_comp().restore_state(snapshot, t)

    @property
    def has_state_events(self) -> bool:
        """True if active component has event indicators."""
        return self.active_comp.has_state_events if self.active_comp else False

    @property
    def supports_rollback(self) -> bool:
        """True if active component supports rollback."""
        return self.active_comp.supports_rollback if self.active_comp else False

    def _handle_events_internal(self, event_names: list[str], t: float) -> None:
        """Delegate event handling to active component."""
        if self.active_comp:
            self.active_comp.handle_event(event_names, t)

    def get_internal_event_hints(self) -> list[InternalEventInfo]:
        """Delegate to active component."""
        if self.active_comp and self.active_comp.has_state_events:
            return self.active_comp.get_internal_event_hints()
        return []

    # -------------------------------------------------------------------
    # Reset Logic
    # -------------------------------------------------------------------
    def reset(self) -> None:
        """Reset all sub-components."""
        for comp in self.models.values():
            if comp is not None:
                comp.reset()
