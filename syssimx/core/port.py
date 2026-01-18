from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Literal, cast

from ..utilities.units import QuantityClass, QuantityType, ureg


# -------------------------------------------------------------------
# Port Types and Specifications - immutable port definitions
# -------------------------------------------------------------------
class PortType(str, Enum):
    REAL = "real"
    INT = "int"
    BOOL = "bool"
    STRING = "string"
    EVENT = "event"  # Special type for event ports (boolean)


Direction = Literal["in", "out"]
PortValue = float | int | bool | str | QuantityType


@dataclass(frozen=True)
class PortSpec:
    """
    Specification of a port in a CoSimComponent (unmutable).
    Defines the name, type, direction, optional unit, and description of the port.
    """

    name: str
    type: PortType
    direction: Direction
    unit: str | None = None
    description: str | None = None

    def validate_value(self, value: Any) -> None:
        """
        Validate that the given value matches the port's type and unit (if applicable).
        """
        # Unit presence only allowed for REAL ports
        if self.type != PortType.REAL and self.unit is not None:
            raise ValueError(
                f"{self.name}: Only REAL ports can have units, got {self.type} with unit {self.unit}"
            )

        # Data Type Checks
        if self.type == PortType.REAL:
            if not isinstance(value, (float, int, QuantityClass)):
                raise TypeError(f"{self.name}: REAL expects float/int/Quantity, got {type(value)}")
        elif self.type == PortType.BOOL:
            if not isinstance(value, bool):
                raise TypeError(f"{self.name}: BOOL expects bool, got {type(value)}")
        elif self.type == PortType.INT:
            if type(value) is not int:
                raise TypeError(f"{self.name}: INT expects int, got {type(value)}")
        elif self.type == PortType.STRING:
            if not isinstance(value, str):
                raise TypeError(f"{self.name}: STRING expects str, got {type(value)}")

        # Unit Checks for REAL ports
        if self.type == PortType.REAL and self.unit and isinstance(value, QuantityClass):
            _ = value.to(self.unit)  # Raises if incompatible

    @staticmethod
    def compatible(spec1: PortSpec, spec2: PortSpec) -> bool:
        """
        Check if two PortSpecs are compatible (same type and compatible units if REAL).
        """
        if spec1.type != spec2.type:
            return False
        if spec1.type == PortType.REAL and (spec1.unit or spec2.unit):
            try:
                (1 * ureg(str(spec1.unit))).to(str(spec2.unit))
            except Exception:
                return False
        return True


# -------------------------------------------------------------------
# Port State - mutable state of a port
# -------------------------------------------------------------------
@dataclass
class PortState:
    """
    State of a port in a CoSimComponent (mutable).
    Holds the specification, current value, last update time, and history of values.
    """

    spec: PortSpec
    value: PortValue | None = None
    t_last: float | None = None

    # TODO:
    # Add sample time and variablility (continuous / discrete / parameter) to support event handling

    def __post_init__(self):
        """Inititialize with type-appropriate default value if None."""
        if self.value is None:
            self.value = self._get_default_value()

    def _get_default_value(self) -> PortValue | None:
        """Get default value based on port type."""
        if self.spec.type == PortType.REAL:
            return 0.0 if self.spec.unit is None else 0.0 * ureg(str(self.spec.unit))
        elif self.spec.type == PortType.INT:
            return 0
        elif self.spec.type == PortType.BOOL:
            return False
        elif self.spec.type == PortType.STRING:
            return ""
        elif self.spec.type == PortType.EVENT:
            return False
        return None

    def set(self, value: PortValue, t: float | None = None) -> None:
        """
        Set the port's value, validating against its specification.
        """
        self.spec.validate_value(value)
        if self.spec.type == PortType.REAL:
            vq: QuantityType | float
            if isinstance(value, QuantityClass):
                vq = (
                    value
                    if self.spec.unit is None
                    else cast(QuantityType, value.to(self.spec.unit))
                )
            else:
                real_value = float(value)
                if self.spec.unit is None:
                    vq = real_value
                else:
                    vq = cast(QuantityType, (real_value * ureg(str(self.spec.unit))))
            self.value = vq
        else:
            self.value = value  # INT, BOOL, STRING
        if t is not None:
            self.t_last = t

    def get(self, as_unit: str | None = None) -> PortValue | None:
        """
        Get the current value of the port.
        """
        if self.value is None:
            return None
        if self.spec.type == PortType.REAL and as_unit:
            if isinstance(self.value, QuantityClass):
                return cast(QuantityType, self.value.to(as_unit))
            if self.spec.unit:
                return cast(
                    QuantityType,
                    (cast(float, self.value) * ureg(self.spec.unit)).to(as_unit),
                )
            return cast(float, self.value)
        return self.value

    def compatible_with(self, other: PortSpec) -> bool:
        """
        Check if this port's specification is compatible with another port's (other) specification.
        """
        if self.spec.type != other.type:
            return False
        if self.spec.type == PortType.REAL and self.spec.unit and other.unit:
            try:
                (0 * ureg(self.spec.unit)).to(other.unit)
            except Exception:
                return False
        return True
