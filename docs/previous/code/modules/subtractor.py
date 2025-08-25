from core.module import common, internal
from core.physical_value import PhysicalValue
import numpy as np

MODULE_INPUTS = [PhysicalValue("u_in_p", None, ""),
                 PhysicalValue("u_in_n", None, "")]


INTERNAL_INITIAL_VALUES = [
    PhysicalValue("difference", 0.0, "")
]


MODULE_OUTPUTS = [PhysicalValue("u_out", unit="")]

@internal(outputs=["difference"])
def subtractor_logic(t, dt, u_in_p, u_in_n):
    """
    Subtracts two input signals.
    """
    return u_in_p - u_in_n

@common(outputs=["u_out"])
def return_difference(t, dt, difference ):
    """
    Common output function to return the difference.
    """
    return difference
