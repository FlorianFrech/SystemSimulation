from __future__ import annotations
from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple, Set, List, Callable
from .port import PortSpec, PortState, PortType
from .history import ComponentHistory
from .events import EventIndicator, Event, _sign

# -------------------------------------------------------------------
# CoSimComponent - Base Class for Co-Simulation Components
# -------------------------------------------------------------------
class CoSimComponent(ABC):
    """
    Unified co-simulation component interface with common functionality.
    """
    name: str
    label: str
    group: Optional[str] = None
    t: float = 0.0  # Current simulation time

    def __init__(self, name: str, label: Optional[str] = None, group: Optional[str] = None):
        self.name = name
        self.label = label if label is not None else name
        self.group = group
        
        # Port specifications (immutable) and states (mutable)
        self.input_specs: Dict[str, PortSpec] = {}
        self.output_specs: Dict[str, PortSpec] = {}
        self.inputs: Dict[str, PortState] = {}
        self.outputs: Dict[str, PortState] = {}

        # History tracking
        self.history = ComponentHistory(component_name=name)

        # Parameter container (populated by subclasses)
        self.parameters: Dict[str, Any] = {}
        
        # Model structure and direct feedthrough info
        self.direct_feedthrough: Dict[str, Set[str]] = {}
        self.model_structure: Dict[str, Dict[str, List[str]]] = {
            "outputs": {},
            "derivatives": {},
            "initialUnknowns": {},
        }

        # Hybrid capabilities
        self.event_indicators: Dict[str, EventIndicator] = {}
        self.event_subscriptions: List[Event] = []

    # -------------------------------------------------------------------
    # Construction of Port States from Specs
    # -------------------------------------------------------------------
    def _initialize_ports_from_specs(self) -> None:
        """
        Create PortState instances from input_specs and output_specs.
        Call this in subclass __init__ after defining specs.
        """
        for spec in self.input_specs.values():
            self.inputs[spec.name] = PortState(spec)
        for spec in self.output_specs.values():
            self.outputs[spec.name] = PortState(spec)
            self.history.add_port(spec.name, spec.unit)

    # -------------------------------------------------------------------
    # Configuration - setting parameters
    # -------------------------------------------------------------------
    def set_parameters(self, **parameters: Any) -> None:
        """
        Set component parameters BEFORE initialize().
        Default: store in self.parameters dict. Override for validation.
        """
        for name, value in parameters.items():
            if name not in self.parameters:
                raise KeyError(f"Unknown parameter '{name}' in component '{self.name}'")
            self.parameters[name] = value
    
    def get_parameters(self) -> Dict[str, Any]:
        """Return current parameters as dict."""
        return self.parameters.copy()

    # -------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------
    def initialize(self, t0: float) -> None:
        """
        Initialize the component at start time t0.
        Base class sets time and calls abstract hook.
        """
        self.t = t0
        self._initialize_component(t0)
        self._update_output_states(t0)
        self._record_outputs(t0)

    @abstractmethod
    def _initialize_component(self, t0: float) -> None:
        """Subclass hook: setup solver, mesh, FMU instance, etc."""
        ...

    # -------------------------------------------------------------------
    # Setting Inputs
    # -------------------------------------------------------------------
    def set_inputs(self, signals: Dict[str, Any], t: Optional[float] = None) -> None:
        """
        Default input setter. Override for type conversions or special handling.
        """
        for k, v in signals.items():
            if k not in self.inputs:
                raise KeyError(f"Input port '{k}' not found in component '{self.name}'.")
            self.inputs[k].set(v, t=t)

    # -------------------------------------------------------------------
    # Direct Feedthrough - Output Evaluation
    # -------------------------------------------------------------------
    def evaluate_outputs(self, inputs: Dict[str, Any], t: Optional[float] = None) -> Dict[str, Any]:
        """
        Default: set given inputs, call an internal "evaluation" step with dt=0,
        and return current outputs as plain values (no units).

        Components without direct feedthrough can just ignore the inputs and
        return their already-valid outputs.
        """
        # Default implementation: just set inputs and return outputs
        if inputs:
            self.set_inputs(inputs, t=None)
        # For non-FMUs
        return {name: port.get() for name, port in self.outputs.items()}
    
    # -------------------------------------------------------------------
    # Performing Time Steps
    # -------------------------------------------------------------------
    def do_step(self, t: float, dt: float) -> None:
        """
        Advance simulation from t to t+dt.
        Base class updates time and outputs; subclass does computation.
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
    def _update_output_states(self, t: Optional[float]=None) -> None:
        """
        Subclass hook: read internal state and update self.outputs[...].set(value, t).
        Called automatically after initialize() and do_step().
        """
        ...

    # -------------------------------------------------------------------
    # Getting Outputs
    # -------------------------------------------------------------------
    def get_outputs(self) -> Dict[str, Any]:
        """Return current outputs as {name: value} dict."""
        return {k: v.get() for k, v in self.outputs.items() if v.get() is not None}

    # -------------------------------------------------------------------
    # State Management
    # -------------------------------------------------------------------
    @abstractmethod
    def set_state(self, state: Dict[str, Any], t: float) -> None:
        """Overwrite component state (for switching or checkpointing)."""
        ...

    @abstractmethod
    def get_state(self) -> Dict[str, Any]:
        """Return current state as dict {var_name: {'value': ..., 'unit': ...}}."""
        ...
   
    # -------------------------------------------------------------------
    # Port History Recording and Retrieval
    # -------------------------------------------------------------------
    def _record_outputs(self, t: float) -> None:
        """Record current output values to history."""
        for name, port in self.outputs.items():
            if port.value is not None:
                self.history.append(name, t, port.value)  

    def get_history(self, port_names: Optional[List[str]] = None, 
                    units: Optional[Dict[str, str]] = None) -> Dict[str, Dict[str, Any]]:
        """
        Get history of output ports.
        
        Args:
            port_names: List of specific ports to retrieve. If None, returns all.
            units: Dict mapping port names to desired units for conversion.
        
        Returns:
            Dict mapping port names to history dicts with 'time', 'values', 'unit'.
        """
        return self.history.to_dict(port_names=port_names, units=units)
    
    def get_history_arrays(self, port_names: Optional[List[str]] = None,
                           units: Optional[Dict[str, str]] = None) -> Tuple[np.ndarray, Dict[str, np.ndarray]]:
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
    def add_event_indicator(self, name: str, func: Callable[["CoSimComponent"], float], direction: int=0) -> None:
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
        event_port_spec = PortSpec(
            name=name,
            type=PortType.EVENT,
            direction="out")
        self.output_specs.update({event_port_spec.name: event_port_spec})
        self.outputs[event_port_spec.name] = PortState(event_port_spec)
        self.outputs[event_port_spec.name].set(False, t=self.t)
        self.history.add_port(event_port_spec.name)
        self._update_output_states(self.t)
        self._record_outputs(self.t)

    def evaluate_event_indicators(self) -> Dict[str, float]:
        """
        Evaluate all event indicators and return their current values.
        """
        indicators = {}
        for name, indicator in self.event_indicators.items():
            indicators[name] = indicator.evaluate(self)
        return indicators
    
    def detect_event_crossing(self, previous: Dict[str, float],
                              current: Dict[str, float],
                              sign_tolerance: float = 1e-10) -> List[str]:
        """
        Detect zero-crossings between previous and current indicator values.
        
        Args:
            sign_tolerance: Values smaller than this are considered zero for sign detection
        """
        events = []
        for name, indicator in self.event_indicators.items():
            prev_sign = _sign(previous[name], sign_tolerance)
            curr_sign = _sign(current[name], sign_tolerance)
            value = current[name]
            
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
    
    @property
    def has_state_events(self) -> bool:
        """True if the component currently has one or more state event indicators."""
        return bool(self.event_indicators)

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

    # -------------------------------------------------------------------
    # Hybrid Capabilities - State Snapshots and Rollback
    # -------------------------------------------------------------------
    def snapshot_state(self) -> Any:
        """
        Return an opaque snapshot that can be passed back to restore_state().
        Components that do not support rollback must override supports_rollback to False
        and may raise NotImplementedError here.
        """
        raise NotImplementedError("snapshot_state() not implemented for this component.")

    def restore_state(self, snapshot: Any, t: float) -> None:
        """
        Restore the component to the state represented by 'snapshot' at time t.
        This must be a *pure rollback*: subsequent do_step(t, dt) calls behave as if
        the component had never advanced past t.
        """
        raise NotImplementedError("restore_state() not implemented for this component.")

    @property
    def supports_rollback(self) -> bool:
        """True if the component supports state snapshot and rollback."""
        # Check if methods are overridden from base class
        return (
            type(self).snapshot_state is not CoSimComponent.snapshot_state and
            type(self).restore_state is not CoSimComponent.restore_state
        )
    
    # -------------------------------------------------------------------
    # Hybrid Capabilities - Event Handling
    # -------------------------------------------------------------------
    def handle_event(self, event_names: List[str], t: float) -> None:
        """
        Handle events by calling subclass hook.
        """
        self._handle_events_internal(event_names, t)
    
    def _handle_events_internal(self, event_names: List[str], t: float) -> None:
        """Subclass hook: handle events (state updates, re-initialization, etc.)."""
        pass

    # -------------------------------------------------------------------
    # Cleanup - reset and free
    # -------------------------------------------------------------------
    @abstractmethod
    def reset(self) -> None:
        """Reset to clean state before re-initialization."""
        self.history.clear()

    def free(self) -> None:
        """Optional: release resources (FMU instances, OpenSim memory, etc.)."""
        pass
    
    # -------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------
    @property
    def reactive_inputs(self) -> Set[str]:
        """Inputs that affect at least one connected output algebraically."""
        reactive_inputs = set(inp for outs in self.direct_feedthrough.values() for inp in outs)
        return reactive_inputs
    
    @property
    def has_direct_feedthrough(self) -> bool:
        return any(self.direct_feedthrough.values())
    
    # -------------------------------------------------------------------
    # General Representation
    # -------------------------------------------------------------------
    def __repr__(self):
        repr = f"<CoSimComponent name='{self.name}'>"
        return repr
    
    def __str__(self):
        return self.__repr__()
