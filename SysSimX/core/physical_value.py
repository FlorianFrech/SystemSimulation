from dataclasses import dataclass
from typing import Union, Iterable
import numpy as np
from units import Q, qty, parse_unit

# --------------------------------------------------------------------------
# Physical value class for name and quantity
@dataclass
class PhysicalValue:
    name: str
    quantity: Q

    @property
    def value(self) -> float:
        return self.quantity.magnitude
    
    @property
    def unit(self):
        return self.quantity.units
    
    def set(self, value, unit_str=None):
        """
        Set the value and optionally the unit.
        If unit_str is provided, it will convert the value to that unit.
        """
        if unit_str:
            self.quantity = qty(value, unit_str)
        else:
            self.quantity = qty(value, self.unit)
    
    def __str__(self) -> str:
        """
        String representation of the physical value.
        """
        return f"{self.name}: {self.quantity:.~P}"