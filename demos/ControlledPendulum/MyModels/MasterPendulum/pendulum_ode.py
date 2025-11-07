from pathlib import Path
import sys
import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp

# ============================================================================
# Analytical Solution using ODE Integration
# ============================================================================
class PendulumODE:
    """Analytical pendulum solution using scipy ODE solver."""
    
    def __init__(self, mass: float, length: float, inertia: float, g: float = 9.81):
        self.mass = mass
        self.length = length
        self.inertia = inertia
        self.g = g
        
    def dynamics(self, t: float, y: np.ndarray, torque_func) -> np.ndarray:
        """
        Pendulum dynamics: [q_dot, omega_dot]
        Args:
            t: Current time
            y: State [q, omega]
            torque_func: Function torque(t) -> float
        Returns:
            dy/dt = [omega, alpha]
        """
        q, omega = y
        torque = torque_func(t)
        
        # alpha = (torque - m*g*L*sin(q)) / I
        alpha = (torque - self.mass * self.g * self.length * np.sin(q)) / self.inertia
        
        return np.array([omega, alpha])
    
    def solve(self, t_span: tuple, y0: np.ndarray, torque_func, dt: float = 0.01):
        """
        Solve pendulum motion over time span.
        Args:
            t_span: (t_start, t_end)
            y0: Initial state [q0, omega0]
            torque_func: Function torque(t) -> float
            dt: Time step for output
        Returns:
            t_vals, q_vals, omega_vals, alpha_vals
        """
        t_eval = np.arange(t_span[0], t_span[1] + dt, dt)
        
        sol = solve_ivp(
            fun=lambda t, y: self.dynamics(t, y, torque_func),
            t_span=t_span,
            y0=y0,
            t_eval=t_eval,
            method='RK45',
            rtol=1e-9,
            atol=1e-12
        )
        
        # Compute accelerations
        alpha_vals = np.array([
            self.dynamics(t, y, torque_func)[1] 
            for t, y in zip(sol.t, sol.y.T)
        ])
        
        return sol.t, sol.y[0], sol.y[1], alpha_vals
    
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