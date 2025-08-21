# modules/lpf_test.py

from core.module import differential, algebraic
from core.physical_value import PhysicalValue

MODULE_INPUTS = [PhysicalValue("Uin", unit="V")]
MODULE_OUTPUTS = [PhysicalValue("Uc", unit="V")]

PARAMETERS = [
    PhysicalValue("R", 1000, "ohm"),
    PhysicalValue("C", 1e-6, "F")
]

INITIAL_VALUES = [
    PhysicalValue("Uc", 0.0, "V")
]

@differential(outputs=["Uc"])
def dUc(t, dt, Uin, Uc, R, C):
    return (Uin - Uc) / (R * C)