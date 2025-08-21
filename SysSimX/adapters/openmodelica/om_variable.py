from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Union, Iterable, Dict

#--------------------------------------------------------
# Variability and Type

class Variability(str, Enum):
    CONTINUOUS = "continuous" # default for state/derived variables
    PARAMETER  = "parameter"
    CONSTANT   = "constant"
    DISCRETE   = "discrete"

class BaseType(str, Enum):
    REAL    = "Real"
    INTEGER = "Integer"
    BOOLEAN = "Boolean"
    STRING  = "String"

#--------------------------------------------------------
# Utilities

def _build_attr_string(name: str, value) -> str:
    """Render a single Modelica attribute as name=value with correct syntax."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return f"{name}={'true' if value else 'false'}"
    if isinstance(value, (int, float)):
        return f"{name}={value}"
    return f'{name}={value}' if str(value).startswith("StateSelect.") else f'{name}="{value}"'

def _format_attributes_with_comma(attributes: Iterable[str]) -> str:
    attributes = [i for i in attributes if i]  # drop empties
    return ", ".join(attributes)

#--------------------------------------------------------
# Variable Class

@dataclass
class Variable:
    """Represents a Modelica variable with attributes and methods to generate its declaration.
    Attributes:
        name: Name of the variable.
        vtype: BaseType of the variable (e.g., Real, Integer).
        variability: Variability of the variable (e.g., Continuous, Parameter).
        quantity: Optional physical quantity associated with the variable.
        start: Optional initial value for the variable.
        fixed: Optional flag indicating if the variable is fixed.
        unit: Optional unit of the variable.
        display_unit: Optional display unit for the variable.
        nominal: Optional nominal value for the variable.
        min: Optional minimum value for the variable.
        max: Optional maximum value for the variable.
        value: Optional value for parameters, constants, or discrete variables.
        comment: Optional documentation comment for the variable.
    """
    name: str
    vtype: BaseType.REAL
    variability: Variability = Variability.CONTINUOUS

    # Optional attributes
    quantity: Optional[str] = None
    start: Optional[Union[int, float, str, bool]] = None 
    fixed: Optional[bool] = None
    unit: Optional[str] = None           
    display_unit: Optional[str] = None   
    nominal: Optional[float] = None     
    min: Optional[Union[int, float]] = None     
    max: Optional[Union[int, float]] = None

    # Value for parameters, constant, or discrete variables
    value: Optional[Union[int, float, str, bool]] = None

    # Documentation commment
    comment: Optional[str] = None

    def _validate(self):
        # Attribute legality per type
        if self.vtype != BaseType.REAL:
            illegal_real_attrs = [
                ("unit", self.unit),
                ("displayUnit", self.display_unit),
                ("nominal", self.nominal),
            ]
            for n, v in illegal_real_attrs:
                if v is not None:
                    raise ValueError(f"{n} is only valid for Real variables: {self.name}")
        if self.vtype not in (BaseType.REAL, BaseType.INTEGER):
            if self.min is not None or self.max is not None:
                raise ValueError(f"min/max are only valid for Real/Integer: {self.name}")

        # constant must have an explicit value (compile-time)
        if self.variability == Variability.CONSTANT and self.value is None:
            raise ValueError(f"constant '{self.name}' must have a value")

    def _attributes_modelica(self) -> str:
        """Return attribute list inside parentheses for the declaration."""
        attrs = []
        # Map Python field names to Modelica attribute identifiers
        if self.vtype == BaseType.REAL:
            attrs += [
                _build_attr_string("quantity", self.quantity),
                _build_attr_string("start", self.start),
                _build_attr_string("fixed", self.fixed) if self.fixed is not None else "",
                _build_attr_string("min", self.min),
                _build_attr_string("max", self.max),
                _build_attr_string("unit", self.unit) if self.unit not in (None, "") else "",
                _build_attr_string("displayUnit", self.display_unit),
                _build_attr_string("nominal", self.nominal),
            ]
        elif self.vtype == BaseType.INTEGER:
            attrs += [
                _build_attr_string("quantity", self.quantity),
                _build_attr_string("start", self.start),
                _build_attr_string("fixed", self.fixed),
                _build_attr_string("min", self.min),
                _build_attr_string("max", self.max),
            ]
        elif self.vtype == BaseType.BOOLEAN:
            attrs += [
                _build_attr_string("quantity", self.quantity),
                _build_attr_string("start", self.start),
                _build_attr_string("fixed", self.fixed),
            ]
        elif self.vtype == BaseType.STRING:
            attrs += [
                _build_attr_string("quantity", self.quantity),
                _build_attr_string("start", self.start),
            ]
        s = _format_attributes_with_comma(attrs)
        return f"({s})" if s else ""

    def _lhs_prefix(self) -> str:
        # Variability qualifier goes before the type, except continuous (omitted)
        qual = ""
        if self.variability == Variability.PARAMETER:
            qual = "parameter "
        elif self.variability == Variability.CONSTANT:
            qual = "constant "
        elif self.variability == Variability.DISCRETE:
            qual = "discrete "
        return qual + self.vtype.value

    def _rhs_value(self) -> str:
        if self.value is None:
            # Parameter without explicit value may take start as default at instantiation time.
            return ""
        if isinstance(self.value, bool):
            return f" = {'true' if self.value else 'false'}"
        if isinstance(self.value, str) and self.vtype == BaseType.STRING:
            return f' = "{self.value}"'
        return f" = {self.value}"

    def to_modelica_decl(self) -> str:
        """
        Emit a single Modelica declaration line, e.g.:
        parameter Real R(unit="ohm", start=1000, fixed=true) = 1000 "resistance";
        """
        self._validate()
        attrs = self._attributes_modelica()
        rhs = self._rhs_value()
        cmt = f' "{self.comment}"' if self.comment else ""
        return f"{self._lhs_prefix()} {self.name}{attrs}{rhs};{cmt}"# List of attributes for the variable       
