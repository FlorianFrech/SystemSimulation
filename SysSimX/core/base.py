from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
from .port import Port

class CoSimComponent(ABC):
    """
    Abstract base class for a co-simulation component (FMU, OpenSim model, etc.).
    Implementations must inherit from this class and implement the methods defined here.
        
        :param name: Name of the component instance.
        :param label: Label for visualization in the system graph.
        :param group: Optional group name for organizing components in the system graph clusters.
        :param inputs: Optional dictionary of input ports {port_name: Port}.
        :param outputs: Optional dictionary of output ports {port_name: Port}.
    """
    name: str
    label: str
    group: Optional[str] = None
    inputs: Optional[Dict[str, Port]]
    outputs: Optional[Dict[str, Port]]

    # ---- Port Introspection ----
    @abstractmethod
    def input_ports(self) -> Dict[str, Port]:
        """Return {port_name: unit_str} for inputs."""

    @abstractmethod
    def output_ports(self) -> Dict[str, Port]:
        """Return {port_name: unit_str} for outputs."""

    # ---- Configuration ----
    @abstractmethod
    def set_parameters(self, **parameters: Any) -> None:
        """Set the parameters of the component during initialization."""

    # ---- Lifecycle ----
    @abstractmethod
    def initialize(self, t0: float) -> None:
        """Initialize the component at the start time t0."""
    
    @abstractmethod
    def set_inputs(self, **signals: float) -> None:
        """Set the input signals for the next step."""
    
    @abstractmethod
    def do_step(self, t: float, h: float) -> None:
        """Advance the component's state from time t to t+h."""
    
    @abstractmethod
    def get_outputs(self) -> Dict[str, float]:
        """Return the current outputs as a dictionary {name: value}."""
    
    @abstractmethod
    def get_state(self) -> Dict[str, Any] | None:
        """Return the current state of the component, or None if not supported."""
    
    @abstractmethod
    def set_state(self, state: Dict[str, Any]) -> None:
        """Overwrite the current state of the component."""

    @abstractmethod
    def reset(self) -> None:
        """Reset the component to a clean state before (before initialization)."""

    def free(self) -> None:
        """Optional: Free resources associated with the component."""
        pass

    def reinitialize(self, t: float, state: Optional[Dict[str, Any]] = None) -> None:
        """Optional: Reinitialize the component, optionally restoring a previous state."""
        pass
    