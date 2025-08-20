from core.module import algebraic, differential, internal, common
from core.physical_value import PhysicalValue


MODULE_INPUTS = [PhysicalValue("input_signal", unit="")]

MODULE_OUTPUTS = [
    PhysicalValue("y", unit=""),  # Integrated value
    ]

PARAMETERS = [
    PhysicalValue("y_min", 0.0, ""),
    PhysicalValue("y_max", 10.0, "")  # Saturation limits
]

INITIAL_VALUES = [
    PhysicalValue("y", 0.0, "")         # Integrated state variable
]

INTERNAL_INITIAL_VALUES = [
    PhysicalValue("effective_rate", 0.0, "") # rate after saturation
]


# Function for saturation logic
@internal(outputs=["effective_rate"])
def saturation_logic(t, dt, y, input_signal, y_min, y_max):
    """Determine effective rate based on saturation limits."""    
    # Check if currently saturated
    at_upper_limit = (y >= y_max)
    at_lower_limit = (y <= y_min)
    
    if at_upper_limit and input_signal > 0:
        # Saturated at upper limit, don't integrate positive inputs
        effective_rate = 0.0
    elif at_lower_limit and input_signal < 0:
        # Saturated at lower limit, don't integrate negative inputs
        effective_rate = 0.0
    else:
        # Normal operation
        effective_rate = input_signal
    
    return effective_rate

@algebraic(outputs=["rate"])
def constraint(t, dt, y, input_signal):
    return input_signal - y

# Common outputs for external interface
@common(outputs=["sum"])
def integrator_outputs(t, dt, y, y_min, y_max):
    """Generate integrator outputs with saturation clamping."""
    # Clamp output to saturation limits (safety measure)
    return max(y_min, min(y_max, y))

# Differential equation: dy/dt = effective_rate
@differential(outputs=["y"])
def integrator_dynamics(t, dt, effective_rate):
    """Core integration: dy/dt = u_in * gain (with saturation)."""
    return effective_rate