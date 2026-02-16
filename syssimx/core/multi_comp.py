"""Multi-component wrapper for heterogeneous model switching.

This module provides the ``MultiComponent`` class for wrapping multiple
interchangeable simulation models (e.g., FEM, OpenSim, FMU pendulum) under a
unified interface. It enables dynamic mode switching during simulation
with automatic state synchronization between models.

Key Features:
    - **Dynamic Mode Switching**: Switch between different simulation
      models at runtime based on custom criteria (time, state, events)
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
                super().__init__(name="Pendulum", initial_mode="FEM")
                self._fem = fem
                self._opensim = opensim
                self._fmu = fmu

            def _register_models(self):
                self.models = {
                    "FEM": self._fem,
                    "OpenSim": self._opensim,
                    "EQB": self._fmu
                }

            def _adapt_state(self, state, target_mode):
                if target_mode == "EQB":
                    return {'q0': state['q'], 'omega0': state['omega']}
                return state

        # Use with mode selector
        pendulum = MasterPendulum(fem, opensim, fmu)
        pendulum.mode_selector = lambda t, state: "FEM" if t < 1.0 else "EQB"
        pendulum.hysteresis = Hysteresis(dwell_time=0.05)

See Also:
    :class:`CoSimComponent`: Base class for all components
    :class:`Hysteresis`: Mode switching debounce utility
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from .base import CoSimComponent
from .events import InternalEventInfo
from .port import PortSpec, PortType

# -------------------------------------------------------------------
# Type Aliases
# -------------------------------------------------------------------
ModeKey = str  # e.g., "FEM", "OpenSim", "EQB"


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
    """Debounce utility to prevent rapid mode switching (chattering).

    Enforces a minimum dwell time between mode switches. This is essential
    when mode selection criteria operate near threshold boundaries, where
    small oscillations could cause rapid back-and-forth switching.

    Attributes:
        dwell_time (float): Minimum time (seconds) that must elapse between
            consecutive mode switches.
        last_switch_time (float): Timestamp of the most recent mode switch.
        last_mode (ModeKey): The mode that was switched to most recently.

    Example:
        >>> hysteresis = Hysteresis(dwell_time=0.05)  # 50ms minimum
        >>> hysteresis.record_switch(t=0.0, new_mode="FEM")
        >>> hysteresis.can_switch(t=0.02, proposed_mode="EQB")
        False  # Only 20ms elapsed
        >>> hysteresis.can_switch(t=0.06, proposed_mode="EQB")
        True   # 60ms elapsed, switch allowed
    """

    def __init__(self, dwell_time: float = 0.01):
        """Initialize hysteresis with specified dwell time.

        Args:
            dwell_time: Minimum time in seconds between mode switches.
                Defaults to 0.01 (10ms).
        """
        self.dwell_time = dwell_time
        self.last_switch_time = 0.0
        self.last_mode: ModeKey = ""

    def can_switch(self, t: float, proposed_mode: ModeKey) -> bool:
        """Check if a mode switch is allowed at the given time.

        A switch is allowed if:
        1. The proposed mode differs from the current mode, AND
        2. Sufficient time has elapsed since the last switch

        Args:
            t: Current simulation time in seconds.
            proposed_mode: The mode being proposed to switch to.

        Returns:
            ``True`` if the switch is allowed, ``False`` if blocked
            by hysteresis (either same mode or insufficient dwell time).
        """
        if proposed_mode == self.last_mode:
            return False  # Already in this mode
        return (t - self.last_switch_time) >= self.dwell_time

    def record_switch(self, t: float, new_mode: ModeKey):
        """Record that a mode switch occurred.

        Call this after successfully completing a mode switch to
        update the hysteresis state.

        Args:
            t: Time at which the switch occurred.
            new_mode: The mode that was switched to.
        """
        self.last_switch_time = t
        self.last_mode = new_mode


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
        1. Override ``_register_models()`` to populate ``self.models``
        2. Override ``_adapt_state()`` for component-specific state translation
        3. (Optional) Set ``self.mode_selector`` for custom switching logic
        4. (Optional) Set ``self.hysteresis`` for chattering prevention

    Base Class Handles:
        - Port unification (validates all models have compatible ports)
        - Mode switching with hysteresis protection
        - State synchronization during mode transitions
        - Input/output delegation to the active component
        - Event indicator delegation for hybrid simulation

    Attributes:
        models (dict[ModeKey, CoSimComponent]): Registry mapping mode keys
            (e.g., "FEM", "OpenSim") to component instances.
        active_mode (ModeKey): Key of the currently active model.
        active_comp (CoSimComponent | None): Reference to the currently
            active component instance.
        mode_selector (Callable | None): Function ``(t, state) -> ModeKey``
            that determines which mode should be active. If ``None``,
            no automatic switching occurs.
        hysteresis (Hysteresis | None): Optional hysteresis controller
            to prevent rapid mode switching.
        state_adapters (dict[ModeKey, StateAdapter]): Optional per-mode
            state adapters for complex translation logic.
        sync_events (list): Log of mode switch events for debugging.

    Example:
        Minimal subclass implementation::

            class DualPendulum(MultiComponent):
                def __init__(self, detailed, simplified):
                    super().__init__("Pendulum", initial_mode="detailed")
                    self._detailed = detailed
                    self._simplified = simplified

                def _register_models(self):
                    self.models = {
                        "detailed": self._detailed,
                        "simplified": self._simplified
                    }

                def _adapt_state(self, state, target_mode):
                    # Both models use same state format
                    return state

    See Also:
        :class:`CoSimComponent`: Parent class with full interface docs
        :class:`Hysteresis`: Mode switching debounce utility
        :class:`StateAdapter`: Protocol for state translation
    """

    def __init__(self, name: str, initial_mode: ModeKey, group: str | None = None):
        """Initialize a multi-component wrapper.

        Args:
            name: Unique identifier for this component in the system.
            initial_mode: Key of the model to activate initially. Must
                match a key in ``self.models`` after ``_register_models()``
                is called.
            group: Optional category for component organization.

        Example:
            >>> super().__init__("Pendulum", initial_mode="FEM", group="Plant")
        """
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
        """Register all sub-components in the models dictionary.

        Subclasses must override this method to populate ``self.models``
        with the available simulation models. Each model is associated
        with a string key (mode) that identifies it.

        Called automatically during ``_initialize_component()``.

        Raises:
            NotImplementedError: If not overridden by subclass.

        Example:
            >>> def _register_models(self):
            ...     self.models = {
            ...         "FEM": self._fem_component,
            ...         "OpenSim": self._opensim_component,
            ...         "EQB": self._fmu_component
            ...     }

        Note:
            Models can be ``None`` if conditionally available. The
            ``initial_mode`` must point to a non-None model.
        """
        raise NotImplementedError(f"{self.name}: Subclass must implement _register_models()")

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
            ...     if target_mode == "EQB":
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

    def _require_active_comp(self) -> CoSimComponent:
        """Return the active component or raise if not initialized.

        Internal helper to safely access ``active_comp`` with a clear
        error message if accessed before initialization.

        Returns:
            The currently active sub-component.

        Raises:
            RuntimeError: If ``active_comp`` is ``None`` (not initialized).
        """
        if self.active_comp is None:
            raise RuntimeError(f"{self.name}: Active component not initialized")
        return self.active_comp

    # -------------------------------------------------------------------
    # Initialization Logic
    # -------------------------------------------------------------------
    def _initialize_component(self, t0: float) -> None:
        """Initialize all sub-components and set up port unification.

        This method orchestrates the initialization sequence:

        1. Calls ``_register_models()`` to populate the models registry
        2. Validates that ``initial_mode`` exists in the registry
        3. Calls ``_pre_initialize_models()`` for parameter synchronization
        4. Initializes all registered sub-components at time ``t0``
        5. Sets the active component based on ``initial_mode``
        6. Unifies ports by adopting the active component's specifications
        7. Verifies identical direct feedthrough property across models
        8. Calls ``_post_initialize()`` for additional setup

        Args:
            t0: Initial simulation time in seconds.

        Raises:
            RuntimeError: If no models are registered after calling
                ``_register_models()``.
            ValueError: If ``initial_mode`` is not in the models registry.

        Note:
            All sub-components are initialized, not just the active one.
            This ensures they're ready for mode switching at any time.

        See Also:
            :meth:`_pre_initialize_models`: Parameter synchronization hook
            :meth:`_post_initialize`: Post-initialization setup hook
        """
        if not self.models:
            raise RuntimeError(f"{self.name}: No models registered in _register_models()")

        if self.active_mode not in self.models:
            raise ValueError(
                f"{self.name}: Initial mode '{self.active_mode}' not in models: {list(self.models.keys())}"
            )

        for mode_key, comp in self.models.items():
            if comp is not None:
                comp.initialize(t0)

        self.active_comp = self.models[self.active_mode]

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
        active_comp = self._require_active_comp()
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
        """Execute time step with potential mode switching.

        Before stepping, checks if the mode selector requests a different
        mode. If so, and hysteresis allows, performs mode switching with
        state synchronization. Then delegates the actual time step to the
        active component.

        Args:
            t: Current simulation time in seconds.
            dt: Time step size in seconds.

        Note:
            Mode switching can be temporarily disabled by setting
            ``_allow_mode_switching = False``. This is useful during
            event detection bisection to prevent mode changes mid-search.
        """
        # Step 1: Check if mode switch is needed
        if self._allow_mode_switching and self.mode_selector is not None:
            state = self.get_state()
            proposed_mode = self.mode_selector(t, state)

            # a) Apply hysteresis if configured
            if self.hysteresis is not None:
                if not self.hysteresis.can_switch(t, proposed_mode):
                    proposed_mode = self.active_mode

            # b) Perform switch if mode changed
            if proposed_mode != self.active_mode:
                self._switch_mode(proposed_mode, t)

        # Step 2: Execute active component's time step
        self._require_active_comp().do_step(t, dt)

    # -------------------------------------------------------------------
    # Mode Switching with State Synchronization
    # -------------------------------------------------------------------
    def _switch_mode(self, new_mode: ModeKey, t: float) -> None:
        """Switch to a new mode with state synchronization.

        Performs the complete mode transition sequence:

        1. Retrieves current state from the active component
        2. Adapts state for the target model via ``_adapt_state()``
        3. Sets the adapted state in the new component
        4. Updates ``active_mode`` and ``active_comp``
        5. Records the switch in hysteresis (if configured)
        6. Logs the switch event to ``sync_events`` for debugging

        Args:
            new_mode: Key of the mode to switch to. Must exist in
                ``self.models`` and be non-None.
            t: Current simulation time at which the switch occurs.

        Raises:
            ValueError: If ``new_mode`` is not in the models registry.
            RuntimeError: If the target model is ``None``.

        Note:
            Prints a log message when switching. The ``sync_events`` list
            captures detailed before/after state for debugging synchronization
            issues.
        """
        version = "old"
        synch_event: dict[str, Any]
        # -------------------------------------------------------------------
        if version == "new":
            if new_mode not in self.models:
                raise ValueError(f"{self.name}: Unknown mode '{new_mode}'")

            # Store synchronization event
            synch_event = {}
            synch_event["time"] = t
            synch_event["from_mode"] = self.active_mode
            synch_event["to_mode"] = new_mode
            print(f"[{self.name}] Switching: {self.active_mode} to {new_mode} @ t={t:.4f}s")

            # Step 1: Get current state from active component
            active = self._require_active_comp()
            if hasattr(active, "get_macro_history"):
                hist = active.get_macro_history()
            else:
                hist = {"current": active.get_state(), "previous": None, "dt": None}

            synch_event["retrieved"] = hist

            # Step 2: Adapt state for new component (subclass hook)
            adapted = self._adapt_state(hist, new_mode)
            new_comp = self.models[new_mode]
            if new_comp is None:
                raise RuntimeError(f"{self.name}: Model '{new_mode}' is not initialized")

            # Step 3: Set state in new component
            if hasattr(new_comp, "set_state_with_history"):
                new_comp.set_state_with_history(
                    adapted["current"], adapted["previous"], adapted["dt"], t
                )
            else:
                new_comp.set_state(adapted["current"], t)

            # Step 4: Update active component
            self.active_mode = new_mode
            self.active_comp = new_comp
            synch_event["now"] = self._require_active_comp().get_state()
            self.sync_events.append(synch_event)

            # Step 5: Record switch in hysteresis
            if self.hysteresis is not None:
                self.hysteresis.record_switch(t, new_mode)
        # -------------------------------------------------------------------
        if version == "old":
            if new_mode not in self.models:
                raise ValueError(f"{self.name}: Unknown mode '{new_mode}'")

            synch_event = {}
            synch_event["time"] = t
            synch_event["from_mode"] = self.active_mode
            synch_event["to_mode"] = new_mode
            print(f"[{self.name}] Switching: {self.active_mode} to {new_mode} @ t={t:.4f}s")

            synch_event["retrieved"] = self._require_active_comp().get_state()

            adapted_state = self._adapt_state(synch_event["retrieved"], new_mode)

            new_comp = self.models[new_mode]
            if new_comp is None:
                raise RuntimeError(f"{self.name}: Model '{new_mode}' is not initialized")
            new_comp.set_state(adapted_state, t)

            self.active_mode = new_mode
            self.active_comp = new_comp

            # Step 4.5: Check state consistency (debugging)
            has_state = self._require_active_comp().get_state()
            synch_event["now"] = has_state
            self.sync_events.append(synch_event)

            if self.hysteresis is not None:
                self.hysteresis.record_switch(t, new_mode)

    # -------------------------------------------------------------------
    # Input/Output Delegation
    # -------------------------------------------------------------------
    def set_inputs(self, signals: dict[str, Any], t: float | None = None) -> None:
        """Set inputs on all registered sub-components.

        Propagates input signals to all models, not just the active one.
        This keeps all models synchronized with the current inputs, enabling
        seamless mode switching without re-setting inputs.

        Args:
            signals: Dictionary mapping input port names to values.
            t: Optional timestamp for the input values.

        Note:
            This differs from the base class behavior which only sets
            inputs on the component itself. Here, we delegate to all
            models for state synchronization purposes.
        """
        for comp in self.models.values():
            if comp is not None:
                comp.set_inputs(signals, t)

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
        self._require_active_comp().set_state(adapted_state, t)

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
        return self._require_active_comp().get_state()

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
        active_comp = self.active_comp
        if active_comp and active_comp.has_state_events:
            return active_comp.evaluate_event_indicators()
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
        active_comp = self.active_comp
        if active_comp and active_comp.has_state_events:
            return active_comp.detect_event_crossings(previous, current, sign_tolerance)
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
        return self._require_active_comp().snapshot_state()

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
        self._require_active_comp().restore_state(snapshot, t)

    @property
    def has_state_events(self) -> bool:
        """Check if the active component has event indicators.

        Returns:
            ``True`` if the currently active sub-component has one or
            more event indicators registered.
        """
        return self.active_comp.has_state_events if self.active_comp else False

    @property
    def supports_rollback(self) -> bool:
        """Check if the active component supports state rollback.

        Returns:
            ``True`` if the currently active sub-component implements
            ``snapshot_state()`` and ``restore_state()``.
        """
        return self.active_comp.supports_rollback if self.active_comp else False

    def _handle_events_internal(self, event_names: list[str], t: float) -> None:
        """Delegate event handling to the active component.

        Forwards the event handling call to the active sub-component,
        which will execute its ``handle_event()`` method.

        Args:
            event_names: List of events that occurred at time ``t``.
            t: Precise time at which the events occurred.
        """
        if self.active_comp:
            self.active_comp.handle_event(event_names, t)

    def get_internal_event_hints(self) -> list[InternalEventInfo]:
        """Retrieve internal event hints from the active component.

        Delegates to the active sub-component to get any timing hints
        from internal micro-stepping for event localization.

        Returns:
            List of ``InternalEventInfo`` objects from the active
            component. Empty list if no hints available.
        """
        if self.active_comp and self.active_comp.has_state_events:
            return self.active_comp.get_internal_event_hints()
        return []

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
        clearing their state and allowing re-initialization.

        Note:
            Unlike the base class, this resets ALL models, not just
            the active one. This ensures clean state when the
            ``MultiComponent`` is re-initialized.
        """
        super().reset()
        for comp in self.models.values():
            if comp is not None:
                comp.reset()
