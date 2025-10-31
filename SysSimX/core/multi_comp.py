from __future__ import annotations
from typing import Any, Dict, Optional, Tuple, List, Callable, Protocol
from pathlib import Path

from .base import CoSimComponent
from .port import PortSpec, PortState, PortType
from ..utilities.units import ureg, Quantity, to_pint_unit

# -------------------------------------------------------------------
# Helpers for mode management
# -------------------------------------------------------------------

ModeKey = str

class StateAdapter(Protocol):
    def get_state(self, comp: CoSimComponent) -> Dict[str, Any]:
        ...
    def set_state(self, comp: CoSimComponent, state: Dict[str, Any]) -> None:
        ...

class Hysteresis:
    """
    Hysteresis mechanism to prevent frequent mode switching around thresholds.
     - dwell_time: Minimum time to wait before allowing another switch.
     - last_switch_time: Time of the last mode switch.
     - last_mode: The last active mode.
    """
    def __init__(self, dwell_time: float=0.03,
                 last_switch_time: float=0.0,
                 last_mode: ModeKey=""):
        self.dwell_time = dwell_time
        self.last_switch_time = last_switch_time
        self.last_mode = last_mode

    def get_mode(self, t: float, proposed_mode: ModeKey) -> ModeKey:
        """
        Determine if a mode switch is allowed based on dwell time.
        """
        if proposed_mode != self.last_mode and (t - self.last_switch_time) < self.dwell_time:
            return self.last_mode
        self.last_switch_time = t
        self.last_mode = proposed_mode
        return self.last_mode
    
# -------------------------------------------------------------------
# Multi-Component Wrapper
# -------------------------------------------------------------------
class MultiComponent(CoSimComponent):
    """
    Abstract base class for components that wrap multiple interchangeble components.
    Subclass must:

    """
    def __init__(self,
                 name: str,
                 group: Optional[str] = None):
        super().__init__(name=name, group=group)
        self._params: Dict[str, Any] = {}
        self.models: Dict[ModeKey, CoSimComponent] = {}
        self.state_adapters: Dict[ModeKey, StateAdapter] = {}
        self.active_key: ModeKey = ""
        self.active_comp: Optional[CoSimComponent] = None
        self.hysteresis: Optional[Hysteresis] = None
        self.mode_rule: Optional[Callable[[float, Dict[str, Any]], ModeKey]] = None

    # -------------------------------------------------------------------
    # Functions to be implemented by subclasses
    # -------------------------------------------------------------------
    def _build_models(self) -> None:
        """
        Abstract method to build the sub-components.
        Subclasses must implement this method to populate self.models.
        """
        raise NotImplementedError("Subclasses must implement _build_models method.")
    
    def publish_from(self, src: CoSimComponent, t: float) -> None:
        """
        Subclass: copy outputs from src component to self.outputs with proper unit conversion.
        """
        raise NotImplementedError("Subclasses must implement publish_from method.")
    
    # -------------------------------------------------------------------
    # MultiComp Interface
    # -------------------------------------------------------------------

    def _initialize_component(self, t0: float) -> None:
        """
        Initialize the multi-component and all sub-components.
        """
        pass

    def set_inputs(self, signals: Dict[str, Any], t: Optional[float] = None) -> None:
        self.active_comp.set_inputs(signals, t=t)
    
    def get_outputs(self):
        return self.active_comp.get_outputs()