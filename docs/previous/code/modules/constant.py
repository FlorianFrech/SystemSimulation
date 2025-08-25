from core.module import common
from core.physical_value import PhysicalValue

MODULE_OUTPUTS = [
    PhysicalValue("u_out", unit="")
]

PARAMETERS = [
    PhysicalValue("k", 1.0, "")
]

@common(outputs=["u_out"])
def output(t, dt, k):
    return 1 * k
