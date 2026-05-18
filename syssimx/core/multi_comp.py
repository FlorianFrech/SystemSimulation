"""Multi-component wrapper for heterogeneous model switching.

This module provides the ``MultiComponent`` class for wrapping multiple
interchangeable simulation models (e.g., FEM, OpenSim, FMU pendulum) under a
unified interface. It enables dynamic mode switching during simulation
with automatic state synchronization between models.

Key Features:
    - **Dynamic Mode Switching**: Switch between different simulation
      models at runtime based on custom criteria (time, cached outputs,
      events)
    - **State Synchronization**: Automatic state transfer and adaptation
      when switching between models with different interfaces
    - **Hysteresis Protection**: Configurable dwell time to prevent
      rapid chattering between modes
    - **Port Unification**: Validates that all sub-models have compatible
      port interfaces
    - **Event Delegation**: Transparently delegates hybrid event detection
      to the currently active sub-component

Typical Use Cases:
    - Multi-fidelity simulation: Switch between high-fidelity FEM and
      reduced-order models based on accuracy requirements
    - Contact dynamics: Use detailed contact model only when contact
      is imminent, otherwise use simpler dynamics
    - Adaptive resolution: Increase model complexity in regions of
      interest, decrease elsewhere

Example:
    Creating a multi-model pendulum::

        class MasterPendulum(MultiComponent):
            def __init__(self, fem, opensim, fmu):
                super().__init__(
                    name="Pendulum",
                    models={"FEM": fem, "OpenSim": opensim, "FMU": fmu},
                    initial_mode="FEM",
                )

            def _adapt_state(self, state, target_mode):
                if target_mode == "FMU":
                    return {'q0': state['q'], 'omega0': state['omega']}
                return state

        # Use with mode selector
        pendulum = MasterPendulum(fem, opensim, fmu)
        pendulum.mode_selector = lambda t: "FEM" if t < 1.0 else "FMU"
        pendulum.hysteresis = Hysteresis(dwell_time=0.05)

See Also:
    :class:`CoSimComponent`: Base class for all components
    :class:`Hysteresis`: Mode switching debounce utility
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any, Protocol

from .base import CoSimComponent
from .events import InternalEventInfo
from .port import PortSpec, PortType

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# Type Aliases
# -------------------------------------------------------------------
ModeKey = str  # e.g., "FEM", "OpenSim", "FMU"


# -------------------------------------------------------------------
# State Adapter Protocol (for incompatible component interfaces)
# -------------------------------------------------------------------
class StateAdapter(Protocol):
    """Protocol for adapting state between components with different interfaces.

    Implement this protocol to provide custom state translation logic
    when switching between models that use different state variable names,
    units, or representations.

    Example:
        >>> class FMUAdapter:
        ...     def adapt_state(self, source_state, target_component):
        ...         # FMU uses 'q0', 'omega0' instead of 'q', 'omega'
        ...         return {
        ...             'q0': source_state['q'],
        ...             'omega0': source_state['omega']
        ...         }
    """

    def adapt_state(
        self, source_state: dict[str, Any], target_component: CoSimComponent
    ) -> dict[str, Any]:
        """Convert state from source format to target component's format.

        Args:
            source_state: State dictionary from the source component,
                typically in the format returned by ``get_state()``.
            target_component: The component that will receive the
                adapted state via ``set_state()``.

        Returns:
            Adapted state dictionary compatible with the target
            component's ``set_state()`` method.
        """
        ...


# -------------------------------------------------------------------
# Hysteresis for Mode Switching
# -------------------------------------------------------------------
class Hysteresis:
    """Minimum dwell time between mode switches.

    Prevents chattering by enforcing a minimum elapsed time between
    consecutive switches. The caller decides whether the proposed mode
    differs from the current one. This class only answers the timing
    question "is the dwell window still open?".

    Attributes:
        dwell_time (float): Minimum time in seconds that must elapse
            between consecutive mode switches.
        last_switch_time (float): Timestamp of the most recent switch.
            Initialized to ``-inf`` so the first switch is always allowed.

    Example:
        >>> hyst = Hysteresis(dwell_time=0.05)
        >>> hyst.in_dwell_window(t=0.02)
        False  # No prior switch yet
        >>> hyst.record_switch(t=0.10)
        >>> hyst.in_dwell_window(t=0.12)
        True   # Only 20 ms since last switch
        >>> hyst.in_dwell_window(t=0.20)
        False  # 100 ms elapsed, window closed
    """

    def __init__(self, dwell_time: float = 0.01):
        """Initialize hysteresis with the given dwell time.

        Args:
            dwell_time: Minimum time in seconds between mode switches.
                Defaults to 0.01 (10 ms).
        """
        self.dwell_time = dwell_time
        self.last_switch_time: float = -float("inf")

    def in_dwell_window(self, t: float) -> bool:
        """Return ``True`` if the dwell window after the last switch is still open."""
        return (t - self.last_switch_time) < self.dwell_time

    def record_switch(self, t: float) -> None:
        """Record that a switch occurred at time ``t``."""
        self.last_switch_time = t


# -------------------------------------------------------------------
# Abstract MultiComponent Base Class
# -------------------------------------------------------------------
class MultiComponent(CoSimComponent):
    """Abstract base class for components wrapping multiple interchangeable models.

    ``MultiComponent`` enables dynamic switching between different simulation
    models during runtime while presenting a unified interface to the rest
    of the co-simulation system. Each sub-model ("mode") can use a different
    solver, fidelity level, or physics representation.

    Subclass Responsibilities:
        1. Construct the sub-components and pass them to ``super().__init__``
           through the ``models`` argument together with ``initial_mode``.
        2. Override ``_adapt_state()`` for component-specific state translation.
        3. (Optional) Set ``self.mode_selector`` for custom switching logic.
        4. (Optional) Set ``self.hysteresis`` for chattering prevention.

    Base Class Handles:
        - Port unification (validates all models have compatible ports)
        - Mode switching with hysteresis protection
        - State synchronization during mode transitions
        - Input/output delegation to the active component
        - Event indicator delegation for hybrid simulation

    Attributes:
        models (dict[ModeKey, CoSimComponent]): Registry mapping mode keys
            (e.g., "FEM", "OpenSim") to component instances. Populated in
            ``__init__`` and fixed for the lifetime of the wrapper.
        active_mode (ModeKey): Key of the currently active model.
        active_comp (CoSimComponent): Reference to the currently active
            component instance. Always set after ``__init__``.
        mode_selector (Callable | None): Function ``(t) -> ModeKey`` that
            determines which mode should be active. Selectors that need state
            information must read cached output ports rather than calling
            ``get_state()``, which can be expensive for high-fidelity models.
            If ``None``, no automatic switching occurs.
        hysteresis (Hysteresis | None): Optional hysteresis controller
            to prevent rapid mode switching.
        state_adapters (dict[ModeKey, StateAdapter]): Optional per-mode
            state adapters for complex translation logic.
        sync_events (list): Log of mode switch events for debugging.

    Example:
        Minimal subclass implementation::

            class DualPendulum(MultiComponent):
                def __init__(self, detailed, simplified):
                    super().__init__(
                        "Pendulum",
                        models={"detailed": detailed, "simplified": simplified},
                        initial_mode="detailed",
                    )

                def _adapt_state(self, state, target_mode):
                    # Both models use same state format
                    return state

    See Also:
        :class:`CoSimComponent`: Parent class with full interface docs
        :class:`Hysteresis`: Mode switching debounce utility
        :class:`StateAdapter`: Protocol for state translation
    """

    def __init__(
        self,
        name: str,
        models: dict[ModeKey, CoSimComponent],
        initial_mode: ModeKey,
        group: str | None = None,
    ):
        """Initialize a multi-component wrapper.

        Args:
            name: Unique identifier for this component in the system.
            models: Mapping of mode keys to component instances. Must
                contain at least ``initial_mode`` and must not be empty.
            initial_mode: Key of the model to activate initially. Must
                be a key in ``models``.
            group: Optional category for component organization.

        Raises:
            ValueError: If ``models`` is empty or ``initial_mode`` is not
                a key in ``models``.

        Example:
            >>> super().__init__(
            ...     name="Pendulum",
            ...     models={"FEM": fem, "FMU": fmu},
            ...     initial_mode="FEM",
            ...     group="Plant",
            ... )
        """
        if not models:
            raise ValueError(f"{name}: 'models' must not be empty")
        if initial_mode not in models:
            raise ValueError(
                f"{name}: initial_mode '{initial_mode}' not in models {list(models.keys())}"
            )

        super().__init__(name, label=name, group=group)

        # Model registry and active references (fixed at construction time)
        self.models: dict[ModeKey, CoSimComponent] = models
        self.active_mode: ModeKey = initial_mode
        self.active_comp: CoSimComponent = models[initial_mode]

        # Mode selection strategy (default: never switch)
        self.mode_selector: Callable[[float], ModeKey] | None = None

        # Hysteresis for switching (default: no hysteresis)
        self.hysteresis: Hysteresis | None = None

        # State adapters (optional): {mode_key: adapter}
        self.state_adapters: dict[ModeKey, StateAdapter] = {}

        # List of synchronization events (for logging/debugging)
        self.sync_events: list = []

        # Flag to prevent mode switching during event detection
        self._allow_mode_switching: bool = True

        # Latest input dict and timestamp seen by set_inputs. Used to
        # bring a newly activated model up to date during a mode switch
        # without forwarding inputs to inactive models on every step.
        self._latest_inputs: tuple[dict[str, Any], float | None] | None = None

        # When True, switch records in ``sync_events`` include the
        # pre-adaptation source state and the synchronized target state.
        # Default False because reading the target state calls
        # ``active_comp.get_state()`` once per switch, which can be
        # expensive for high-fidelity models.
        self.record_switch_state: bool = False

        # Previous and current state for synchronization
        self._prev_state: dict[str, Any] | None = None
        self._curr_state: dict[str, Any] | None = None

    # -------------------------------------------------------------------
    # State Adaptation Hook
    # -------------------------------------------------------------------
    def _adapt_state(self, state: dict[str, Any], target_mode: ModeKey) -> dict[str, Any]:
        """Adapt state dictionary for the target model's interface.

        Subclasses must override this method to translate state between
        models that use different variable names, units, or representations.
        Called during mode switching to transform the current model's state
        into a format the target model can accept.

        Args:
            state: State dictionary from the current active component,
                as returned by ``get_state()``.
            target_mode: Key of the model being switched to.

        Returns:
            Adapted state dictionary compatible with the target model's
            ``set_state()`` method.

        Raises:
            NotImplementedError: If not overridden by subclass.

        Example:
            >>> def _adapt_state(self, state, target_mode):
            ...     if target_mode == "FMU":
            ...         # FMU uses initial condition naming
            ...         return {
            ...             'q0': state['q'],
            ...             'omega0': state['omega'],
            ...             'torque': state['torque']
            ...         }
            ...     return state  # Other models use standard naming

        Note:
            This is the primary extension point for handling heterogeneous
            model interfaces. If models share identical state formats,
            simply return ``state`` unchanged.
        """
        raise NotImplementedError(f"{self.name}: Subclass must implement _adapt_state()")

    # -------------------------------------------------------------------
    # Initialization Logic
    # -------------------------------------------------------------------
    def _initialize_component(self, t0: float) -> None:
        """Initialize all registered sub-components at time ``t0``.

        Models and the active component are fixed by ``__init__``. This
        hook only initializes each registered sub-component so that any
        of them is ready for activation on a later mode switch.

        Args:
            t0: Initial simulation time in seconds.

        Note:
            All sub-components are initialized, not just the active one.
        """
        for comp in self.models.values():
            if comp is not None:
                comp.initialize(t0)

    # -------------------------------------------------------------------
    # Port Unification and Validation
    # -------------------------------------------------------------------
    @staticmethod
    def _validate_port_compatibility(
        ref_spec: PortSpec, spec: PortSpec, model_name: str, port_name: str
    ) -> None:
        """Validate that two PortSpecs are compatible for MultiComponent use."""
        if ref_spec.name != port_name or spec.name != port_name:
            raise ValueError(
                f"Port name mismatch for '{port_name}' in model '{model_name}': "
                f"got '{spec.name}', expected '{port_name}'."
            )
        if ref_spec.direction != spec.direction:
            raise ValueError(
                f"Port direction mismatch for '{port_name}' in model '{model_name}': "
                f"{ref_spec.direction} vs {spec.direction}."
            )
        if ref_spec.type != spec.type:
            raise ValueError(
                f"Port type mismatch for '{port_name}' in model '{model_name}': "
                f"{ref_spec.type} vs {spec.type}."
            )
        if not PortSpec.compatible(ref_spec, spec):
            raise ValueError(
                f"Port unit/type incompatibility for '{port_name}' in model '{model_name}': "
                f"{ref_spec} vs {spec}."
            )

    def _unify_ports(self) -> None:
        """Adopt port specifications from active component and validate compatibility.

        Copies input and output port specifications from the active component
        to this ``MultiComponent``, then validates that all registered models
        have compatible port interfaces.

        Raises:
            ValueError: If any model is missing a required input or output
                port that exists in the active component's specification.

        Note:
            This ensures the ``MultiComponent`` presents a consistent interface
            regardless of which sub-model is active. All models must have at
            least the same ports as the active component (they may have more).
        """
        # Adopt active component's port specs
        active_comp = self.active_comp
        self.input_specs = active_comp.input_specs.copy()
        self.output_specs = active_comp.output_specs.copy()

        # Validate: all models must have compatible ports
        for mode_key, comp in self.models.items():
            if comp is None:
                continue

            # Check inputs
            for name, spec in self.input_specs.items():
                if name not in comp.input_specs:
                    raise ValueError(f"{self.name}: Model '{mode_key}' missing input port '{name}'")
                self._validate_port_compatibility(spec, comp.input_specs[name], mode_key, name)

            # Check outputs
            for name, spec in self.output_specs.items():
                if name not in comp.output_specs:
                    raise ValueError(
                        f"{self.name}: Model '{mode_key}' missing output port '{name}'"
                    )
                self._validate_port_compatibility(spec, comp.output_specs[name], mode_key, name)

    # -------------------------------------------------------------------
    # Time Stepping with Mode Switching
    # -------------------------------------------------------------------
    def _do_step_internal(self, t: float, dt: float) -> None:
        """Execute one macro step, switching modes first if requested.

        Args:
            t: Current simulation time in seconds.
            dt: Macro step size in seconds.

        Note:
            Mode switching can be temporarily disabled by setting
            ``_allow_mode_switching = False``. This is used by the hybrid
            algorithm during trial steps so that event detection does not
            change the active model while a rollback snapshot is valid.
        """
        if dt <= 0.0:
            self.active_comp.do_step(t, dt)
            return
        target_mode = self._select_target_mode(t)
        if target_mode != self.active_mode:
            self._switch_mode(target_mode, t)
        self.active_comp.do_step(t, dt)


    def _select_target_mode(self, t: float) -> ModeKey:
        """Return the desired mode at ``t``, honoring switching guards.

        Returns the current ``active_mode`` when switching is disabled,
        when no selector is configured, or when the hysteresis dwell
        window is still open. Otherwise returns the selector's proposal.

        Args:
            t: Current simulation time in seconds.

        Returns:
            The mode key that should be active for the next step. Equal to
            ``self.active_mode`` if no switch is requested or allowed.
        """
        if not self._allow_mode_switching or self.mode_selector is None:
            return self.active_mode
        if self.hysteresis is not None and self.hysteresis.in_dwell_window(t):
            return self.active_mode
        return self.mode_selector(t)

    # -------------------------------------------------------------------
    # Mode Switching with State Synchronization
    # -------------------------------------------------------------------
    def _switch_mode(self, new_mode: ModeKey, t: float) -> None:
        """Switch to a new mode with state synchronization.

        Orchestrates the transition. Validates the target, transfers the
        adapted state to the new active component, records the switch event
        for inspection, and notifies the hysteresis controller.

        Args:
            new_mode: Key of the mode to switch to. Must exist in
                ``self.models`` and be non-None.
            t: Current simulation time at which the switch occurs.

        Raises:
            ValueError: If ``new_mode`` is not in the models registry.
            RuntimeError: If the target model is ``None``.
        """
        if new_mode not in self.models:
            raise ValueError(f"{self.name}: Unknown mode '{new_mode}'")
        new_comp = self.models[new_mode]
        if new_comp is None:
            raise RuntimeError(f"{self.name}: Model '{new_mode}' is not initialized")

        from_mode = self.active_mode
        logger.info("[%s] Switching: %s to %s @ t=%.4fs", self.name, from_mode, new_mode, t)

        retrieved_state = self._perform_state_transfer(new_comp, new_mode, t)
        self._capture_switch_event(t, from_mode, new_mode, retrieved_state)

        if self.hysteresis is not None:
            self.hysteresis.record_switch(t)

    def _perform_state_transfer(
        self, new_comp: CoSimComponent, new_mode: ModeKey, t: float
    ) -> dict[str, Any]:
        """Move physical state from the current active model to ``new_comp``.

        Retrieves the state of the active component, replays the most
        recent inputs onto ``new_comp`` so it is current with the outgoing
        model, adapts the state for the target model, writes it to
        ``new_comp``, and promotes ``new_comp`` to be the active component.

        Args:
            new_comp: The component instance that will become active.
            new_mode: Key of the target mode used by ``_adapt_state()``.
            t: Current simulation time.

        Returns:
            The retrieved (pre-adaptation) state of the previously active
            component, for inclusion in the switch event log.
        """
        retrieved = self.active_comp.get_state()
        adapted = self._adapt_state(retrieved, new_mode)
        if self._latest_inputs is not None:
            signals, t_inputs = self._latest_inputs
            new_comp.set_inputs(signals, t_inputs)
        new_comp.set_state(adapted, t)
        self.active_mode = new_mode
        self.active_comp = new_comp
        return retrieved

    def _capture_switch_event(
        self, t: float, from_mode: ModeKey, to_mode: ModeKey, retrieved: dict[str, Any]
    ) -> None:
        """Append one record of the completed switch to ``sync_events``.

        Always logs the time, source mode, and target mode. When
        ``self.record_switch_state`` is ``True``, the record also
        includes the pre-adaptation source state (``retrieved``) and
        a fresh snapshot of the new active component's state (``now``).
        The ``now`` snapshot calls ``active_comp.get_state()``, which
        can be expensive for high-fidelity models. ``record_switch_state``
        defaults to ``False`` and should be enabled only for debugging
        synchronization issues.

        Args:
            t: Time at which the switch occurred.
            from_mode: Mode key that was active before the switch.
            to_mode: Mode key that is active after the switch.
            retrieved: State exported from the source component before
                adaptation.
        """
        record: dict[str, Any] = {
            "time": t,
            "from_mode": from_mode,
            "to_mode": to_mode,
        }
        if self.record_switch_state:
            record["retrieved"] = retrieved
            record["now"] = self.active_comp.get_state()
        self.sync_events.append(record)

    # -------------------------------------------------------------------
    # Input/Output Delegation
    # -------------------------------------------------------------------
    def set_inputs(self, signals: dict[str, Any], t: float | None = None) -> None:
        """Forward inputs to the active sub-component and cache them.

        Only the active model receives inputs each step. The cached
        ``(signals, t)`` pair is replayed onto the target model inside
        ``_perform_state_transfer`` when a mode switch occurs, so the
        newly activated model sees the same inputs the outgoing one had.

        Args:
            signals: Dictionary mapping input port names to values.
            t: Optional timestamp for the input values.
        """
        self._latest_inputs = (signals, t)
        self.active_comp.set_inputs(signals, t)

    def _update_output_states(
        self, t: float | None = None, event_names: list[str] | None = None
    ) -> None:
        """Copy output values from the active component to this wrapper.

        Reads all output values from the active sub-component and writes
        them to this ``MultiComponent``'s output ports. Also handles event
        port updates based on which events fired.

        Args:
            t: Current simulation time for timestamping port values.
            event_names: List of event names that just occurred. Event
                ports matching these names are set to ``True``; others
                are set to ``False``.

        Note:
            This ensures the ``MultiComponent`` always reflects the active
            component's outputs, regardless of which model is active.
        """
        active_comp = self.active_comp
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

    def evaluate_outputs(self, inputs: dict[str, Any], t: float | None = None) -> dict[str, Any]:
        saved = self._allow_mode_switching
        self._allow_mode_switching = False
        try:
            outputs = self.active_comp.evaluate_outputs(inputs, t=t)
            for name, value in outputs.items():
                if name in self.outputs and value is not None:
                    self.outputs[name].set(value, t=t)
            return outputs
        finally:
            self._allow_mode_switching = saved

    # -------------------------------------------------------------------
    # State Management Delegation
    # -------------------------------------------------------------------
    def set_state(self, state: dict[str, Any], t: float) -> None:
        """Set state on the active component with adaptation.

        Adapts the provided state for the active model's interface using
        ``_adapt_state()``, then delegates to the active component.

        Args:
            state: State dictionary to set. Will be adapted for the
                active model's expected format.
            t: Time at which to set the state.

        See Also:
            :meth:`_adapt_state`: State translation hook
        """
        adapted_state = self._adapt_state(state, self.active_mode)
        self.active_comp.set_state(adapted_state, t)

    def get_state(self) -> dict[str, Any]:
        """Get the current state from the active component.

        Returns:
            State dictionary from the active sub-component, in that
            component's native format.

        Note:
            The returned state format depends on which model is active.
            Use ``_adapt_state()`` if you need to translate to another
            model's format.
        """
        return self.active_comp.get_state()

    # -------------------------------------------------------------------
    # Hybrid Capabilities Delegation
    # -------------------------------------------------------------------
    def add_event_indicator(self, name: str, func: Callable, direction: int = 0) -> None:
        """Register an event indicator on all sub-components.

        Adds the event indicator to every sub-component that supports
        rollback, ensuring consistent event detection regardless of
        which model is active.

        Args:
            name: Unique name for the event indicator.
            func: Callable ``(component) -> float`` that returns the
                indicator value. Should work with any sub-component.
            direction: Zero-crossing direction: -1 (falling), 0 (both),
                +1 (rising).

        Note:
            The indicator function should access state through the
            unified interface (e.g., ``comp.get_outputs()``) rather
            than model-specific internals to work across all models.
        """
        for comp in self.models.values():
            if comp is not None and comp.supports_rollback:
                comp.add_event_indicator(name, func, direction)

        # Also add to self for port management
        super().add_event_indicator(name, func, direction)

    def evaluate_event_indicators(self) -> dict[str, float]:
        """Evaluate event indicators on the active component.

        Delegates to the active sub-component's event indicator
        evaluation if it has state events configured.

        Returns:
            Dictionary mapping indicator names to their current values.
            Empty dict if active component has no event indicators.
        """
        if self.active_comp.has_state_events:
            return self.active_comp.evaluate_event_indicators()
        return {}

    def detect_event_crossings(
        self, previous: dict[str, float], current: dict[str, float], sign_tolerance: float = 1e-10
    ) -> list[str]:
        """Detect zero-crossings on the active component.

        Delegates to the active sub-component's crossing detection
        if it has state events configured.

        Args:
            previous: Indicator values before the step.
            current: Indicator values after the step.
            sign_tolerance: Threshold for zero detection.

        Returns:
            List of indicator names that experienced crossings.
            Empty list if active component has no event indicators.
        """
        if self.active_comp.has_state_events:
            return self.active_comp.detect_event_crossings(previous, current, sign_tolerance)
        return []

    def snapshot_state(self):
        """Capture state snapshot from the active component.

        Delegates to the active sub-component's snapshot mechanism.
        Used for time rollback during event localization.

        Returns:
            Opaque snapshot from the active component.

        Warning:
            The snapshot is only valid for restoration to the same
            active component. Mode switches invalidate snapshots.
        """
        return self.active_comp.snapshot_state()

    def restore_state(self, snapshot, t) -> None:
        """Restore state snapshot on the active component.

        Delegates to the active sub-component's restore mechanism.
        Used to roll back time during event localization bisection.

        Args:
            snapshot: Opaque snapshot from ``snapshot_state()``.
            t: Time at which the snapshot was taken.

        Warning:
            Must restore to the same component that created the snapshot.
            Do not switch modes between snapshot and restore.
        """
        self.active_comp.restore_state(snapshot, t)

    @property
    def has_state_events(self) -> bool:
        """``True`` if the currently active sub-component has event indicators."""
        return self.active_comp.has_state_events

    @property
    def supports_rollback(self) -> bool:
        """``True`` if the currently active sub-component supports state rollback."""
        return self.active_comp.supports_rollback

    def _handle_events_internal(self, event_names: list[str], t: float) -> None:
        """Delegate event handling to the active component.

        Args:
            event_names: List of events that occurred at time ``t``.
            t: Precise time at which the events occurred.
        """
        self.active_comp.handle_event(event_names, t)

    def get_internal_event_hints(self) -> list[InternalEventInfo]:
        """Retrieve internal event hints from the active component.

        Forwarding is unconditional so that hints reported by the active
        model during a trial step are visible to the hybrid algorithm and
        can short-circuit bisection.

        Returns:
            List of ``InternalEventInfo`` objects from the active component.
        """
        return self.active_comp.get_internal_event_hints()

    # -------------------------------------------------------------------
    # Detect Direct Feedthrough
    # -------------------------------------------------------------------
    def _detect_direct_feedthrough(self):
        """Determine if all models have consistent direct feedthrough.

        Checks the ``direct_feedthrough`` property of all registered
        sub-components. If they differ, raises an error. Otherwise,
        sets this ``MultiComponent``'s ``direct_feedthrough`` property
        accordingly.
        """
        self.direct_feedthrough = None
        for mode_key, comp in self.models.items():
            if comp is None:
                continue
            if self.direct_feedthrough is None:
                self.direct_feedthrough = comp.direct_feedthrough
            elif self.direct_feedthrough != comp.direct_feedthrough:
                raise ValueError(
                    f"{self.name}: Inconsistent direct feedthrough across models. "
                    f"Model '{mode_key}' has direct_feedthrough={comp.direct_feedthrough}, "
                    f"expected {self.direct_feedthrough}."
                )

    # -------------------------------------------------------------------
    # Reset Logic
    # -------------------------------------------------------------------
    def reset(self) -> None:
        """Reset all registered sub-components.

        Calls ``reset()`` on every non-None model in the registry,
        clearing their state and allowing re-initialization. Also
        clears the cached input replay buffer.

        Note:
            Unlike the base class, this resets ALL models, not just
            the active one. This ensures clean state when the
            ``MultiComponent`` is re-initialized.
        """
        super().reset()
        for comp in self.models.values():
            if comp is not None:
                comp.reset()
        self._latest_inputs = None
