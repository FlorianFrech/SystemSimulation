from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple, Set, List
from .port import PortSpec, PortState
from .history import ComponentHistory

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

        self.direct_feedthrough: Dict[str, Set[str]] = {}
        self.model_structure: Dict[str, Dict[str, List[str]]] = {
            "outputs": {},
            "derivatives": {},
            "initialUnknowns": {},
        }

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
        # For non-FMUs this is often enough:
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
    def _update_output_states(self, t: float) -> None:
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
    def has_state(self) -> bool:
        """Override in subclasses that have ODE/DAE state."""
        return False
    
    @property
    def has_direct_feedthrough(self) -> bool:
        return any(self.direct_feedthrough.values())