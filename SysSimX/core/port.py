from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
from .units import UREG, to_pint_unit
from pint import Quantity as Q
from pint import Unit

class Port(ABC):
    """
    Abstract base class for a port (input or output) of a co-simulation component.
    """
    name: str
    type: Any
    value: Any
    unit: Optional[Unit]
    quantity: Optional[Q]
    description: Optional[str]

class RealPort(Port):
    """
    A port representing a real-valued signal.
    """
    def __init__(self, name: str, value: float, unit: Optional[str] = None, description: Optional[str] = None):
        self.name = name
        self.type = float
        self.value = value
        self.unit = unit
        self.description = description
        self.quantity = Q(0, self.unit) if self.unit else Q(0)

class IntPort(Port):
    """
    A port representing an integer-valued signal.
    """
    def __init__(self, name: str, value: int, description: Optional[str] = None):
        self.name = name
        self.type = int
        self.value = 0
        self.description = description

class BoolPort(Port):
    """
    A port representing a boolean-valued signal.
    """
    def __init__(self, name: str, description: Optional[str] = None):
        self.name = name
        self.type = bool
        self.value = False
        self.description = description

class StringPort(Port):
    """
    A port representing a string-valued signal.
    """
    def __init__(self, name: str, description: Optional[str] = None):
        self.name = name
        self.type = str
        self.value = ""
        self.description = description