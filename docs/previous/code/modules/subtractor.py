from core.module import common
from core.physical_value import PhysicalValue
import numpy as np

MODULE_INPUTS = [PhysicalValue("u_in_p", None, ""),
                 PhysicalValue("u_in_n", None, "")]


MODULE_OUTPUTS = [PhysicalValue("u_out", unit="")]

@common(outputs=["difference"])
def signal_generator(t, dt, u_in_p, u_in_n):
    return u_in_p - u_in_n
