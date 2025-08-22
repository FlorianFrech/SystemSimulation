from typing import Any
from .expressions import Symbol

class Variable(Symbol):
    name: str
    type: Any
    unit: Any
    value: Any

    def __init__(self, name: str, type_: Any, unit: Any = None, value: Any = None):
        """Initialize the parameter with a name, type, unit, and value."""
        self.name = name
        self.type_ = type_
        self.unit = unit
        self.value = value
    
    def decl(self) -> str:
        """Return the Modelica declaration for this variable."""
        unit_str = f"unit=\"{self.unit}\"" if self.unit else ""
        value_str = f" = {self.value}" if self.value is not None else ""
        return f"{self.type_} {self.name}({unit_str}){value_str};"