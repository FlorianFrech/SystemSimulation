# ============================================================================
# Torque Profile Functions
# ============================================================================
def zero_torque(t: float) -> float:
    """No applied torque (free swing)."""
    return 0.0


def constant_torque(amplitude: float):
    """Constant torque profile."""

    def torque(t: float) -> float:
        return amplitude

    return torque


def ramp_torque(t_end: float, amplitude: float):
    """Piecewise torque profile (ramp, hold, reverse)."""

    def torque(t: float) -> float:
        interval = t_end / 6
        if t < interval:
            return t * amplitude
        elif t < 2 * interval:
            return interval * amplitude
        elif t < 3 * interval:
            return interval * amplitude - (t - 2 * interval) * amplitude
        elif t < 4 * interval:
            return -(t - 3 * interval) * amplitude
        elif t < 5 * interval:
            return -(interval) * amplitude
        else:
            return -interval * amplitude + (t - 5 * interval) * amplitude

    return torque