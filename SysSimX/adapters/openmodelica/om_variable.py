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

def _fmt_attr(name: str, value) -> str:
    """Render a single Modelica attribute as name=value with correct syntax."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return f"{name}={'true' if value else 'false'}"
    if isinstance(value, (int, float)):
        return f"{name}={value}"
    return f'{name}={value}' if str(value).startswith("StateSelect.") else f'{name}="{value}"'

def _comma_join(items: Iterable[str]) -> str:
    items = [i for i in items if i]  # drop empties
    return ", ".join(items)

#--------------------------------------------------------
# Variable Class

@dataclass
class Variable:
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
                _fmt_attr("quantity", self.quantity),
                _fmt_attr("start", self.start),
                _fmt_attr("fixed", self.fixed) if self.fixed is not None else "",
                _fmt_attr("min", self.min),
                _fmt_attr("max", self.max),
                _fmt_attr("unit", self.unit) if self.unit not in (None, "") else "",
                _fmt_attr("displayUnit", self.display_unit),
                _fmt_attr("nominal", self.nominal),
            ]
        elif self.vtype == BaseType.INTEGER:
            attrs += [
                _fmt_attr("quantity", self.quantity),
                _fmt_attr("start", self.start),
                _fmt_attr("fixed", self.fixed),
                _fmt_attr("min", self.min),
                _fmt_attr("max", self.max),
            ]
        elif self.vtype == BaseType.BOOLEAN:
            attrs += [
                _fmt_attr("quantity", self.quantity),
                _fmt_attr("start", self.start),
                _fmt_attr("fixed", self.fixed),
            ]
        elif self.vtype == BaseType.STRING:
            attrs += [
                _fmt_attr("quantity", self.quantity),
                _fmt_attr("start", self.start),
            ]
        s = _comma_join(attrs)
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
