from core.module import common
from core.physical_value import PhysicalValue

MODULE_OUTPUTS = [
    PhysicalValue("u_out", unit="")
]

@common(outputs=["u_out"])
def output(t, dt):
    return 1
