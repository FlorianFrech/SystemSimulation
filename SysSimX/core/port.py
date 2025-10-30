from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Generic, Optional, TypeVar, Literal, Union
from ..utilities.units import ureg, Quantity


class PortType(str, Enum):
    REAL = "real"
    INT = "int"
    BOOL = "bool"
    STRING = "string"

Direction = Literal['in', 'out']
T = TypeVar('T', float, int, bool, str) # types from fmpy.model_description.read_model_description

@dataclass(frozen=True)
class PortSpec(Generic[T]):
    """
    Specification of a port in a CoSimComponent (unmutable).
    Defines the name, type, direction, optional unit, and description of the port.
    """
    name: str
    type: PortType
    direction: Direction
    unit: Optional[str] = None
    description: Optional[str] = None

    def validate_value(self, value: Any) -> None:
        """
        Validate that the given value matches the port's type and unit (if applicable).
        """
        # Unit presence only allowed for REAL ports
        if self.type != PortType.REAL and self.unit is not None:
            raise ValueError(f"{self.name}: Only REAL ports can have units, got {self.type} with unit {self.unit}")
        
        # Data Type Checks
        if self.type == PortType.REAL:
            if not isinstance(value, (float, int, Quantity)):
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
        if self.type == PortType.REAL and self.unit and isinstance(value, Quantity):
            _ = value.to(self.unit) # Raises if incompatible
    
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

@dataclass
class PortState(Generic[T]):
    """
    State of a port in a CoSimComponent (mutable).
    Holds the specification, current value, last update time, and history of values.
    """
    spec: PortSpec[T]
    value: Optional[Union[T, Quantity]] = None
    t_last: Optional[float] = None
    history: list[tuple[float, Union[T, Quantity]]] = field(default_factory=list) # (time, value)

    # TODO:
    # Add sample time and variablility (continuous / discrete / parameter) to support event handling

    def set(self, value: Union[T, Quantity], t: Optional[float] = None) -> None:
        """
        Set the port's value, validating against its specification.
        """
        self.spec.validate_value(value)
        if self.spec.type == PortType.REAL:
            if isinstance(value, Quantity):
                vq = value if self.spec.unit is None else value.to(self.spec.unit)
            else:
                vq = value if self.spec.unit is None else (value * ureg(str(self.spec.unit)))
            self.value = vq
        else:
            self.value = value # INT, BOOL, STRING
        if t is not None:
            self.t_last = t
            self.history.append((t, self.value))

    def get(self, as_unit: Optional[str] = None) -> Union[T, Quantity, None]:
        """
        Get the current value of the port.
        """
        if self.value is None:
            return None
        if self.spec.type == PortType.REAL and as_unit:
            if isinstance(self.value, Quantity):
                return self.value.to(as_unit)
            return (self.value * ureg(self.spec.unit)).to(as_unit) if self.spec.unit else self.value
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