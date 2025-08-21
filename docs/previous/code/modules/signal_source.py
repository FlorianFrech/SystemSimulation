from core.module import common
from core.physical_value import PhysicalValue
import numpy as np

MODULE_INPUTS = []
MODULE_OUTPUTS = [PhysicalValue("Uin", unit="V")]

PARAMETERS = [
    PhysicalValue("A1", 60, "V"),
    PhysicalValue("A2", 5, "V"),
    PhysicalValue("f1", 0.159, "1/s"),     # Hz
    PhysicalValue("f2", 7.96, "1/s"),
]

@common(outputs=["Uin"])
def signal_generator(t, dt, A1, A2, f1, f2):
    s1 = A1 * np.sin(2 * np.pi * f1 * t)
    s2 = A2 * np.sin(2 * np.pi * f2 * t)
    return s1 + s2
