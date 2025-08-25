from typing import Any, Optional
from enum import Enum

from math import pi as _pi

class Expression:
    def to_mo(self): raise NotImplementedError
    def __add__(self, other): return BinaryOperator('+', self, as_expr(other))
    def __radd__(self, other): return BinaryOperator('+', as_expr(other), self)
    def __sub__(self, other): return BinaryOperator('-', self, as_expr(other))
    def __rsub__(self, other): return BinaryOperator('-', as_expr(other), self)
    def __mul__(self, other): return BinaryOperator('*', self, as_expr(other))
    def __rmul__(self, other): return BinaryOperator('*', as_expr(other), self)
    def __truediv__(self, other): return BinaryOperator('/', self, as_expr(other))
    def __rtruediv__(self, other): return BinaryOperator('/', as_expr(other), self)
    def __pow__(self, other): return BinaryOperator('^', self, as_expr(other))

class Literal(Expression):
    def __init__(self, value): self.value = value
    def to_mo(self):
        # ensure floats always use '.' for Modelica
        return repr(float(self.value)) if isinstance(self.value,(int,float)) else str(self.value)

class Symbol(Expression):
    def __init__(self, name): self.name = name
    def to_mo(self): return self.name

class BinaryOperator(Expression):
    def __init__(self, op, l, r): self.op, self.l, self.r = op, l, r
    def to_mo(self):
        # Modelica power is ^ ; enforce parentheses to be safe
        return f"({self.l.to_mo()} {self.op} {self.r.to_mo()})"

class FunctionCall(Expression):
    def __init__(self, function, *args): self.function, self.args = function, args
    def to_mo(self):
        arg_str = ", ".join(a.to_mo() for a in self.args)
        return f"{self.function}({arg_str})"

def as_expr(x):
    return x if isinstance(x, Expression) else Literal(x)

