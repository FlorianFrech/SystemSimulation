from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple, Union
from .port import PortSpec, PortState
from ..utilities.units import ureg, Quantity

class CoSimComponent(ABC):
    """
    Unified co-simulation component interface.
     - Defines metadata, port specifications, and state handling
     - Abstract methods for lifecycle management (initialize, set_inputs, do_step, get_outputs, set_state, get_state, reset)
     - Default implementations for common behaviors (set_inputs, get_outputs)
    """
    # Metadata
    name: str
    label: str
    group: Optional[str] = None
    
    # Port specifications (immutable) and states (mutable)
    input_specs = Dict[str, PortSpec]
    output_specs = Dict[str, PortSpec]
    inputs: Dict[str, PortState]
    outputs: Dict[str, PortState]

    def __init__(self, name: str, label: Optional[str] = None, group: Optional[str] = None):
        self.name = name
        self.label = label if label is not None else name
        self.group = group
        self.input_specs = {}
        self.output_specs = {}
        self.inputs = {}
        self.outputs = {}

    # ---- Configuration ----
    def set_parameters(self, **parameters: Any) -> None:
        """Set the parameters of the component during initialization."""
        pass

    # ---- Lifecycle ----
    @abstractmethod
    def initialize(self, t0: float) -> None:
        """Initialize the component at the start time t0."""
        ...
    
    def set_inputs(self, signals: Dict[str, Any], t: Optional[float] = None) -> None:
        """
        Default method for inputs. Subclasses can override for custom behavior.
        """
        for k, v in signals.items():
            if k not in self.inputs:
                raise KeyError(f"Input port '{k}' not found in component '{self.name}'.")
            self.inputs[k].set(v, t=t)
    
    @abstractmethod
    def do_step(self, t: float, dt: float) -> None:
        """Advance the component's state from time t to t+dt."""
        ...
    
    def get_outputs(self) -> Dict[str, Any]:
        """Return the current outputs as a dictionary {name: value}."""
        if self.outputs is None:
            return {}
        return {k: v.get() for k, v in self.outputs.items() if v.get() is not None}
    
    @abstractmethod
    def set_state(self, state: Dict[str, Any]) -> None:
        """Overwrite the current state of the component."""
        ...

    @abstractmethod
    def get_state(self) -> Dict[str, Any] | None:
        """Return the current state of the component, or None if not supported."""
        ...
    
    @abstractmethod
    def reset(self) -> None:
        """Reset the component to a clean state before (before initialization)."""
        ...

    def free(self) -> None:
        """Optional: Free resources associated with the component."""
        pass