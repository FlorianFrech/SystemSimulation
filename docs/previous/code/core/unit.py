# Unit Definition
import pint
import re
from typing import Union, Dict, Any, Optional, Tuple
from dataclasses import dataclass

# ---------------------------------------------------------------------------------
# Global variables and utility functions
# ---------------------------------------------------------------------------------
ureg = pint.UnitRegistry()
Q_ = ureg.Quantity

# Global utility functions
def abbreviate_si_unit(unit_str: str) -> str:
    """
    Replaces long-form SI unit names with their standard abbreviations.
    Example: "kilogram" → "kg", "meter" → "m".
    """
    si_unit_dict = {
        r"\bkilogram\b": "kg",
        r"\bmeter\b": "m",
        r"\bsecond\b": "s",
        r"\bampere\b": "A",
        r"\bkelvin\b": "K",
        r"\bmole\b": "mol",
        r"\bcandela\b": "cd"
    }

    for pattern, abbreviation in si_unit_dict.items():
        unit_str = re.sub(pattern, abbreviation, unit_str)
    return unit_str

def normalize_unit_string(unit_str: str) -> str:
    """
    Replaces long-form SI unit names with their standard abbreviations and formats the string.
    """
    unit_str = abbreviate_si_unit(unit_str)
    unit_str = re.sub(r"\s*\*\*\s*", "^", unit_str)  # exponentiation
    unit_str = re.sub(r"\s*\*\s*", "*", unit_str)    # multiplication
    unit_str = re.sub(r"\s*/\s*", "/", unit_str)     # division
    return unit_str

def convert_to_si(value: float, unit_str: str) -> Tuple[float, str]:
    """
    Converts a value and unit string to base SI units using Pint.
    Example: (100, "cm") → (1.0, "m")

    Args:
        value: Numeric value to convert.
        unit_str: String representation of the unit (e.g. "V", "ohm", "F", "s").
    
    Returns:
        Tuple of (numeric_value, normalized_unit_str) if successful.
    
    Raises:
        ValueError: If the unit string is not recognized by Pint.
    """
    # Input validation
    if not isinstance(value, (int, float)):
        raise TypeError(f"Expected numeric value, got {type(value)}")
    
    if not isinstance(unit_str, str):
        raise TypeError(f"Expected string for unit, got {type(unit_str)}")
    
    if not unit_str.strip():
        # Hanldle empty unit string as dimensionless
        return value, ""
    
    try:
        quantity = value * ureg(unit_str)
        base_quantity = quantity.to_base_units()
        normalized_unit = normalize_unit_string(str(base_quantity.units))
        return base_quantity.magnitude, normalized_unit
    except pint.errors.UndefinedUnitError as e:
        raise ValueError(
            f"Unit '{unit_str}' is not recognized. "
            "Please use a valid unit string (e.g. 'V', 'ohm', 'F', 's'). "
            "For full list, see pint_units.txt in main project's folder."
        ) 

# ---------------------------------------------------------------------------------
# Unit class definition
# ---------------------------------------------------------------------------------

