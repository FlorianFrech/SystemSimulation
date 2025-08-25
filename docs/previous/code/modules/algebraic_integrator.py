from core.module import algebraic, differential, internal, common
from core.physical_value import PhysicalValue


MODULE_INPUTS = [PhysicalValue("u", unit="")]

MODULE_OUTPUTS = [
    PhysicalValue("x", unit="")
    ]

PARAMETERS = []

INITIAL_VALUES = [
    PhysicalValue("x", 0.0, "")
    ]


@differential(outputs=["x"])
def differential_part(t, dt, x):
    """
    dx/dt = (1 - x) / 2
    """
    return (1 - x) / 2
