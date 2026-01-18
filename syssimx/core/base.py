"""
Co-simulation component base classes and interfaces.

State Management API
--------------------
Components provide two distinct state management interfaces:

**Physical State Transfer** (for mode switching and inspection):
    - get_state(): Export human-readable physical variables
    - set_state(): Import and initialize from physical variables
    - Format: Dict[str, Dict[str, Any]] with 'value' and 'unit' keys
    - Use: Transferring state between different models, debugging

**Time Rollback** (for event detection via bisection):
    - snapshot_state(): Capture complete internal solver state (opaque)
    - restore_state(): Restore exact solver state at previous time
    - Format: Opaque (component-specific, may include solver internals)
    - Use: Reverting to previous time during hybrid simulation

**Key Rule**: These are separate concerns. Snapshots cannot be adapted across
models and should only be used for rollback within the same component instance.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

import numpy as np

from .events import Event, EventIndicator, InternalEventInfo, _sign
from .history import ComponentHistory
from .port import PortSpec, PortState, PortType


# -------------------------------------------------------------------
# CoSimComponent - Base Class for Co-Simulation Components
# -------------------------------------------------------------------
class CoSimComponent(ABC):
    """
    Unified co-simulation component interface with common functionality.
    """

    name: str
    label: str
    group: str | None = None
    t: float = 0.0  # Current simulation time

    # -------------------------------------------------------------------
    # Construction and Identity
    # -------------------------------------------------------------------
    def __init__(self, name: str, label: str | None = None, group: str | None = None):
        self.name = name
        self.label = label if label is not None else name
        self.group = group

        # Port specifications (immutable) and states (mutable)
        self.input_specs: dict[str, PortSpec] = {}
        self.output_specs: dict[str, PortSpec] = {}
        self.inputs: dict[str, PortState] = {}
        self.outputs: dict[str, PortState] = {}

        # History tracking
        self.history = ComponentHistory(component_name=name)

        # Parameter container (populated by subclasses)
        self.parameters: dict[str, Any] = {}

        # Model structure and direct feedthrough info
        self.direct_feedthrough: dict[str, set[str]] = {}
        self.model_structure: dict[str, dict[str, list[str]]] = {
            "outputs": {},
            "derivatives": {},
            "initialUnknowns": {},
        }

        # Hybrid capabilities
        self.event_indicators: dict[str, EventIndicator] = {}
        self.internal_event_hints: list[InternalEventInfo] = []  # For precise event localization
        self.event_subscriptions: list[Event] = []
        self.event_annotations: dict[str, dict[str, Any]] = {}
        self.event_commutativity: dict[tuple[str, str], bool] = {}

    def __repr__(self):
        repr = f"<CoSimComponent name='{self.name}'>"
        return repr

    def __str__(self):
        return self.__repr__()

    # -------------------------------------------------------------------
    # Configuration - setting parameters
    # -------------------------------------------------------------------
    def set_parameters(self, **parameters: Any) -> None:
        """
        Set one or more component parameters before initialize().

        Args:
            **parameters: Keyword arguments mapping parameter names to values

        Raises:
            KeyError: If any parameter name is unknown
            ValueError: If parameter validation fails (override to add)

        Example:
            >>> comp.set_parameters(mass=1.5, length=0.4)
            >>> comp.set_parameters(gain=2.0)  # Single parameter works too

        Note:
            Must be called before initialize(). For validation logic,
            override this method in subclasses.
        """
        for name, value in parameters.items():
            if name not in self.parameters:
                raise KeyError(
                    f"Unknown parameter '{name}' for component '{self.name}'. "
                    f"Available parameters: {list(self.parameters.keys())}"
                )
            self._validate_parameter(name, value)  # Hook for subclasses
            self.parameters[name] = value

    def get_parameters(self, *names: str) -> dict[str, Any]:
        """
        Get one or more parameter values.

        Args:
            *names: Parameter names to retrieve. If empty, returns all parameters.

        Returns:
            Dict mapping parameter names to their values

        Raises:
            KeyError: If any parameter name is unknown

        Example:
            >>> comp.get_parameters('mass', 'length')
            {'mass': 1.5, 'length': 0.4}
            >>> comp.get_parameters()  # All parameters
            {'mass': 1.5, 'length': 0.4, 'gain': 2.0}
        """
        if not names:
            return self.parameters.copy()

        result = {}
        for name in names:
            if name not in self.parameters:
                raise KeyError(
                    f"Unknown parameter '{name}' for component '{self.name}'. "
                    f"Available parameters: {list(self.parameters.keys())}"
                )
            result[name] = self.parameters[name]
        return result

    def _validate_parameter(self, name: str, value: Any) -> None:
        """
        Hook for subclass parameter validation.

        Override to add custom validation logic. Called before setting parameter.

        Args:
            name: Parameter name
            value: Proposed value

        Raises:
            ValueError: If validation fails

        Example:
            >>> def _validate_parameter(self, name, value):
            ...     if name == 'mass' and value <= 0:
            ...         raise ValueError("Mass must be positive")
            ...     super()._validate_parameter(name, value)
        """
        pass  # Base implementation does nothing

    # -------------------------------------------------------------------
    # Port specification and initialization
    # -------------------------------------------------------------------
    def _initialize_ports_from_specs(self) -> None:
        """
        Initialize input and output ports from their specifications.

        This method creates PortState instances for all input and output ports defined
        in the component's specifications. It also registers output ports with the
        component's history for tracking purposes.

        The method iterates through:
        - input_specs: Creates PortState objects in the inputs dictionary
        - output_specs: Creates PortState objects in the outputs dictionary and
            registers them with the history tracker including their units

        Notes
        -----
        This is typically called during component initialization to set up the port
        infrastructure before the component begins operation.
        """
        for spec in self.input_specs.values():
            self.inputs[spec.name] = PortState(spec)
        for spec in self.output_specs.values():
            self.outputs[spec.name] = PortState(spec)
            self.history.add_port(spec.name, spec.unit)

    # -------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------
    def initialize(self, t0: float) -> None:
        """
        Initialize the component at the given time.

        This method sets up the component's initial state by performing the following steps:
        1. Sets the internal time to the initial time
        2. Automatically initializes ports from specifications if they exist
        3. Initializes the component's internal state
        4. Updates the output states based on the initial conditions
        5. Records the initial output values

        Args:
            t0 (float): The initial time at which to initialize the component.
        """
        self.t = t0

        # Automatic port initialization
        if self.input_specs or self.output_specs:
            self._initialize_ports_from_specs()

        # Hook for subclass-specific initialization
        self._initialize_component(t0)

        # Standard output state and recording after initialization
        self._update_output_states(t0)
        self._record_outputs(t0)

    @abstractmethod
    def _initialize_component(self, t0: float) -> None:
        """Subclass hook: perform actual initialization steps."""
        ...

    # -------------------------------------------------------------------
    # I/O - Inputs and Outputs
    # -------------------------------------------------------------------
    def set_inputs(self, signals: dict[str, Any], t: float | None = None) -> None:
        """
        Default input setter. Override for type conversions or special handling.
        """
        for k, v in signals.items():
            if k not in self.inputs:
                raise KeyError(f"Input port '{k}' not found in component '{self.name}'.")
            self.inputs[k].set(v, t=t)

    def evaluate_outputs(self, inputs: dict[str, Any], t: float | None = None) -> dict[str, Any]:
        """
        Evaluate and return the component's outputs for the given inputs at time t.

        Components with direct feedthrough must override this method to perform an update
        of outputs based on the provided inputs (e.g, zero-step evaluation with dt=0).

        Args:
            inputs: Dictionary mapping input port names to their values.
                If empty, no inputs will be set before evaluation.
            t: Time at which to evaluate outputs. This parameter
                is currently not accessed in the default implementation but may be used
                by subclasses for time-dependent behavior.
        """

        # Default implementation: just set inputs and return outputs
        if inputs:
            self.set_inputs(inputs, t=None)
        # For non-FMUs
        return {name: port.get() for name, port in self.outputs.items()}

    def get_outputs(self) -> dict[str, Any]:
        """Return current outputs as {name: value} dict."""
        return {k: v.get() for k, v in self.outputs.items() if v.get() is not None}

    # -------------------------------------------------------------------
    # Stepping
    # -------------------------------------------------------------------
    def do_step(self, t: float, dt: float) -> None:
        """
        Execute a single simulation step.

        This method advances the simulation by one time step, updating internal states,
        output states, and recording outputs at the new time point.

        Args:
            t (float): The current simulation time.
            dt (float): The time step size to advance the simulation.

        Returns:
            None

        Note:
            This method performs the following operations in order:
            1. Executes internal step calculations via _do_step_internal()
            2. Updates the current time to t + dt
            3. Updates output states at the new time
            4. Records outputs at the new time
        """
        self._do_step_internal(t, dt)
        self.t = t + dt

        self._update_output_states(self.t)
        self._record_outputs(self.t)

    @abstractmethod
    def _do_step_internal(self, t: float, dt: float) -> None:
        """Subclass hook: perform actual time step computation."""
        ...

    @abstractmethod
    def _update_output_states(
        self, t: float | None = None, event_names: list[str] | None = []
    ) -> None:
        """
        Subclass hook: read internal state and update self.outputs[...].set(value, t).
        Called automatically after initialize() and do_step().
        """
        ...

    # -------------------------------------------------------------------
    # State Management
    # -------------------------------------------------------------------
    @abstractmethod
    def set_state(self, state: dict[str, Any], t: float) -> None:
        """
        Set physical state from human-readable format (for mode switching).

        This method initializes the component from physical variables exported
        by get_state(). It may perform unit conversions and state adaptation
        but should not preserve solver-specific internal state.

        Args:
            state: Dict mapping variable names to {'value': ..., 'unit': ...}
            t: Time at which to set the state

        Example:
            >>> state = {'q': {'value': 0.5, 'unit': 'rad'},
            ...          'omega': {'value': 1.0, 'unit': 'rad/s'}}
            >>> component.set_state(state, t=0.0)

        Note:
            For mode switching in MultiComponent, this state may be adapted
            from another model's format using _adapt_state().
        """
        ...

    @abstractmethod
    def get_state(self) -> dict[str, dict[str, Any]]:
        """
        Export current physical state (for inspection and mode switching).

        Returns a human-readable representation of the component's physical
        state that can be transferred to other models or saved for debugging.
        Does NOT include solver-specific internal state.

        Returns:
            Dict mapping variable names to dicts with 'value' and 'unit' keys

        Example:
            >>> state = component.get_state()
            >>> print(state)
            {'q': {'value': 0.5, 'unit': 'rad'},
            'omega': {'value': 1.0, 'unit': 'rad/s'}}

        See Also:
            snapshot_state: For complete internal state capture (rollback)
        """
        ...

    def snapshot_state(self) -> Any:
        """
        Capture complete internal state for time rollback (opaque format).

        Creates an opaque snapshot that preserves ALL solver state needed
        to restore the component to its exact condition at the current time.
        This includes internal solver artifacts not exposed by get_state().

        Returns:
            Opaque snapshot object (format is component-specific)

        Raises:
            NotImplementedError: If component doesn't support rollback

        Example:
            >>> snapshot = component.snapshot_state()
            >>> component.do_step(t, dt)
            >>> component.restore_state(snapshot, t)  # Exact rollback

        Warning:
            - Snapshot format is internal and may change
            - Cannot be used across different component instances or modes
            - Only for rollback within the same component

        See Also:
            restore_state: Restore from snapshot
            supports_rollback: Check if rollback is supported
            get_state: For human-readable state export
        """
        raise NotImplementedError(f"Component '{self.name}' does not support rollback. ")

    def restore_state(self, snapshot: Any, t: float) -> None:
        """
        Restore component to exact state from snapshot (pure rollback).

        Reverses time by restoring the component to the state captured by
        snapshot_state(). After restoration, subsequent do_step() calls
        behave as if the component never advanced past time t.

        Args:
            snapshot: Opaque snapshot from snapshot_state()
            t: Time at which the snapshot was taken

        Raises:
            NotImplementedError: If component doesn't support rollback
            ValueError: If snapshot is from incompatible state/mode

        Example:
            >>> snapshot = component.snapshot_state()
            >>> original_time = component.t
            >>> component.do_step(t, dt)
            >>> component.restore_state(snapshot, original_time)
            >>> # Component is now back at original_time

        Warning:
            - Snapshot must be from the same component instance
            - For MultiComponent, mode must match snapshot['active_mode']
            - Not for transferring state between models (use set_state)

        See Also:
            snapshot_state: Create snapshot
            get_state/set_state: For physical state transfer
        """
        raise NotImplementedError("restore_state() not implemented for this component.")

    @property
    def supports_rollback(self) -> bool:
        """
        True if component supports snapshot/restore for time rollback.

        Components that support rollback must override both snapshot_state()
        and restore_state(). This is required for event detection in hybrid
        co-simulation, which uses bisection search to locate event times.

        Returns:
            True if both snapshot_state and restore_state are implemented

        Note:
            Automatically detects overrides from base class.
        """
        # Check if methods are overridden from base class
        return (
            type(self).snapshot_state is not CoSimComponent.snapshot_state
            and type(self).restore_state is not CoSimComponent.restore_state
        )

    # -------------------------------------------------------------------
    # History Recording and Retrieval
    # -------------------------------------------------------------------
    def _record_outputs(self, t: float) -> None:
        """Record current output values to history."""
        for name, port in self.outputs.items():
            if port.value is not None:
                self.history.append(name, t, port.value)

    def get_history(
        self, port_names: list[str] | None = None, units: dict[str, str] | None = None
    ) -> dict[str, dict[str, Any]]:
        """
        Get history of output ports.

        Args:
            port_names: List of specific ports to retrieve. If None, returns all.
            units: Dict mapping port names to desired units for conversion.

        Returns:
            Dict mapping port names to history dicts with 'time', 'values', 'unit'.
        """
        return self.history.to_dict(port_names=port_names, units=units)

    def get_history_arrays(
        self, port_names: list[str] | None = None, units: dict[str, str] | None = None
    ) -> tuple[np.ndarray, dict[str, np.ndarray]]:
        """
        Get history as numpy arrays.

        Args:
            port_names: List of specific ports to retrieve. If None, returns all.
            units: Dict mapping port names to desired units.

        Returns:
            Tuple of (time_array, {port_name: values_array})
        """
        return self.history.to_arrays(port_names=port_names, units=units)

    # -------------------------------------------------------------------
    # Hybrid Capabilities - Event Indicators and Handling
    # -------------------------------------------------------------------
    def add_event_indicator(
        self, name: str, func: Callable[[CoSimComponent], float], direction: int = 0
    ) -> None:
        """
        Register an event indicator function for zero-crossing detection.

        Args:
            name: Name of the event indicator
            func: Function that takes the component and returns a float indicator value
            direction: Direction of zero-crossing to detect (-1: falling, 0: both, +1: rising)
        Raises:
            RuntimeError: if component does not support rollback
            KeyError: if an indicator with the same name already exists
            ValueError: if direction is not -1, 0, or +1
        """
        if not self.supports_rollback:
            raise RuntimeError(
                f"Component '{self.name}' must support rollback to register event indicators."
            )
        if name in self.event_indicators:
            raise KeyError(f"Event indicator '{name}' already exists in component '{self.name}'.")
        if direction not in (-1, 0, 1):
            raise ValueError("Direction must be -1 (falling), 0 (both), or +1 (rising).")
        self.event_indicators[name] = EventIndicator(name, func, direction)

        # Add event port to output specs, outputs, and history
        event_port_spec = PortSpec(name=name, type=PortType.EVENT, direction="out")
        self.output_specs.update({event_port_spec.name: event_port_spec})
        self.outputs[event_port_spec.name] = PortState(event_port_spec)
        self.outputs[event_port_spec.name].set(False, t=self.t)
        self.history.add_port(event_port_spec.name)
        self._update_output_states(self.t)
        self._record_outputs(self.t)

    @property
    def has_state_events(self) -> bool:
        """True if the component currently has one or more state event indicators."""
        return bool(self.event_indicators)

    def evaluate_event_indicators(self) -> dict[str, float]:
        """
        Evaluate all event indicators and return their current values.
        """
        indicators = {}
        for name, indicator in self.event_indicators.items():
            indicators[name] = indicator.evaluate(self)
        return indicators

    def detect_event_crossings(
        self, previous: dict[str, float], current: dict[str, float], sign_tolerance: float = 1e-10
    ) -> list[str]:
        """
        Detect zero-crossings between previous and current indicator values.

        Args:
            sign_tolerance: Values smaller than this are considered zero for sign detection
        """
        events = []
        for name, indicator in self.event_indicators.items():
            prev_sign = _sign(previous[name], sign_tolerance)
            curr_sign = _sign(current[name], sign_tolerance)

            # Check for crossing according to indicator direction
            if indicator.direction == 0:  # Any direction
                crossed = prev_sign != curr_sign
            elif indicator.direction == 1:  # Rising only
                crossed = prev_sign < 0 and curr_sign >= 0
            elif indicator.direction == -1:  # Falling only
                crossed = prev_sign > 0 and curr_sign <= 0

            if crossed:
                events.append(name)
        return events

    def report_internal_event(
        self,
        event_name: str,
        t_before: float,
        t_after: float,
        indicator_before: float | None = None,
        indicator_after: float | None = None,
    ) -> None:
        """
        Report an event detected during internal micro-stepping.

        Call this from _do_step_internal when an event is detected internally.
        The master algorithm will use this hint to narrow the bisection interval.

        Args:
            event_name: Name of the event (must match an event indicator)
            t_before: Last micro-step time before the event
            t_after: First micro-step time after the event
            indicator_before: Indicator value at t_before (optional)
            indicator_after: Indicator value at t_after (optional)
        """
        hint = InternalEventInfo(
            event_name=event_name,
            t_before=t_before,
            t_after=t_after,
            indicator_before=indicator_before,
            indicator_after=indicator_after,
        )
        self.internal_event_hints.append(hint)

    def get_internal_event_hints(self) -> list[InternalEventInfo]:
        """
        Retrieve and clear internal event hints.

        Returns:
            List of InternalEventInfo objects with timing hints for event localization.
        """
        hints = self.internal_event_hints.copy()
        self.internal_event_hints.clear()
        return hints

    def subscribe_event(self, event: Event) -> None:
        """Register an explicit event subscription (time must be omitted)."""
        if event.time is not None:
            raise ValueError("Subscription events must not include a time.")
        for existing in self.event_subscriptions:
            if existing.name == event.name and existing.source == event.source:
                raise KeyError(
                    f"Event subscription '{event.source}:{event.name}' already exists in component '{self.name}'."
                )
        self.event_subscriptions.append(event)

    @property
    def has_event_subscriptions(self) -> bool:
        return bool(self.event_subscriptions)

    def handle_event(self, event_names: list[str], t: float) -> None:
        """
        Handle events by calling subclass hook.
        """
        self._handle_events_internal(event_names, t)
        self._update_output_states(t, event_names)
        self._record_outputs(t)

    def _handle_events_internal(self, event_names: list[str], t: float) -> None:
        """Subclass hook: handle events (state updates, re-initialization, etc.)."""
        pass

    # -------------------------------------------------------------------
    # Cleanup - reset and free
    # -------------------------------------------------------------------
    def reset(self) -> None:
        """Reset to clean state before re-initialization."""
        self.t = 0.0
        self.history.clear()

    def free(self) -> None:
        """Optional: release resources (FMU instances, OpenSim memory, etc.)."""
        pass

    # -------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------
    @property
    def reactive_inputs(self) -> set[str]:
        """Get the set of input names that have direct feedthrough to any output.

        Returns:
            Set[str]: A set of input names that affect at least one output algebraically
                (i.e., have direct feedthrough). An input is considered reactive if it
                appears in the direct_feedthrough mapping for any output.

        Note:
            This method aggregates all inputs across all outputs in the direct_feedthrough
            dictionary, returning the union of all input sets.
        """
        reactive_inputs = set(inp for outs in self.direct_feedthrough.values() for inp in outs)
        return reactive_inputs

    @property
    def has_direct_feedthrough(self) -> bool:
        """Check if the component has any direct feedthrough from inputs to outputs.

        Direct feedthrough occurs when an output depends directly on an input in the
        same time step, without any intermediate state dynamics.

        Returns:
            bool: True if at least one input-output pair has direct feedthrough.
        """
        return any(self.direct_feedthrough.values())
