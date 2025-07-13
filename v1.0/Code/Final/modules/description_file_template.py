from module import algebraic, differential, internal, common
from physical_value import PhysicalValue


MODULE_INPUTS = [PhysicalValue("", unit="")]

MODULE_OUTPUTS = [
    PhysicalValue("", unit=""),
    PhysicalValue("", unit=""),
]

PARAMETERS = [
    PhysicalValue("", 0.0, ""),
    PhysicalValue("", 0.0, ""),
    PhysicalValue("", 0.0, ""),
]

INITIAL_VALUES = [
    PhysicalValue("", 0.0, "")
]

INTERNAL_INITIAL_VALUES = [
    PhysicalValue("", 0.0, ""),
    PhysicalValue("", 0.0, "")
]


# functions always have t, dt as arguments (in that order); regardless weather they use them or not
@internal(outputs=["", ""])
def func1(t, dt):
    pass

@algebraic(outputs=[""])
def func2(t, dt):
    pass

@differential(outputs=[""])
def func3(t, dt):
    pass

@common(outputs=[""])
def func4(t, dt):
    pass