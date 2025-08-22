from math import pi as _pi

from .expressions import Expression, Literal, Symbol, FunctionCall, as_expr

# Math helpers (emit Modelica intrinsics)
def sin(x):  return FunctionCall("sin",  as_expr(x))
def cos(x):  return FunctionCall("cos",  as_expr(x))
def tan(x):  return FunctionCall("tan",  as_expr(x))
def exp(x):  return FunctionCall("exp",  as_expr(x))
def log(x):  return FunctionCall("log",  as_expr(x))
def sqrt(x): return FunctionCall("sqrt", as_expr(x))
def der(x):  return FunctionCall("der",  as_expr(x))

pi = Literal(_pi)              # numeric literal
time = Symbol("time")          # Modelica built-in time