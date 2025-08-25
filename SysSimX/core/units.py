# units.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Tuple, Union
import numpy as np
import pint

# --------------------------------------------------------------------------
# One global unit registry
_ureg = pint.UnitRegistry(autoconvert_offset_to_baseunit=True)
parse_unit = _ureg.Unit
Q = _ureg.Quantity

# Set default printing to abbreviated units
_ureg.formatter.default_format = "~P"

# --------------------------------------------------------------------------
# Constructor for pint quantity and unit
def qty(value: Union[float, int, np.ndarray, Iterable[float]], unit: str) -> pint.Quantity:
    return np.asarray(value) * _ureg(unit)

def parse_unit(unit_str: str) -> pint.Unit:
    return _ureg.parse_units(unit_str)

# --------------------------------------------------------------------------
# Dimensional analysis and compatibility
def have_same_dimensions(q1: pint.Quantity, q2: pint.Quantity) -> bool:
    """
    Check if two quantities have the same dimensions.
    """
    return q1.dimensionality == q2.dimensionality

def assert_compatible(*quantities: pint.Quantity) -> None:
    """
    Assert that all quantities are compatible (same dimensions).
    Raises ValueError if not compatible.
    """
    if not all(have_same_dimensions(q, quantities[0]) for q in quantities):
        raise ValueError("Quantities are not compatible: " + ", ".join(str(q) for q in quantities))
    


        
