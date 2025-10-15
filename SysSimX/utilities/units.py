# units.py
# --------------------------------------------------------------------------
from pint import UnitRegistry
import re

ureg = UnitRegistry()
ureg.formatter.default_format = "~P"
ureg.autoconvert_offset_to_baseunit = True
Quantity = ureg.Quantity

def fix_exponent(unit_str: str) -> str:
    """
    FMU unit strings may be in the form "s-2" and are not recognized by pint.
    Adds "^" between any character and a number to allow parsing by pint.
    """
    fixed_str = re.sub(r'([a-zA-Z])(-?\d+)', r'\1^\2', unit_str)
    return fixed_str


def to_pint_unit(unit_str: str):
    """
    Convert a unit string to a pint Unit object.
    
    :param unit_str: The unit string to convert.
    :return: A pint Unit object.
    """
    if not unit_str:
        return ureg.dimensionless
    try:
        unit_str = fix_exponent(unit_str)
        return ureg.Unit(unit_str)
    except Exception as e:
        raise ValueError(f"Invalid unit string '{unit_str}': {e}")