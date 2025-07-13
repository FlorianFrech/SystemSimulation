# physical_value.py

import numpy as np
import re
from collections import defaultdict
from pint import UnitRegistry
from pint.errors import UndefinedUnitError


ureg = UnitRegistry()

# ------------------------------------------
# Unit normalization (e.g. "kilogram" → "kg")
# ------------------------------------------
def normalize_unit_string(unit_str):
    replacements = {
        "kilogram": "kg",
        "meter": "m",
        "second": "s",
        "ampere": "A",
        "kelvin": "K",
        "mole": "mol",
        "candela": "cd"
    }
    for long, short in replacements.items():
        unit_str = unit_str.replace(long, short)
    unit_str = unit_str.replace(" ** ", "^").replace(" * ", "*").replace(" / ", "/")
    return unit_str

# ---------------------------------------------------------------------------------
# One-time unit + value conversion to base SI using pint (e.g. "J" → "kg*m^2/s^2")
# ---------------------------------------------------------------------------------
def convert_to_si(value, unit_str):
    """
    Converts a value and unit string to base SI units using Pint.
    Returns: (numeric_value, normalized_unit_str)

    Raises ValueError if the unit string is not recognized by Pint.
    """
    try:
        q = value * ureg(unit_str)
        base = q.to_base_units()
        norm_unit = normalize_unit_string(str(base.units))
        return base.magnitude, norm_unit
    except UndefinedUnitError as e:
        raise ValueError(
            f"Unit '{unit_str}' is not recognized. "
            f"Please use a valid unit string (e.g. 'V', 'ohm', 'F', 's'). "
            f"For full list, see pint_units.txt in main project's folder."
        )

# -----------------------------
# Core Unit math and comparison
# -----------------------------
class Unit:
    """Handles parsing and math for physical units."""

    def __init__(self, unit_str=None):
        self.original = unit_str
        self.units = self._parse_unit(unit_str) if unit_str else {}

    def _parse_unit(self, s):
        """Parses 'kg*m^2/s^2' into {'kg': 1, 'm': 2, 's': -2}."""
        units = defaultdict(int)
        if not s:
            return units

        parts = s.split('/')
        numerator = parts[0]
        denominators = parts[1:]  # allow multiple divisions, rare but possible

        def process(subs, sign):
            tokens = re.findall(r'([a-zA-Z]+)(\^-?\d+)?', subs)
            for base, power in tokens:
                p = int(power[1:]) if power else 1
                # power[0] = "^", power[1] = "+" or "-"
                units[base] += sign * p

        process(numerator, +1)
        for denom in denominators:
            # loop if there are multiple divisions
            process(denom, -1)

        return dict(units)
    
    
    def __add__(self, other):
        if not isinstance(other, Unit):
            return NotImplemented
        if self.units != other.units:
            raise ValueError(f"Cannot add units {self} and {other} — units must match exactly.")
        return Unit(str(self))  # return unchanged unit, addition just confirms compatibility

    def __sub__(self, other):
        if not isinstance(other, Unit):
            return NotImplemented
        if self.units != other.units:
            raise ValueError(f"Cannot subtract units {self} and {other} — units must match exactly.")
        return Unit(str(self))
    
    def __mul__(self, other):
        result = defaultdict(int, self.units)
        for k, v in other.units.items():
            result[k] += v
        return Unit.from_dict(result)

    def __truediv__(self, other):
        result = defaultdict(int, self.units)
        for k, v in other.units.items():
            result[k] -= v
        return Unit.from_dict(result)

    def __pow__(self, exponent):
        result = {k: v * exponent for k, v in self.units.items()}
        return Unit.from_dict(result)

    def is_compatible_with(self, other):
        return self.units == other.units

    def __repr__(self):
        return self.original or "unitless"

    @classmethod
    def from_dict(cls, d):
        s = "*".join([f"{k}^{v}" if v != 1 else k for k, v in d.items() if v != 0])
        return cls(s if s else None)

# -----------------------------
# PhysicalValue: name + unit + value
# -----------------------------
class PhysicalValue:
    """
    Represents a physical quantity (e.g. input, output, parameter).
    Value can be scalar or vector. Unit is always normalized.
    """

    def __init__(self, name, value=None, unit=None):
        """
        Parameters:
            name: str — identifier of the variable
            value: float, list, or None — numeric value or placeholder
            unit: str or None — will be normalized via Unit class
        """
        self.name = name
        self.value = self._to_array_if_vector(value)
        self.unit = unit if isinstance(unit, Unit) else Unit(unit)
        
        # attributes to save original value and unit in case normalisation was applied: 10000.0, "kg*m^2/s^2" → 10, "kJ"
        self.original_value = self._to_array_if_vector(value)
        self.original_unit = unit if isinstance(unit, Unit) else Unit(unit)


    def _to_array_if_vector(self, v):
        if v is None:
            return None
        elif isinstance(v, list):
            return np.array(v)
        return v

    def set_value(self, value):
        self.value = self._to_array_if_vector(value)

    def get_value(self):
        return self.value
    
    def set_unit(self, unit):
        self.unit = Unit(unit)

    def get_unit(self):
        return self.unit

    def __repr__(self):
        val_str = f"{self.value}" if self.value is not None else "None"
        return f"{self.name}: {val_str} [{self.unit}]"


# val, unit = convert_to_si(10, "kJ")  # → 10000.0, "kg*m^2/s^2"
# pv = PhysicalValue("energy", val, unit)
# print(pv)  # energy: 10000.0 [kg*m^2/s^2]