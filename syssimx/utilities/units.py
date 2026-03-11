"""Utilities for handling physical units using Pint.

This module provides functions and types for working with physical units
and quantities using the Pint library. It includes functionality to parse
unit strings commonly found in FMU models and convert them to Pint units.

Classes:
    - QuantityType: Type alias for Pint Quantity.
    - QuantityClass: The Pint Quantity class.

Functions:
    - to_pint_unit(unit_str: str) -> Unit: Convert a unit string to a Pint Unit object.
    - fix_exponent(unit_str: str) -> str: Fix unit strings with exponents for Pint parsing.
"""

import re
from typing import TypeAlias

from pint import Quantity as PintQuantity
from pint import Unit as PintUnit
from pint import UnitRegistry

ureg: UnitRegistry = UnitRegistry()
ureg.formatter.default_format = "~P"
ureg.autoconvert_offset_to_baseunit = True
ureg.case_sensitive = True

# FMUs sometimes use capitalized unit names like "Ohm". Pint defines
# "ohm" by default, but with case-sensitive parsing enabled we need
# explicit aliases for these variants.
try:
    ureg.define("Ohm = ohm")
except Exception:
    # If already defined (e.g., during reloads), ignore.
    pass

Unit = ureg.Unit
"""Unit of the default Pint UnitRegistry."""
UnitType: TypeAlias = PintUnit
"""The Pint Unit class."""
UnitClass: type[PintUnit] = PintUnit
"""The Pint Unit class."""

Quantity = ureg.Quantity
"""Quantity of the default Pint UnitRegistry."""
QuantityType: TypeAlias = PintQuantity
"""The Pint Quantity class."""
QuantityClass: type[PintQuantity] = PintQuantity
"""The Pint Quantity class."""


def fix_exponent(unit_str: str) -> str:
    """Fixes exponent notation in unit strings for Pint parsing.

    FMU unit strings may be in the form "s-2" or "s2" and are not recognized by pint.
    Adds "^" between any character and a number to allow parsing by pint.

    Args:
        unit_str: The unit string to fix.
    """
    fixed_str = re.sub(r"([a-zA-Z])(-?\d+)", r"\1^\2", unit_str)
    return fixed_str


def to_pint_unit(unit_str: str | PintUnit | None):
    """Convert a unit string to a Pint Unit object.
    Args:
        unit_str: The unit string to convert.
    Returns:
        Pint Unit object corresponding to the input string.
    """
    if unit_str is None or unit_str == "":
        return ureg.dimensionless
    if isinstance(unit_str, PintUnit):
        if unit_str._REGISTRY is not ureg:
            raise ValueError("Unit is not from the framework UnitRegistry")
        return unit_str
    try:
        unit_str = fix_exponent(unit_str)
        return ureg.Unit(unit_str)
    except Exception as e:
        raise ValueError(f"Invalid unit string '{unit_str}': {e}")
