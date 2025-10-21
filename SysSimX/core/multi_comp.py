from __future__ import annotations
from typing import Any, Dict, Optional, Tuple, List
from pathlib import Path

from fmpy import read_model_description, extract
from fmpy.model_description import ModelVariable, ModelDescription
from fmpy.fmi2 import FMU2Slave

from .base import CoSimComponent
from .port import PortSpec, PortState, PortType
from ..utilities.units import ureg, Quantity, to_pint_unit

class MultiComp(CoSimComponent):
    """
    Multi-component co-simulation component that encapsulates multiple sub-components.
    """

    active_component: Optional[CoSimComponent] = None
    """Reference to the currently active sub-component."""
    
    def __init__(self, 
                 name: str, 
                 components: List[CoSimComponent], 
                 label: Optional[str] = None, 
                 group: Optional[str] = None):
        super().__init__(name, label, group)
        
        self.components = components
        
        # Verify that all components have unique names
        # TODO: Implement uniqueness check

        # Verify that all components have the same input/output specs
        # TODO: Implement spec consistency check

        # Initialize port states based on specifications
        # TODO: Implement port state initialization

