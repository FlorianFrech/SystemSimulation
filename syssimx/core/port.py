"""Port specification and port state management for co-simulation components.

This module defines the PortType enum, PortSpec class for immutable port
specifications, and PortState class for mutable port state with type-safe
get/set operations including unit handling.

Overview of classes:
- PortType: Enum of supported port data types (REAL, INT, BOOL, STRING, EVENT)
- PortSpec: Immutable specification of a port (name, type, direction, unit, description)
- PortState: Mutable state of a port (spec, current value, last update time)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Literal, cast

import numpy as np

from ..utilities.units import (
    QuantityClass,
    QuantityType,
    UnitType,
    to_pint_unit,
    ureg,
)


# -------------------------------------------------------------------
# Port Types and Specifications - immutable port definitions
# -------------------------------------------------------------------
class PortType(StrEnum):
    """Supported port data types for co-simulation components.

    Attributes:
        REAL: Floating-point values, optionally with physical units.
        INT: Integer values.
        BOOL: Boolean values (True/False).
        STRING: String values.
        EVENT: Boolean trigger for discrete events.
    """

    REAL = "real"
    INT = "int"
    BOOL = "bool"
    STRING = "string"
    EVENT = "event"  # Boolean trigger for discrete events


Direction = Literal["in", "out"]
PortValue = float | int | bool | str | QuantityType


def _validate_unit(unit: str | UnitType | None, port_name: str) -> None:
    """Validate that a unit string or Unit is recognized by the framework registry."""
    if unit is None or unit == "":
        return
    try:
        _ = to_pint_unit(unit)
    except Exception as e:
        raise ValueError(f"Port '{port_name}': Invalid unit '{unit}': {e}") from e


def _coerce_numpy_scalar(value: Any) -> Any:
    """Convert numpy scalar types to Python native types.

    This allows seamless use of numpy arrays in port operations.
    Returns the original value if not a numpy scalar.
    """
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.bool_):
        return bool(value)
    return value


@dataclass(frozen=True)
class PortSpec:
    """
    Specification of a port in a CoSimComponent (immutable).

    Defines the name, type, direction, optional unit, and description of the port.
    Units are validated at construction time to catch errors early.

    Attributes:
        name: Unique identifier for the port within a component.
        type: Data type of the port (REAL, INT, BOOL, STRING, EVENT).
        direction: Whether this is an input ("in") or output ("out") port.
        unit: Physical unit string or Unit for REAL ports (e.g., "m/s", "N*m").
        description: Human-readable description of the port's purpose.
    """

    name: str
    type: PortType
    direction: Direction
    unit: str | UnitType | None = None
    description: str | None = None

    def __post_init__(self) -> None:
        """Validate port specification at construction time."""
        # Only REAL ports can have units
        if self.type != PortType.REAL and self.unit is not None:
            raise ValueError(
                f"Port '{self.name}': Only REAL ports can have units, "
                f"got {self.type.value.upper()} with unit '{self.unit}'"
            )
        # Validate unit string is recognized by pint
        _validate_unit(self.unit, self.name)

    def __str__(self) -> str:
        """Human-readable string representation."""
        unit_str = f" [{self.unit}]" if self.unit else ""
        return f"{self.name} ({self.type.value}, {self.direction}){unit_str}"

    def validate_value(self, value: Any, *, coerce_numpy: bool = True) -> Any:
        """
        Validate that the given value matches the port's type and unit.

        Args:
            value: The value to validate.
            coerce_numpy: If True, convert numpy scalars to Python native types.

        Returns:
            The (possibly coerced) value if valid.

        Raises:
            TypeError: If value type doesn't match port type.
            ValueError: If unit validation fails.
            DimensionalityError: If Quantity has incompatible dimensions.
        """
        if coerce_numpy:
            value = _coerce_numpy_scalar(value)

        # Type-specific validation
        if self.type == PortType.REAL:
            return self._validate_real(value)
        elif self.type == PortType.INT:
            return self._validate_int(value)
        elif self.type == PortType.BOOL:
            return self._validate_bool(value)
        elif self.type == PortType.STRING:
            return self._validate_string(value)
        elif self.type == PortType.EVENT:
            return self._validate_event(value)
        else:
            raise ValueError(f"Unknown port type: {self.type}")

    def _validate_real(self, value: Any) -> float | QuantityType:
        """Validate REAL port value."""
        if not isinstance(value, (float, int, QuantityClass)):
            raise TypeError(
                f"Port '{self.name}': REAL expects float, int, or Quantity, "
                f"got {type(value).__name__}"
            )
        # Unit compatibility check for Quantity
        if self.unit and isinstance(value, QuantityClass):
            _ = value.to(self.unit)  # Raises DimensionalityError if incompatible
        if isinstance(value, QuantityClass):
            return cast(QuantityType, value)
        return float(value)

    def _validate_int(self, value: Any) -> int:
        """Validate INT port value."""
        # Use 'type(value) is int' to reject bool (which is subclass of int)
        if type(value) is not int:
            raise TypeError(f"Port '{self.name}': INT expects int, got {type(value).__name__}")
        return value

    def _validate_bool(self, value: Any) -> bool:
        """Validate BOOL port value."""
        if not isinstance(value, bool):
            raise TypeError(f"Port '{self.name}': BOOL expects bool, got {type(value).__name__}")
        return value

    def _validate_string(self, value: Any) -> str:
        """Validate STRING port value."""
        if not isinstance(value, str):
            raise TypeError(f"Port '{self.name}': STRING expects str, got {type(value).__name__}")
        return value

    def _validate_event(self, value: Any) -> bool:
        """Validate EVENT port value (boolean trigger)."""
        if not isinstance(value, bool):
            raise TypeError(f"Port '{self.name}': EVENT expects bool, got {type(value).__name__}")
        return value

    @staticmethod
    def compatible(spec1: PortSpec, spec2: PortSpec) -> bool:
        """Check if two PortSpecs are compatible for connection.

        Compatibility rules:
        - Types must match exactly (REAL-REAL, INT-INT, etc.)
        - For REAL ports: both must have units, and units must be dimensionally compatible
        - For REAL ports: both having no unit is also compatible

        Args:
            spec1: Source port specification (typically output).
            spec2: Destination port specification (typically input).

        Returns:
            True if ports can be connected, False otherwise.
        """
        # Type must match exactly
        if spec1.type != spec2.type:
            return False

        # For non-REAL types, type match is sufficient
        if spec1.type != PortType.REAL:
            return True

        # REAL type: check unit compatibility
        return PortSpec._check_unit_compatibility(spec1.unit, spec2.unit)

    @staticmethod
    def _check_unit_compatibility(
        unit1: str | UnitType | None, unit2: str | UnitType | None
    ) -> bool:
        """Check if two unit specifications are compatible.

        Rules:
        - Both None: compatible (dimensionless)
        - One None, one has unit: incompatible (ambiguous)
        - Both have units: check dimensional compatibility
        """
        if unit1 is None and unit2 is None:
            return True
        if unit1 is None or unit2 is None:
            return False  # Asymmetric: one has unit, other doesn't
        try:
            u1 = to_pint_unit(unit1)
            u2 = to_pint_unit(unit2)
            (1 * u1).to(u2)
            return True
        except Exception:
            return False


# -------------------------------------------------------------------
# Port State - mutable state of a port
# -------------------------------------------------------------------
@dataclass
class PortState:
    """Mutable state of a port in a CoSimComponent.

    Holds the specification, current value, and last update time.
    Provides type-safe get/set operations with automatic unit conversion.

    Attributes:
        spec: Immutable specification defining port properties.
        value: Current value of the port.
        t_last: Simulation time of last value update.
    """

    spec: PortSpec
    value: PortValue | None = field(default=None)
    t_last: float | None = field(default=None)

    def __post_init__(self) -> None:
        """Initialize with type-appropriate default value if None."""
        if self.value is None:
            self.value = self._get_default_value()

    def __str__(self) -> str:
        """Human-readable string representation."""
        time_str = f" @ t={self.t_last}" if self.t_last is not None else ""
        return f"{self.spec.name} = {self.value}{time_str}"

    def _get_default_value(self) -> PortValue:
        """Get default value based on port type."""
        defaults: dict[PortType, PortValue] = {
            PortType.REAL: 0.0 if self.spec.unit is None else 0.0 * ureg(str(self.spec.unit)),
            PortType.INT: 0,
            PortType.BOOL: False,
            PortType.STRING: "",
            PortType.EVENT: False,
        }
        return defaults[self.spec.type]

    def set(self, value: PortValue, t: float | None = None) -> None:
        """Set the port's value with validation and unit conversion.

        Args:
            value: New value to set. For REAL ports with units, Quantities
                   are automatically converted to the port's unit.
            t: Simulation time of this update (optional).

        Raises:
            TypeError: If value type doesn't match port type.
            DimensionalityError: If Quantity has incompatible dimensions.
        """
        # Validate and potentially coerce numpy types
        validated_value = self.spec.validate_value(value, coerce_numpy=True)

        # Handle REAL port unit conversion
        if self.spec.type == PortType.REAL:
            self.value = self._convert_real_value(validated_value)
        else:
            self.value = validated_value

        if t is not None:
            self.t_last = t

    def _convert_real_value(self, value: float | int | QuantityType) -> float | QuantityType:
        """Convert and store REAL value with proper unit handling."""
        if isinstance(value, QuantityClass):
            if self.spec.unit is None:
                return cast(QuantityType, value)
            return cast(QuantityType, value.to(self.spec.unit))
        else:
            real_value = float(value)
            if self.spec.unit is None:
                return real_value
            return cast(QuantityType, real_value * ureg(str(self.spec.unit)))

    def get(self, as_unit: str | None = None) -> PortValue | None:
        """Get the current value of the port.

        Args:
            as_unit: For REAL ports, convert to this unit before returning.

        Returns:
            Current port value, possibly converted to requested unit.
        """
        if self.value is None:
            return None

        if self.spec.type == PortType.REAL and as_unit is not None:
            return self._get_with_unit_conversion(as_unit)

        return self.value

    def _get_with_unit_conversion(self, target_unit: str) -> PortValue:
        """Get REAL value converted to target unit."""
        if isinstance(self.value, QuantityClass):
            return cast(QuantityType, self.value.to(target_unit))
        if self.spec.unit is not None:
            unit = to_pint_unit(self.spec.unit)
            return cast(QuantityType, (cast(float, self.value) * unit).to(target_unit))
        # No unit on port, return raw value
        return cast(float, self.value)

    def compatible_with(self, other: PortSpec) -> bool:
        """Check if this port's state can connect to another port specification.

        Uses the same compatibility rules as PortSpec.compatible().

        Args:
            other: Target port specification to check compatibility with.

        Returns:
            True if connection is valid, False otherwise.
        """
        return PortSpec.compatible(self.spec, other)

    def reset(self) -> None:
        """Reset port to default value and clear timestamp."""
        self.value = self._get_default_value()
        self.t_last = None