@dataclass(frozen=True)
class Unit:
    """
    Immutable unit class that wraps Pint functionality with enhanced features.
    
    Handles parsing, validation, and mathematical operations on physical units
    Maintains both the original representation and the normalized form.
    """
    
    _unit_str: Optional[str] = None
    _pint_unit: Optional[pint.Unit] = None
    
    def __post_init__(self):
        """Initialize the Unit object after dataclass creation."""
        if self._unit_str is not None and self._pint_unit is not None:
            return  # Both provided, assume valid
        
        if self._unit_str is not None:
            # Create from string
            try:
                pint_unit = ureg.parse_expression(self._unit_str).units
                object.__setattr__(self, '_pint_unit', pint_unit)
            except Exception as e:
                raise ValueError(f"Invalid unit string '{self._unit_str}': {e}")
        elif self._pint_unit is not None:
            # Create from Pint unit
            object.__setattr__(self, '_unit_str', str(self._pint_unit))
        else:
            # Dimensionless unit
            object.__setattr__(self, '_pint_unit', ureg.dimensionless)
            object.__setattr__(self, '_unit_str', '')

    @classmethod
    def from_string(cls, unit_str: str) -> 'Unit':
        """Create Unit from string representation."""
        if not isinstance(unit_str, str):
            raise TypeError(f"Expected string, got {type(unit_str)}")
        return cls(_unit_str=unit_str.strip())
    
    @classmethod
    def from_pint(cls, pint_unit: pint.Unit) -> 'Unit':
        """Create Unit from Pint Unit object."""
        if not isinstance(pint_unit, pint.Unit):
            raise TypeError(f"Expected pint.Unit, got {type(pint_unit)}")
        return cls(_pint_unit=pint_unit)
    
    @classmethod
    def dimensionless(cls) -> 'Unit':
        """Create a dimensionless unit."""
        return cls()
    
    @property
    def original_string(self) -> str:
        """Return the original unit string."""
        return self._unit_str or ''
    
    @property
    def pint_unit(self) -> pint.Unit:
        """Return the underlying Pint unit."""
        return self._pint_unit
    
    @property
    def dimensionality(self) -> pint.util.UnitsContainer:
        """Return the dimensionality of this unit."""
        return self._pint_unit.dimensionality
    
    @property
    def is_dimensionless(self) -> bool:
        """Check if this is a dimensionless unit."""
        return self._pint_unit.dimensionality == Q_(1).dimensionality
    
    def to_base_units(self) -> 'Unit':
        """Convert to base SI units."""
        try:
            base_units = (1 * self._pint_unit).to_base_units().units
            return Unit.from_pint(base_units)
        except Exception as e:
            raise ValueError(f"Cannot convert to base units: {e}")
        
    def to_reduced_units(self) -> 'Unit':
        """Convert to reduced form (cancel out equivalent units)."""
        try:
            reduced = (1 * self._pint_unit).to_reduced_units().units
            return Unit.from_pint(reduced)
        except Exception as e:
            raise ValueError(f"Cannot reduce units: {e}")
    
    def is_compatible_with(self, other: 'Unit') -> bool:
        """Check if units are dimensionally compatible."""
        if not isinstance(other, Unit):
            return False
        return self.dimensionality == other.dimensionality
    
    def conversion_factor_to(self, other: 'Unit') -> float:
        """Get conversion factor from this unit to another compatible unit."""
        if not self.is_compatible_with(other):
            raise ValueError(f"Units {self} and {other} are not compatible")
        
        try:
            factor = (1 * self._pint_unit).to(other._pint_unit).magnitude
            return factor
        except Exception as e:
            raise ValueError(f"Cannot get conversion factor: {e}")

    # Arithmetic operations
    def __mul__(self, other: 'Unit') -> 'Unit':
        """Multiply units."""
        if not isinstance(other, Unit):
            return NotImplemented
        result_unit = self._pint_unit * other._pint_unit
        return Unit.from_pint(result_unit)
    
    def __truediv__(self, other: 'Unit') -> 'Unit':
        """Divide units."""
        if not isinstance(other, Unit):
            return NotImplemented
        result_unit = self._pint_unit / other._pint_unit
        return Unit.from_pint(result_unit)
    
    def __pow__(self, exponent: Union[int, float]) -> 'Unit':
        """Raise unit to a power."""
        if not isinstance(exponent, (int, float)):
            return NotImplemented
        result_unit = self._pint_unit ** exponent
        return Unit.from_pint(result_unit)
    
    def __rtruediv__(self, other) -> 'Unit':
        """Right division (1/unit)."""
        if other == 1:
            return Unit.from_pint(self._pint_unit ** -1)
        return NotImplemented
    
    # Comparison operations
    def __eq__(self, other: object) -> bool:
        """Check equality of units."""
        if not isinstance(other, Unit):
            return False
        return self.dimensionality == other.dimensionality
    
    def __hash__(self) -> int:
        """Hash based on dimensionality for use in sets/dicts."""
        return hash(tuple(sorted(self.dimensionality.items())))
    
    # String representations
    def __str__(self) -> str:
        """Return a clean string representation."""
        if self.is_dimensionless:
            return "dimensionless"
        return str(self._pint_unit)
    
    def __repr__(self) -> str:
        """Return detailed representation for debugging."""
        return f"Unit('{self._unit_str}' -> {self._pint_unit})"
    
    def format(self, spec: str = '~') -> str:
        """
        Format unit with various options.
        
        Args:
            spec: Format specification
                '~' - short form (default)
                'P' - pretty format
                'C' - compact format
                'L' - LaTeX format
                'H' - HTML format
        """
        return f"{self._pint_unit:{spec}}"
    
    # Validation methods
    @staticmethod
    def is_valid_unit_string(unit_str: str) -> bool:
        """Check if a string represents a valid unit."""
        try:
            ureg.parse_expression(unit_str)
            return True
        except:
            return False
    
    @staticmethod
    def parse_compound_unit(unit_str: str) -> Dict[str, float]:
        """
        Parse a compound unit string into its constituent parts.
        
        Returns:
            Dictionary mapping base units to their powers
        """
        try:
            unit = ureg.parse_expression(unit_str).units
            return dict(unit.dimensionality)
        except Exception as e:
            raise ValueError(f"Cannot parse unit string '{unit_str}': {e}")
    
    # Utility methods
    def get_compatible_units(self) -> list:
        """Get a list of compatible units from the registry."""
        compatible = []
        for name, unit_def in ureg._units.items():
            try:
                test_unit = getattr(ureg, name)
                if self.is_compatible_with(Unit.from_pint(test_unit.units)):
                    compatible.append(name)
            except:
                continue
        return compatible
    
    def simplify(self) -> 'Unit':
        """Simplify the unit representation."""
        try:
            simplified = (1 * self._pint_unit).to_compact().units
            return Unit.from_pint(simplified)
        except:
            return self

# Convenience functions
def unit(unit_str: str) -> Unit:
    """Quick constructor for Unit from string."""
    return Unit.from_string(unit_str)

def dimensionless() -> Unit:
    """Create a dimensionless unit."""
    return Unit.dimensionless()

# Common unit constants
METER = Unit.from_string("m")
KILOGRAM = Unit.from_string("kg")
SECOND = Unit.from_string("s")
AMPERE = Unit.from_string("A")
KELVIN = Unit.from_string("K")
MOLE = Unit.from_string("mol")
CANDELA = Unit.from_string("cd")

# Derived units
NEWTON = Unit.from_string("N")
JOULE = Unit.from_string("J")
WATT = Unit.from_string("W")
VOLT = Unit.from_string("V")
OHM = Unit.from_string("ohm")
FARAD = Unit.from_string("F")
HENRY = Unit.from_string("H")