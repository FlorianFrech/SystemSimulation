from core.module import algebraic, differential, internal
from core.physical_value import PhysicalValue


MODULE_INPUTS = [PhysicalValue("U", unit="V")]

MODULE_OUTPUTS = [
    PhysicalValue("I", unit="A"),
    PhysicalValue("IL", unit="A"),
]

PARAMETERS = [
    PhysicalValue("R", 100, "ohm"),
    PhysicalValue("L", 0.01, "H"),
    PhysicalValue("C", 1e-6, "F"),
]

INITIAL_VALUES = [
    PhysicalValue("IL", 0.0, "A")
]

INTERNAL_INITIAL_VALUES = [
    PhysicalValue("U_prev", 0.0, "V"),
    PhysicalValue("dU", 0.0, "V/s")
]

@internal(outputs=["U_prev", "dU"])
def update_du(t, dt, U, U_prev):
    dU = (U - U_prev) / dt
    return U, dU

@algebraic(outputs=["I"])
def compute_total_current(t, dt, U, IL, dU, R, C):
    return U / R + C * dU + IL

@differential(outputs=["IL"])
def dIL(t, dt, U, L):
    return U / L
