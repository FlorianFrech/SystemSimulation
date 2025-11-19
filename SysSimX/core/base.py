from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple, Union, Set, List
from .port import PortSpec, PortState
from ..utilities.units import ureg, Quantity

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

        # Parameter container (populated by subclasses)
        self.parameters: Dict[str, Any] = {}

        self.direct_feedthrough: Dict[str, Set[str]] = {}
        self.model_structure: Dict[str, Dict[str, List[str]]] = {
            "outputs": {},
            "derivatives": {},
            "initialUnknowns": {},
        }

    # ---- Port Management Helper ----
    def _initialize_ports_from_specs(self) -> None:
        """
        Create PortState instances from input_specs and output_specs.
        Call this in subclass __init__ after defining specs.
        """
        for spec in self.input_specs.values():
            self.inputs[spec.name] = PortState(spec)
        for spec in self.output_specs.values():
            self.outputs[spec.name] = PortState(spec)

    # ---- Configuration ----
    def set_parameters(self, **parameters: Any) -> None:
        """
        Set component parameters BEFORE initialize().
        Default: store in self.parameters dict. Override for validation.
        """
        for name, value in parameters.items():
            if name not in self.parameters:
                raise KeyError(f"Unknown parameter '{name}' in component '{self.name}'")
            self.parameters[name] = value

    # ---- Lifecycle ----
    def initialize(self, t0: float) -> None:
        """
        Initialize the component at start time t0.
        Base class sets time and calls abstract hook.
        """
        self.t = t0
        self._initialize_component(t0)
        self._update_output_states(t0)  # Ensure outputs ready after init

    @abstractmethod
    def _initialize_component(self, t0: float) -> None:
        """Subclass hook: setup solver, mesh, FMU instance, etc."""
        ...
    
    def set_inputs(self, signals: Dict[str, Any], t: Optional[float] = None) -> None:
        """
        Default input setter. Override for type conversions or special handling.
        """
        for k, v in signals.items():
            if k not in self.inputs:
                raise KeyError(f"Input port '{k}' not found in component '{self.name}'.")
            self.inputs[k].set(v, t=t)

    def do_step(self, t: float, dt: float) -> None:
        """
        Advance simulation from t to t+dt.
        Base class updates time and outputs; subclass does computation.
        """
        self._do_step_internal(t, dt)
        self.t = t + dt
        self._update_output_states(self.t)
    
    @abstractmethod
    def _do_step_internal(self, t: float, dt: float) -> None:
        """Subclass hook: perform actual time step computation."""
        ...

    def get_outputs(self) -> Dict[str, Any]:
        """Return current outputs as {name: value} dict."""
        return {k: v.get() for k, v in self.outputs.items() if v.get() is not None}

    # ---- Abstract Output Update Hook ----
    @abstractmethod
    def _update_output_states(self, t: float) -> None:
        """
        Subclass hook: read internal state and update self.outputs[...].set(value, t).
        Called automatically after initialize() and do_step().
        """
        ...
    
    @abstractmethod
    def set_state(self, state: Dict[str, Any], t: float) -> None:
        """Overwrite component state (for switching or checkpointing)."""
        ...

    @abstractmethod
    def get_state(self) -> Dict[str, Any]:
        """Return current state as dict {var_name: {'value': ..., 'unit': ...}}."""
        ...

    def get_history(self) -> Dict[str, List[Tuple[float, Any]]]:
        """
        Optional: return time history of states/outputs for logging or analysis.
        Default: empty dict.
        """
        history = {}
        for name, out_port in self.outputs.items():
            if out_port.history:
                history[name] = out_port.history
        return history

    @abstractmethod
    def reset(self) -> None:
        """Reset to clean state before re-initialization."""
        ...

    def free(self) -> None:
        """Optional: release resources (FMU instances, OpenSim memory, etc.)."""
        pass
    
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
