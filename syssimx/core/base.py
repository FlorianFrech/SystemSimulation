"""Co-simulation component base classes and interfaces.

This module defines the abstract base class ``CoSimComponent`` that all
co-simulation components must inherit from. It provides a unified interface
for initialization, stepping, I/O handling, state management, and event
detection in heterogeneous co-simulation scenarios.

Architecture Overview:
    The component lifecycle follows these phases:

    1. **Construction**: Create component with name and optional label/group
    2. **Configuration**: Set parameters via ``set_parameters()``
    3. **Initialization**: Call ``initialize(t0)`` to set up ports and state
    4. **Simulation Loop**: Repeated calls to ``set_inputs()``, ``do_step()``,
       ``get_outputs()``
    5. **Cleanup**: Call ``reset()`` for re-initialization or ``free()`` for
       resource release

State Management API:
    Components provide two distinct state management interfaces:

    Physical State Transfer (for mode switching and inspection):
        - ``get_state()``: Export human-readable physical variables
        - ``set_state()``: Import and initialize from physical variables
        - Format: ``Dict[str, Dict[str, Any]]`` with 'value' and 'unit' keys
        - Use: Transferring state between different models, debugging

    Time Rollback (for event detection via bisection):
        - ``snapshot_state()``: Capture complete internal solver state (opaque)
        - ``restore_state()``: Restore exact solver state at previous time
        - Format: Opaque (component-specific, may include solver internals)
        - Use: Reverting to previous time during hybrid simulation

    Key Rule:
        These are separate concerns. Snapshots cannot be adapted across
        models and should only be used for rollback within the same
        component instance.

Example:
    Basic component usage pattern::

        from syssimx.core.base import CoSimComponent

        # Create and configure
        comp = MyComponent("sensor", label="Temperature Sensor")
        comp.set_parameters(gain=2.0, offset=0.5)

        # Initialize at t=0
        comp.initialize(t0=0.0)

        # Simulation loop
        for t in np.arange(0, 10, 0.01):
            comp.set_inputs({'u': input_signal[t]})
            comp.do_step(t, dt=0.01)
            outputs = comp.get_outputs()

        # Retrieve history
        time, values = comp.get_history_arrays()

See Also:
    - :class:`syssimx.components.FMUComponent`: FMI 2.0 wrapper
    - :class:`syssimx.components.FEMComponent`: NGSolve transient structural FEM wrapper
    - :class:`syssimx.components.OpenSimComponent`: Biomechanics wrapper
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

import numpy as np

from ..utilities.units import Quantity
from .events import Event, EventIndicator, InternalEventInfo, _sign
from .history import ComponentHistory
from .port import PortSpec, PortState, PortType


# -------------------------------------------------------------------
# CoSimComponent - Base Class for Co-Simulation Components
# -------------------------------------------------------------------
class CoSimComponent(ABC):
    """Abstract base class for all co-simulation components.

    This class defines the unified interface that all simulation components
    must implement to participate in a co-simulation. It handles port
    management, history recording, parameter configuration, and provides
    hooks for hybrid event detection.

    Subclasses must implement the following abstract methods:
        - ``_initialize_component(t0)``: Component-specific initialization
        - ``_do_step_internal(t, dt)``: Time step computation
        - ``_update_output_states(t, event_names)``: Update output port values
        - ``get_state()``: Export physical state
        - ``set_state(state, t)``: Import physical state

    Attributes:
        name (str): Unique identifier for the component within a system.
        label (str): Human-readable display name (defaults to name).
        group (str | None): Optional grouping category for organization.
        t (float): Current simulation time in seconds.
        input_specs (dict[str, PortSpec]): Input port specifications (immutable).
        output_specs (dict[str, PortSpec]): Output port specifications (immutable).
        inputs (dict[str, PortState]): Current input port states (mutable).
        outputs (dict[str, PortState]): Current output port states (mutable).
        history (ComponentHistory): Time-series recorder for output values.
        parameters (dict[str, Any]): Configurable component parameters.
        direct_feedthrough (dict[str, set[str]]): Maps outputs to inputs with
            algebraic dependency (no state dynamics between them).
        model_structure (dict[str, dict[str, list[str]]]): FMI-style dependency
            structure for outputs, derivatives, and initial unknowns.
        event_indicators (dict[str, EventIndicator]): Registered zero-crossing
            functions for state event detection.
        internal_event_hints (list[InternalEventInfo]): Timing hints from
            micro-stepping components to improve event localization.
        event_subscriptions (list[Event]): External events this component
            subscribes to.
        event_annotations (dict[str, dict[str, Any]]): Metadata for events.
        event_commutativity (dict[tuple[str, str], bool]): Whether event pairs
            can be handled in any order.

    Example:
        Creating a custom component::

            class Integrator(CoSimComponent):
                def __init__(self, name: str):
                    super().__init__(name)
                    self.input_specs = {'u': PortSpec('u', PortType.REAL, 'in')}
                    self.output_specs = {'y': PortSpec('y', PortType.REAL, 'out')}
                    self.parameters = {'gain': 1.0}
                    self._state = 0.0

                def _initialize_component(self, t0: float) -> None:
                    self._state = 0.0

                def _do_step_internal(self, t: float, dt: float) -> None:
                    self._state += self.parameters['gain'] * self.inputs['u'].get() * dt

                def _update_output_states(self, t: float, event_names=None) -> None:
                    self.outputs['y'].set(self._state, t=t)

                def get_state(self) -> dict:
                    return {'y': {'value': self._state, 'unit': '1'}}

                def set_state(self, state: dict, t: float) -> None:
                    self._state = state['y']['value']
                    self.t = t

    See Also:
        :class:`PortSpec`: Port specification dataclass
        :class:`PortState`: Mutable port state container
        :class:`ComponentHistory`: History recording utility
    """

    name: str
    label: str
    group: str | None = None
    t: float = 0.0  # Current simulation time

    # -------------------------------------------------------------------
    # Construction and Identity
    # -------------------------------------------------------------------
    def __init__(self, name: str, label: str | None = None, group: str | None = None):
        """Initialize a new co-simulation component.

        Args:
            name: Unique identifier for this component. Must be unique within
                the containing System. Used for connection definitions and
                graph construction.
            label: Human-readable display name for visualization and logging.
                Defaults to ``name`` if not provided.
            group: Optional category for grouping related components (e.g.,
                'sensors', 'actuators', 'controllers'). Used for filtering
                and organization in large systems.

        Example:
            >>> comp = MyComponent("pid_1", label="PID Controller", group="controllers")
            >>> comp.name
            'pid_1'
            >>> comp.label
            'PID Controller'
        """
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
        # When False, ``do_step`` skips writing outputs to history. The hybrid
        # master algorithm disables this during trial/probe steps (event
        # localization) so that rolled-back advances do not pollute history.
        self._record_history: bool = True

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
        self._events_being_handled: dict[str, Event] = {}

        # Initialization tracking
        self._is_initialized: bool = False

    def __repr__(self):
        repr = f"<CoSimComponent name='{self.name}'>"
        return repr

    def __str__(self):
        return self.__repr__()

    # -------------------------------------------------------------------
    # Configuration - setting parameters
    # -------------------------------------------------------------------
    def set_parameters(self, **parameters: Any) -> None:
        """Set one or more component parameters before initialization.

        Parameters control component behavior and must be set before
        calling ``initialize()``. Available parameters are defined in
        the component's ``__init__`` method.

        Args:
            **parameters: Keyword arguments mapping parameter names to
                their values. All names must exist in ``self.parameters``.

        Raises:
            KeyError: If any parameter name is not recognized.
            ValueError: If parameter validation fails (see
                ``_validate_parameter()`` hook).

        Example:
            >>> comp.set_parameters(mass=1.5, length=0.4)
            >>> comp.set_parameters(gain=2.0)  # Single parameter
            >>> comp.get_parameters()
            {'mass': 1.5, 'length': 0.4, 'gain': 2.0}

        Note:
            Override ``_validate_parameter()`` in subclasses to add
            custom validation logic (e.g., range checking).

        See Also:
            :meth:`get_parameters`: Retrieve parameter values
            :meth:`_validate_parameter`: Validation hook
        """
        for name, value in parameters.items():
            if name not in self.parameters:
                raise KeyError(
                    f"Unknown parameter '{name}' for component '{self.name}'. "
                    f"Available parameters: {list(self.parameters.keys())}"
                )
            value = self._validate_parameter(name, value)
            self.parameters[name] = value

    def get_parameters(self, *names: str) -> dict[str, Any]:
        """Retrieve one or more parameter values.

        Args:
            *names: Parameter names to retrieve. If no names are provided,
                returns all parameters.

        Returns:
            Dictionary mapping parameter names to their current values.
            Returns a copy to prevent external modification.

        Raises:
            KeyError: If any requested parameter name is not recognized.

        Example:
            >>> comp.get_parameters('mass', 'length')
            {'mass': 1.5, 'length': 0.4}
            >>> comp.get_parameters()  # All parameters
            {'mass': 1.5, 'length': 0.4, 'gain': 2.0}

        See Also:
            :meth:`set_parameters`: Set parameter values
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

    def _validate_parameter(self, name: str, value: Any) -> Any:
        """Subclass hook for custom parameter validation.

        Override this method to add validation logic such as range
        checking, type verification, or cross-parameter constraints.
        Called by ``set_parameters()`` before storing the value.

        Args:
            name: Name of the parameter being set.
            value: Proposed value for the parameter.

        Raises:
            ValueError: If validation fails. Include a descriptive
                message explaining the constraint.

        Example:
            >>> def _validate_parameter(self, name: str, value: Any) -> Any:
            ...     if name == 'mass' and value <= 0:
            ...         raise ValueError("Mass must be positive")
            ...     if name == 'damping' and not (0 <= value <= 1):
            ...         raise ValueError("Damping must be in [0, 1]")
            ...     return super()._validate_parameter(name, value)

        Note:
            Always call ``super()._validate_parameter(name, value)`` at
            the end to allow parent class validation.
        """
        existing_param = self.parameters.get(name)
        if existing_param is None:
            raise KeyError(f"Parameter '{name}' not found for validation.")

        # 1) Check if value is a compatible Quantity
        if isinstance(value, Quantity):
            if not value.is_compatible_with(existing_param.units):
                raise ValueError(
                    f"Parameter '{name}' expects units compatible with "
                    f"'{existing_param.units}', got '{value.units}'."
                )
            return value.to(existing_param.units)

        # 2) Convert raw numeric values to Quantity with correct units
        elif isinstance(value, (int, float)) and hasattr(existing_param, "units"):
            return Quantity(value, existing_param.units)

        # 3) Otherwise, accept the value as-is (e.g., strings, bools)
        else:
            return value

    # -------------------------------------------------------------------
    # Port specification and initialization
    # -------------------------------------------------------------------
    def _initialize_ports_from_specs(self) -> None:
        """Create port state objects from port specifications.

        Iterates through ``input_specs`` and ``output_specs`` to create
        corresponding ``PortState`` instances. Output ports are also
        registered with the component's history tracker.

        Called automatically during ``initialize()`` if port specs exist.

        Note:
            Port specifications (``PortSpec``) define the port interface
            (name, type, direction, unit). Port states (``PortState``)
            hold the actual runtime values.

        See Also:
            :class:`PortSpec`: Port specification dataclass
            :class:`PortState`: Mutable port value container
        """
        for spec in self.input_specs.values():
            if spec.name not in self.inputs:
                self.inputs[spec.name] = PortState(spec)
        for spec in self.output_specs.values():
            if spec.name not in self.outputs:
                self.outputs[spec.name] = PortState(spec)
            unit = str(spec.unit) if spec.unit is not None else None
            self.history.add_port(spec.name, unit)

    # -------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------
    def initialize(self, t0: float) -> None:
        """Initialize the component at the specified start time.

        Prepares the component for simulation by setting up ports, event
        indicators, and internal state. This method must be called once
        before the simulation loop begins.

        The initialization sequence:

        1. Sets internal time to ``t0``
        2. Creates ``PortState`` objects from port specifications
        3. Creates event output ports for registered indicators
        4. Calls ``_initialize_component(t0)`` subclass hook
        5. Updates output states and records initial values

        If already initialized, returns immediately (idempotent).

        Args:
            t0: Initial simulation time in seconds.

        Example:
            >>> comp.set_parameters(mass=1.5)
            >>> comp.initialize(t0=0.0)
            >>> comp.t
            0.0
            >>> comp.get_outputs()
            {'y': 0.0}

        Note:
            Call ``reset()`` before re-initializing with different
            parameters or initial time.

        See Also:
            :meth:`reset`: Clear state for re-initialization
            :meth:`_initialize_component`: Subclass initialization hook
        """
        if self._is_initialized:
            return  # Prevent double initialization

        self.t = t0

        # Automatic port initialization
        if self.input_specs or self.output_specs:
            self._initialize_ports_from_specs()

        # Create event output ports for registered event indicators
        self._initialize_event_ports()

        # Hook for subclass-specific initialization
        self._initialize_component(t0)

        # Detect direct feedthrough based on input-output dependencies
        self._detect_direct_feedthrough()

        # Standard output state and recording after initialization
        self._update_output_states(t0)
        self._record_outputs(t0)

        self._is_initialized = True

    def _initialize_event_ports(self) -> None:
        """Create output ports for all registered event indicators.

        Automatically creates ``PortSpec`` and ``PortState`` objects for
        each event indicator registered before initialization. Event ports
        are boolean outputs that signal when an event has occurred.

        Note:
            Called automatically during ``initialize()``. Event indicators
            registered after initialization create their ports immediately
            in ``add_event_indicator()``.
        """
        for name in self.event_indicators:
            if name not in self.output_specs:
                event_port_spec = PortSpec(name=name, type=PortType.EVENT, direction="out")
                self.output_specs[name] = event_port_spec
                self.outputs[name] = PortState(event_port_spec)
                self.outputs[name].set(False, t=self.t)
                self.history.add_port(name)

    @abstractmethod
    def _initialize_component(self, t0: float) -> None:
        """Subclass hook for component-specific initialization.

        Override this method to perform initialization tasks such as:

        - Loading model files or external resources
        - Setting initial state values
        - Configuring internal solvers
        - Validating parameters

        Called automatically by ``initialize()`` after ports are created
        but before outputs are updated and recorded.

        Args:
            t0: Initial simulation time in seconds.

        Example:
            >>> def _initialize_component(self, t0: float) -> None:
            ...     self._state = np.zeros(self.n_states)
            ...     self._solver = RK45(self._ode_func, t0, self._state)

        Note:
            Port specifications (``input_specs``, ``output_specs``) should
            be defined in ``__init__``, not here. This method is for
            runtime initialization that depends on parameters.
        """
        ...

    # -------------------------------------------------------------------
    # I/O - Inputs and Outputs
    # -------------------------------------------------------------------
    def set_inputs(self, signals: dict[str, Any], t: float | None = None) -> None:
        """Set input port values from a dictionary of signals.

        This method updates the component's input ports with new values.
        Override in subclasses for type conversions, unit handling, or
        special input processing.

        Args:
            signals: Dictionary mapping input port names to their values.
                Keys must match registered input port names.
            t: Optional timestamp for the input values. Used for
                interpolation and history tracking.

        Raises:
            KeyError: If any key in ``signals`` doesn't match a registered
                input port name.

        Example:
            >>> comp.set_inputs({'u': 1.5, 'v': 2.0}, t=0.5)
            >>> comp.set_inputs({'u': 0.0})  # Timestamp optional

        Note:
            Called automatically by the master algorithm before each step.
            The System class handles unit conversions via Connection objects
            before calling this method.
        """
        for k, v in signals.items():
            if k not in self.inputs:
                raise KeyError(f"Input port '{k}' not found in component '{self.name}'.")
            self.inputs[k].set(v, t=t)

    def evaluate_outputs(self, inputs: dict[str, Any], t: float | None = None) -> dict[str, Any]:
        """Evaluate outputs for given inputs without advancing time.

        This method computes outputs based on the provided inputs at the
        current time, without performing a time step. Essential for solving
        algebraic loops where outputs depend algebraically on inputs.

        Components with direct feedthrough must override this method to
        perform a zero-step evaluation (dt=0) that updates outputs based
        on the current inputs.

        Args:
            inputs: Dictionary mapping input port names to their values.
                If empty, no inputs will be set before evaluation.
            t: Time at which to evaluate outputs. May be used by subclasses
                for time-dependent algebraic relationships.

        Returns:
            Dictionary mapping output port names to their computed values.

        Example:
            >>> # For algebraic loop solving (IJCSA algorithm)
            >>> outputs = comp.evaluate_outputs({'u': trial_value}, t=0.5)
            >>> y = outputs['y']

        Note:
            The default implementation simply sets inputs and returns current
            outputs. Override for components with true algebraic feedthrough
            where outputs must be recomputed based on new inputs.

        See Also:
            :attr:`direct_feedthrough`: Declares input-output dependencies
            :attr:`has_direct_feedthrough`: Check for any feedthrough
        """

        # Default implementation: just set inputs and return outputs
        if inputs:
            self.set_inputs(inputs, t=None)
        # For non-FMUs
        return {name: port.get() for name, port in self.outputs.items()}

    def get_outputs(self) -> dict[str, Any]:
        """Return current output values as a dictionary.

        Retrieves the current value of all output ports that have been set.
        Ports with ``None`` values are excluded from the result.

        Returns:
            Dictionary mapping output port names to their current values.
            Only includes ports with non-None values.

        Example:
            >>> comp.do_step(t=0.0, dt=0.01)
            >>> outputs = comp.get_outputs()
            >>> print(outputs)
            {'y': 1.5, 'dy': 0.1}

        Note:
            For type-safe access with units, use ``outputs[name].get()``
            directly on the PortState object.
        """
        return {k: v.get() for k, v in self.outputs.items() if v.get() is not None}

    # -------------------------------------------------------------------
    # Stepping
    # -------------------------------------------------------------------
    def do_step(self, t: float, dt: float) -> None:
        """Execute a single simulation time step.

        Advances the component's simulation from time ``t`` to ``t + dt``.
        This is the main simulation interface called by the master
        algorithm during the simulation loop.

        The method performs these operations in order:

        1. Calls ``_do_step_internal(t, dt)`` for actual computation
        2. Updates ``self.t`` to ``t + dt``
        3. Calls ``_update_output_states()`` to refresh outputs
        4. Calls ``_record_outputs()`` to save to history (unless
           ``_record_history`` is ``False``, e.g. during trial steps)

        Args:
            t: Current simulation time at the start of the step (seconds).
                Should match ``self.t`` from the previous step.
            dt: Time step size to advance (seconds). Must be positive.

        Example:
            >>> comp.initialize(t0=0.0)
            >>> for i in range(1000):
            ...     t = i * 0.001
            ...     comp.set_inputs({'u': signal[i]}, t=t)
            ...     comp.do_step(t, dt=0.001)

        Note:
            Inputs should be set via ``set_inputs()`` before calling
            ``do_step()``. The master algorithm handles this automatically.

        See Also:
            :meth:`_do_step_internal`: Override for custom stepping logic
        """
        self._do_step_internal(t, dt)
        self.t = t + dt

        self._update_output_states(self.t)
        if self._record_history:
            self._record_outputs(self.t)

    @abstractmethod
    def _do_step_internal(self, t: float, dt: float) -> None:
        """Subclass hook for time step computation.

        Override this method to implement the component's simulation logic.
        This is where state integration, solver calls, and internal
        computations happen.

        Args:
            t: Current simulation time at the start of the step (seconds).
            dt: Time step size to advance (seconds).

        Example:
            Simple Euler integration::

                def _do_step_internal(self, t: float, dt: float) -> None:
                    u = self.inputs['u'].get()
                    self._state += self._derivative(self._state, u) * dt

        Note:
            - Do NOT update ``self.t`` here; ``do_step()`` handles that
            - Do NOT call ``_update_output_states()``; done by ``do_step()``
            - For event detection, call ``report_internal_event()`` if
              micro-stepping detects a zero-crossing

        See Also:
            :meth:`do_step`: Public interface that calls this method
            :meth:`report_internal_event`: Report events from micro-stepping
        """
        ...

    @abstractmethod
    def _update_output_states(
        self, t: float | None = None, event_names: list[str] | None = None
    ) -> None:
        """Subclass hook to update output port values from internal state.

        Override this method to read internal state variables and write
        them to output ports using ``self.outputs[name].set(value, t=t)``.
        Called automatically after ``initialize()`` and ``do_step()``.

        Args:
            t: Current simulation time (seconds). May be ``None`` during
                initialization in some edge cases.
            event_names: List of event names that just occurred. Allows
                conditional output updates based on which events fired.
                Empty list or ``None`` during normal stepping.

        Example:
            >>> def _update_output_states(self, t=None, event_names=None):
            ...     self.outputs['position'].set(self._x, t=t)
            ...     self.outputs['velocity'].set(self._v, t=t)
            ...     # Set event port if bounce just occurred
            ...     if event_names and 'bounce' in event_names:
            ...         self.outputs['bounce'].set(True, t=t)
            ...     else:
            ...         self.outputs['bounce'].set(False, t=t)

        Note:
            - Called after ``_initialize_component()`` during init
            - Called after ``_do_step_internal()`` during stepping
            - Called after ``_handle_events_internal()`` during events
            - Always use ``port.set(value, t=t)`` to include timestamp
        """
        ...

    def _apply_event_ports(self, t: float | None, event_names: list[str] | None) -> None:
        """Set EVENT output ports according to the events that just fired.

        When ``event_names`` is non-empty, the matching EVENT ports are set to
        ``True`` (other ports are left untouched). Otherwise every EVENT
        output port is reset to ``False``. Intended to be called at the end of
        a subclass's ``_update_output_states`` override.

        Args:
            t: Timestamp for the port updates.
            event_names: Names of the events that fired, or ``None``/empty
                during normal stepping.
        """
        if event_names:
            for event_name in event_names:
                if event_name in self.output_specs:
                    self.outputs[event_name].set(True, t=t)
        else:
            for out_port in self.outputs.values():
                if out_port.spec.type == PortType.EVENT:
                    out_port.set(False, t=t)

    # -------------------------------------------------------------------
    # State Management
    # -------------------------------------------------------------------
    def set_state(self, state: dict[str, Any], t: float) -> None:
        """Set physical state from human-readable format.

        Initializes the component from physical variables exported by
        ``get_state()``. Used for mode switching in ``MultiComponent``
        and for debugging/testing. May perform unit conversions.

        This is the "physical state transfer" interface, distinct from
        ``snapshot_state()``/``restore_state()`` which handle opaque
        solver state for time rollback.

        Args:
            state: Dictionary mapping state variable names to dicts with
                'value' and 'unit' keys. Format matches ``get_state()``
                output.
            t: Time at which to set the state (seconds). The component's
                internal time should be updated to this value.

        Example:
            >>> state = {
            ...     'q': {'value': 0.5, 'unit': 'rad'},
            ...     'omega': {'value': 1.0, 'unit': 'rad/s'}
            ... }
            >>> component.set_state(state, t=0.0)
            >>> component.t
            0.0

        Note:
            - For mode switching, state may be adapted from another model
            - Does NOT preserve solver-specific internal artifacts
            - May require re-initialization of internal solvers

        See Also:
            :meth:`get_state`: Export state in matching format
            :meth:`restore_state`: Opaque state for rollback (different use)
        """
        raise NotImplementedError(f"[{self.name}] set_state() not implemented for this component.")

    def get_state(self) -> dict[str, dict[str, Any]]:
        """Export current physical state in human-readable format.

        Returns the component's physical state variables (positions,
        velocities, etc.) in a format suitable for inspection, debugging,
        or transferring to another model during mode switching.

        This is the "physical state transfer" interface. It does NOT
        include solver-specific internal artifacts. For complete state
        capture for rollback, use ``snapshot_state()``.

        Returns:
            Dictionary mapping state variable names to dicts containing:

            - 'value': The numeric value (float or array)
            - 'unit': The physical unit string (e.g., 'rad', 'm/s')

        Example:
            >>> state = component.get_state()
            >>> print(state)
            {'q': {'value': 0.5, 'unit': 'rad'},
             'omega': {'value': 1.0, 'unit': 'rad/s'}}

        Note:
            The returned format matches what ``set_state()`` expects,
            enabling state round-tripping and model switching.

        See Also:
            :meth:`set_state`: Import state in matching format
            :meth:`snapshot_state`: Opaque state for rollback
        """
        raise NotImplementedError(f"[{self.name}] get_state() not implemented for this component.")

    def snapshot_state(self) -> Any:
        """Capture complete internal state for time rollback.

        Creates an opaque snapshot preserving ALL solver state needed
        to restore the component to its exact condition at the current
        time. This includes internal solver artifacts not exposed by
        ``get_state()``.

        This is required for event detection in hybrid co-simulation,
        where bisection search needs to roll back and retry time steps
        at different points.

        Returns:
            Opaque snapshot object. Format is component-specific and
            should be treated as a black box.

        Raises:
            NotImplementedError: If the component doesn't support
                rollback. Check ``supports_rollback`` before calling.

        Example:
            >>> snapshot = component.snapshot_state()
            >>> component.do_step(t, dt)
            >>> # Oops, event detected - roll back
            >>> component.restore_state(snapshot, t)

        Warning:
            - Snapshot format is internal and may change between versions
            - Cannot transfer snapshots between component instances
            - Only for rollback within the SAME component
            - Use ``get_state()``/``set_state()`` for model switching

        See Also:
            :meth:`restore_state`: Restore from snapshot
            :attr:`supports_rollback`: Check capability before using
            :meth:`get_state`: Human-readable state export
        """
        raise NotImplementedError(f"Component '{self.name}' does not support rollback. ")

    def restore_state(self, snapshot: Any, t: float) -> None:
        """Restore component to exact state from a snapshot.

        Reverses time by restoring the component to the state captured
        by ``snapshot_state()``. After restoration, subsequent
        ``do_step()`` calls behave as if the component never advanced
        past time ``t``.

        Used internally by the hybrid master algorithm during bisection
        search for event localization.

        Args:
            snapshot: Opaque snapshot object returned by
                ``snapshot_state()``. Must be from this component.
            t: Time at which the snapshot was originally taken (seconds).
                Component's internal time will be reset to this value.

        Raises:
            NotImplementedError: If the component doesn't support
                rollback.
            ValueError: If the snapshot is incompatible (wrong component,
                wrong mode for ``MultiComponent``).

        Example:
            >>> t_before = component.t
            >>> snapshot = component.snapshot_state()
            >>> component.do_step(t_before, dt)
            >>> # Roll back to before the step
            >>> component.restore_state(snapshot, t_before)
            >>> component.t == t_before
            True

        Warning:
            - Snapshot must be from the SAME component instance
            - Do not use across models (use ``set_state()`` instead)
            - For ``MultiComponent``, active mode must match snapshot

        See Also:
            :meth:`snapshot_state`: Create snapshots
            :meth:`set_state`: Physical state transfer between models
        """
        raise NotImplementedError("restore_state() not implemented for this component.")

    @property
    def supports_rollback(self) -> bool:
        """Check if the component supports state snapshot and restore.

        Components that support rollback can participate in hybrid
        co-simulation with event detection. The hybrid master algorithm
        requires rollback capability to perform bisection search for
        precise event localization.

        Returns:
            ``True`` if both ``snapshot_state()`` and ``restore_state()``
            are implemented (overridden from base class). ``False``
            otherwise.

        Example:
            >>> if component.supports_rollback:
            ...     component.add_event_indicator('zero_crossing', func)
            ... else:
            ...     print("Cannot add events without rollback support")

        Note:
            Automatically detects method overrides using introspection.
            No manual flag setting required.

        See Also:
            :meth:`snapshot_state`: Capture state for rollback
            :meth:`restore_state`: Restore from snapshot
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
        """Record current output values to the history buffer.

        Appends the current value of each output port to the component's
        history for later retrieval. Called automatically after
        ``initialize()`` and ``do_step()``.

        Args:
            t: Current simulation time to associate with the recorded values.

        Note:
            Only ports with non-None values are recorded. This method is
            called internally and typically should not be overridden.
        """
        for name, port in self.outputs.items():
            if port.value is not None:
                self.history.append(name, t, port.value)

    def get_history(
        self, port_names: list[str] | None = None, units: dict[str, str] | None = None
    ) -> dict[str, dict[str, Any]]:
        """Retrieve time-series history of output port values.

        Returns the recorded history from simulation as a dictionary
        structure. Optionally filter by port names and convert units.

        Args:
            port_names: List of port names to retrieve. If ``None``,
                returns history for all output ports.
            units: Dictionary mapping port names to desired output units
                (e.g., ``{'angle': 'deg'}``). Pint is used for conversion.
                If ``None``, values are returned in their original units.

        Returns:
            Dictionary mapping port names to history dictionaries with:

            - 'time': List of time values
            - 'values': List of recorded values at each time
            - 'unit': The unit of the values (after conversion)

        Example:
            >>> history = comp.get_history(['y', 'dy'])
            >>> print(history['y']['time'][:3])
            [0.0, 0.01, 0.02]
            >>> print(history['y']['values'][:3])
            [0.0, 0.1, 0.19]

            >>> # With unit conversion
            >>> history = comp.get_history(['angle'], units={'angle': 'deg'})

        See Also:
            :meth:`get_history_arrays`: Get history as NumPy arrays
        """
        return self.history.to_dict(port_names=port_names, units=units)

    def get_history_arrays(
        self, port_names: list[str] | None = None, units: dict[str, str] | None = None
    ) -> tuple[np.ndarray, dict[str, np.ndarray]]:
        """Retrieve time-series history as NumPy arrays.

        Returns the recorded history optimized for numerical analysis
        and plotting. More efficient than ``get_history()`` for large
        datasets.

        Args:
            port_names: List of port names to retrieve. If ``None``,
                returns history for all output ports.
            units: Dictionary mapping port names to desired output units.
                If ``None``, values are returned in their original units.

        Returns:
            Tuple of ``(time_array, values_dict)`` where:
            - time_array: 1D NumPy array of time points
            - values_dict: Dict mapping port names to 1D NumPy arrays

        Example:
            >>> t, values = comp.get_history_arrays(['y', 'dy'])
            >>> plt.plot(t, values['y'], label='Position')
            >>> plt.plot(t, values['dy'], label='Velocity')

        See Also:
            :meth:`get_history`: Get history as nested dictionaries
        """
        return self.history.to_arrays(port_names=port_names, units=units)

    # -------------------------------------------------------------------
    # Hybrid Capabilities - Event Indicators and Handling
    # -------------------------------------------------------------------
    def add_event_indicator(
        self, name: str, func: Callable[[CoSimComponent], float], direction: int = 0
    ) -> None:
        """Register an event indicator function for zero-crossing detection.

        Event indicators are scalar functions of component state that trigger
        events when they cross zero. The hybrid master algorithm monitors
        these indicators and uses bisection search to locate the precise
        crossing time.

        Can be called before or after ``initialize()``. If called before
        initialization, the event output port will be created during
        ``initialize()``. If called after, the port is created immediately.

        Args:
            name: Unique name for the event indicator. This name is used
                to identify the event in handlers and subscriptions.
            func: Callable that takes the component instance and returns
                a float. The event triggers when this value crosses zero.
            direction: Direction of zero-crossing to detect:
                - -1: Falling edge only (positive → negative)
                - 0: Both directions (default)
                - +1: Rising edge only (negative → positive)

        Raises:
            RuntimeError: If the component does not support rollback
                (required for bisection-based event localization).
            KeyError: If an indicator with the same name already exists.
            ValueError: If direction is not -1, 0, or +1.

        Example:
            Detect when velocity crosses zero (bouncing ball)::

                def velocity_indicator(comp: CoSimComponent) -> float:
                    return comp.outputs['v'].get()

                ball.add_event_indicator('bounce', velocity_indicator, direction=-1)

        See Also:
            :meth:`evaluate_event_indicators`: Evaluate all indicators
            :meth:`detect_event_crossings`: Check for crossings
            :attr:`has_state_events`: Check if indicators are registered
        """
        if not self.supports_rollback:
            raise RuntimeError(
                f"Component '{self.name}' must support rollback to register event indicators."
            )
        if name in self.event_indicators:
            raise KeyError(f"Event indicator '{name}' already exists in component '{self.name}'.")
        if direction not in (-1, 0, 1):
            raise ValueError("Direction must be -1 (falling), 0 (both), or +1 (rising).")

        # Register the event indicator
        self.event_indicators[name] = EventIndicator(name, func, direction)

        # If already initialized, create the event port immediately
        if self._is_initialized:
            event_port_spec = PortSpec(name=name, type=PortType.EVENT, direction="out")
            self.output_specs[name] = event_port_spec
            self.outputs[name] = PortState(event_port_spec)
            self.outputs[name].set(False, t=self.t)
            self.history.add_port(name)
            self._update_output_states(self.t)
            self._record_outputs(self.t)

    @property
    def has_state_events(self) -> bool:
        """Check if state event indicators are registered.

        State events are triggered by zero-crossings of indicator functions
        during simulation. Components with state events require the hybrid
        master algorithm for proper event detection and handling.

        Returns:
            True if at least one event indicator is registered via
            ``add_event_indicator()``. False otherwise.

        Example:
            >>> ball.add_event_indicator('bounce', velocity_indicator)
            >>> ball.has_state_events
            True

        See Also:
            :meth:`add_event_indicator`: Register event indicators
            :attr:`event_indicators`: Dictionary of registered indicators
        """
        return bool(self.event_indicators)

    def evaluate_event_indicators(self) -> dict[str, float]:
        """Evaluate all registered event indicators at the current state.

        Computes the current value of each event indicator function.
        These values are compared between time steps to detect zero
        crossings.

        Returns:
            Dictionary mapping event indicator names to their current
            float values. Positive, negative, or zero values indicate
            the position relative to the event threshold.

        Example:
            >>> indicators_before = comp.evaluate_event_indicators()
            >>> comp.do_step(t, dt)
            >>> indicators_after = comp.evaluate_event_indicators()
            >>> events = comp.detect_event_crossings(indicators_before, indicators_after)

        Note:
            Called by the hybrid master algorithm before and after each
            macro step to detect state events.
        """
        indicators = {}
        for name, indicator in self.event_indicators.items():
            indicators[name] = indicator.evaluate(self)
        return indicators

    def detect_event_crossings(
        self, previous: dict[str, float], current: dict[str, float], sign_tolerance: float = 1e-10
    ) -> list[str]:
        """Detect zero-crossings between previous and current indicator values.

        Compares indicator values before and after a time step to identify
        which indicators have crossed zero. Respects the direction setting
        of each indicator (rising, falling, or both).

        Args:
            previous: Indicator values at the start of the step, as returned
                by ``evaluate_event_indicators()`` before ``do_step()``.
            current: Indicator values at the end of the step, as returned
                by ``evaluate_event_indicators()`` after ``do_step()``.
            sign_tolerance: Values with absolute magnitude smaller than this
                threshold are treated as zero for sign determination.
                Defaults to 1e-10.

        Returns:
            List of event indicator names that experienced a zero-crossing
            during the step, filtered by each indicator's direction setting.

        Example:
            >>> prev = comp.evaluate_event_indicators()  # {'bounce': 0.5}
            >>> comp.do_step(t, dt)
            >>> curr = comp.evaluate_event_indicators()  # {'bounce': -0.2}
            >>> events = comp.detect_event_crossings(prev, curr)
            >>> print(events)
            ['bounce']

        Note:
            This method only detects that a crossing occurred somewhere in
            the interval. Use bisection search to locate the precise time.
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
        """Report an event detected during internal micro-stepping.

        Call this from ``_do_step_internal()`` when an event is detected
        during internal sub-stepping. The master algorithm uses these
        hints to narrow the bisection interval, improving event
        localization efficiency.

        Args:
            event_name: Name of the event indicator that crossed zero.
                Must match a registered event indicator name.
            t_before: Last micro-step time before the event was detected.
                Should be within the current macro step interval.
            t_after: First micro-step time after the event was detected.
                Together with ``t_before``, defines a bracket for bisection.
            indicator_before: Indicator value at ``t_before``. Optional but
                improves localization accuracy if available.
            indicator_after: Indicator value at ``t_after``. Optional but
                improves localization accuracy if available.

        Example:
            Inside an adaptive integrator::
            >>>
            >>>    def _do_step_internal(self, t, dt):
            >>>        h = dt / 100  # Internal micro-step
            >>>        for i in range(100):
            >>>            t_i = t + i * h
            >>>            #... integration logic ...
            >>>            if velocity_before > 0 and velocity_after < 0:
            >>>                self.report_internal_event(
            >>>                    'bounce', t_i, t_i + h,
            >>>                    velocity_before, velocity_after
            >>>                )

        Note:
            Hints are consumed by ``get_internal_event_hints()`` and cleared
            after retrieval. Multiple hints can be reported per step.

        See Also:
            :meth:`get_internal_event_hints`: Retrieve and clear hints
            :class:`InternalEventInfo`: Hint data structure
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
        """Retrieve and clear internal event timing hints.

        Returns event hints reported by the component during micro-stepping
        and clears the internal buffer. Called by the master algorithm
        after each macro step to incorporate micro-step event information
        into the bisection search.

        Returns:
            List of ``InternalEventInfo`` objects containing timing brackets
            for events detected during micro-stepping. The list is cleared
            after this call.

        Example:
            >>> comp.do_step(t, dt)
            >>> hints = comp.get_internal_event_hints()
            >>> for hint in hints:
            ...     print(f"{hint.event_name}: [{hint.t_before}, {hint.t_after}]")

        Note:
            Each call clears the hints buffer. Call only once per step
            to avoid losing information.

        See Also:
            :meth:`report_internal_event`: Add hints during stepping
        """
        hints = self.internal_event_hints.copy()
        self.internal_event_hints.clear()
        return hints

    def subscribe_event(self, event: Event) -> None:
        """Register a subscription to an external event.

        Allows this component to receive notifications when another
        component emits a named event. The subscription is pattern-based:
        specify the source component and event name to listen for.

        Args:
            event: An ``Event`` object specifying the source component
                and event name to subscribe to. The ``time`` field must
                be ``None`` (subscriptions are not time-specific).

        Raises:
            ValueError: If ``event.time`` is not ``None``.
            KeyError: If an identical subscription already exists.

        Example:
            Subscribe to a sensor's threshold event::
            >>>
            >>>    from syssimx.core.events import Event
            >>>
            >>>    threshold_event = Event(name='high_temp', source='sensor_1')
            >>>    controller.subscribe_event(threshold_event)

        Note:
            When the subscribed event fires, ``handle_event()`` is called
            with the event name in the ``event_names`` list.

        See Also:
            :meth:`handle_event`: Called when subscribed events occur
            :attr:`has_event_subscriptions`: Check for subscriptions
        """
        if event.time is not None:
            raise ValueError("Subscription events must not include a time.")
        for existing in self.event_subscriptions:
            if existing.name == event.name and existing.source == event.source:
                raise KeyError(
                    f"Event subscription '{event.source}:{event.name}' already exists in component '{self.name}'."
                )
        self.event_subscriptions.append(event)

    @property
    def self_handled_events(self) -> list[str]:
        """Names of own events this component reacts to without external wiring.

        Events normally reach a component through an :class:`EventConnection`.
        Some components own events whose effect is purely internal, so
        requiring the user to wire the component to itself would be ceremony
        that is easy to forget. ``System.initialize()`` subscribes the
        component to every event named here.

        Returns:
            Event indicator names, all of which must be registered on this
            component. Empty by default.

        See Also:
            :meth:`MultiComponent.add_switch_indicator`: Registers a mode
            switch, which is handled by the wrapper that owns it.
        """
        return []

    @property
    def has_event_subscriptions(self) -> bool:
        """Check if this component subscribes to external events.

        Event subscriptions allow a component to receive and react to
        events emitted by other components in the system.

        Returns:
            True if at least one event subscription is registered via
            ``subscribe_event()``. False otherwise.

        See Also:
            :meth:`subscribe_event`: Register event subscriptions
            :attr:`event_subscriptions`: List of subscribed events
        """
        return bool(self.event_subscriptions)

    def handle_event(
        self, event_names: list[str], t: float, events: list[Event] | None = None
    ) -> None:
        """Process detected events and update component state.

        Called by the master algorithm when events are detected and
        localized. Invokes the subclass event handler, updates outputs,
        and records the post-event state.

        Args:
            event_names: List of event names that occurred at this time.
                May include multiple simultaneous events.
            t: Precise time at which the events occurred (after
                bisection localization).

        Example:
            Handling a bounce event::

                def _handle_events_internal(self, event_names, t):
                    if 'bounce' in event_names:
                        # Reverse velocity with coefficient of restitution
                        v = self.outputs['v'].get()
                        self._velocity = -0.8 * v

        Note:
            Override ``_handle_events_internal()`` to implement custom
            event handling logic. This wrapper method ensures outputs
            are properly updated and recorded after event handling.

        See Also:
            :meth:`_handle_events_internal`: Subclass hook for event logic
        """
        if events is not None and {event.name for event in events} != set(event_names):
            raise ValueError("Event metadata must match the handled event names.")
        previous_events = self._events_being_handled
        self._events_being_handled = {event.name: event for event in events or []}
        try:
            self._handle_events_internal(event_names, t)
            self._update_output_states(t, event_names)
            self._record_outputs(t)
        finally:
            self._events_being_handled = previous_events

    def _handle_events_internal(self, event_names: list[str], t: float) -> None:
        """Subclass hook for custom event handling logic.

        Override this method to implement state discontinuities, mode
        switches, or other event-driven behavior. Called by
        ``handle_event()`` when events are detected.

        Args:
            event_names: List of event indicator names that triggered.
                Check membership to determine which events occurred.
            t: Precise event time after bisection localization.

        Example:
            Implementing a bouncing ball::

                def _handle_events_internal(self, event_names, t):
                    if 'ground_contact' in event_names:
                        self._velocity *= -self.parameters['restitution']
                        self._position = 0.0  # Reset to ground level

        Note:
            - Called before ``_update_output_states()``
            - Multiple events may fire simultaneously
            - State changes here should be reflected in subsequent outputs
        """
        pass

    # -------------------------------------------------------------------
    # Cleanup - reset and free
    # -------------------------------------------------------------------
    def reset(self) -> None:
        """Reset component to clean state for re-initialization.

        Clears the simulation time, history buffer, and initialization flag.
        After calling ``reset()``, the component can be re-initialized with
        ``initialize()`` for a new simulation run.

        Subclasses should call ``super().reset()`` and additionally clear
        any internal state variables.

        Example:
            >>> comp.initialize(t0=0.0)
            >>> comp.do_step(0.0, 0.01)
            >>> comp.reset()
            >>> comp.initialize(t0=5.0)  # Fresh start at t=5

        Note:
            Does not release resources (use ``free()`` for that). The
            component remains usable after reset.

        See Also:
            :meth:`free`: Release resources permanently
            :meth:`initialize`: Re-initialize after reset
        """
        self.t = 0.0
        self.history.clear()
        self._is_initialized = False

    def free(self) -> None:
        """Release component resources permanently.

        Override this method in subclasses to clean up external resources
        such as FMU instances, file handles, network connections, or
        native library memory.

        Example:
            >>> system.run(t0=0, tf=10, dt=0.01)
            >>> for comp in system.components.values():
            ...     comp.free()  # Clean up all resources

        Note:
            After calling ``free()``, the component may not be usable.
            For reuse, call ``reset()`` instead.

        See Also:
            :meth:`reset`: Reset for re-initialization without freeing
        """
        pass

    # -------------------------------------------------------------------
    # Detect Direct Feedthrough
    # -------------------------------------------------------------------
    def _detect_direct_feedthrough(self) -> dict[str, set[str]]:
        """Detect direct feedthrough dependencies between inputs and outputs.

        Analyzes the component's behavior to determine which output ports
        depend algebraically on which input ports. This information is used
        to identify potential algebraic loops in the system.

        Returns:
            Dictionary mapping output port names to sets of input port
            names that have direct feedthrough to that output. If an output
            has no direct feedthrough, it maps to an empty set.

        Example:
            >>> comp.direct_feedthrough = comp._detect_direct_feedthrough()
            >>> print(comp.direct_feedthrough)
            {'y': {'u', 'v'}, 'z': {'u'}, 'w': set()}
        Note:
            - Called during initialization to populate
              ``self.direct_feedthrough``
            - Uses finite difference perturbation to test dependencies
            - May be overridden in subclasses for efficiency
        """
        feedthrough_map: dict[str, set[str]] = {
            out_name: set()
            for out_name, spec in self.output_specs.items()
            if spec.type == PortType.REAL
        }

        # Small perturbation value
        delta = 1e-3

        def _as_float(value: Any) -> float:
            if value is None:
                return 0.0
            if hasattr(value, "magnitude"):
                return float(value.magnitude)
            return float(value)

        # Store original input values
        inputs = [name for name, spec in self.input_specs.items() if spec.type == PortType.REAL]
        original_inputs = {}
        for inp_name in inputs:
            value = self.inputs[inp_name].get()
            original_inputs[inp_name] = _as_float(value)

        # Store original output values
        original_outputs = self.evaluate_outputs(original_inputs)

        # Perturb each input and check output changes
        perturbed_inputs = original_inputs.copy()
        for inp_name in inputs:
            # Perturb input
            perturbed_inputs[inp_name] = _as_float(perturbed_inputs[inp_name]) + delta

            # Evaluate outputs with perturbed input
            perturbed_outputs = self.evaluate_outputs(perturbed_inputs)
            # Check which outputs changed
            for out_name, orig_value in original_outputs.items():
                pert_value = perturbed_outputs[out_name]
                if _as_float(orig_value) != _as_float(pert_value):
                    # not np.isclose(
                    #     _as_float(orig_value), _as_float(pert_value), rtol=1e-3#, atol=1e-8
                    # ):
                    feedthrough_map[out_name].add(inp_name)

            # Reset input
            perturbed_inputs[inp_name] = original_inputs[inp_name]

        # Restore original inputs on the component to avoid leaving
        # perturbed values behind after detection.
        if original_inputs:
            self.set_inputs(original_inputs)

        self.direct_feedthrough = feedthrough_map
        return feedthrough_map

    # -------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------
    @property
    def reactive_inputs(self) -> set[str]:
        """Input port names with direct algebraic feedthrough to outputs.

        An input is "reactive" if changing its value immediately affects
        at least one output without requiring a time step. This information
        is used by the System to detect algebraic loops.

        Returns:
            Set of input port names that have direct feedthrough to any
            output. Empty set if no feedthrough exists.

        Example:
            >>> comp.direct_feedthrough = {'y': {'u', 'v'}, 'z': {'u'}}
            >>> comp.reactive_inputs
            {'u', 'v'}

        See Also:
            :attr:`direct_feedthrough`: Full input-output dependency map
            :attr:`has_direct_feedthrough`: Boolean check for any feedthrough
        """
        reactive_inputs = set(inp for outs in self.direct_feedthrough.values() for inp in outs)
        return reactive_inputs

    @property
    def has_direct_feedthrough(self) -> bool:
        """Check if any output depends algebraically on any input.

        Direct feedthrough occurs when an output depends directly on an
        input in the same time step, without intermediate state dynamics.
        Components with direct feedthrough create potential algebraic
        loops when connected in cycles.

        Returns:
            True if at least one input-output pair has direct feedthrough.
            False if all outputs depend only on internal state.

        Example:
            >>> # A pure gain has direct feedthrough: y = k * u
            >>> gain.has_direct_feedthrough
            True
            >>> # An integrator has no feedthrough: y = integral(u)
            >>> integrator.has_direct_feedthrough
            False

        See Also:
            :attr:`direct_feedthrough`: Detailed dependency mapping
            :attr:`reactive_inputs`: Set of inputs with feedthrough
        """
        return any(self.direct_feedthrough.values())
