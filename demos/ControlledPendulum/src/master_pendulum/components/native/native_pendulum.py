import numpy as np
from scipy.integrate import solve_ivp

from syssimx import CoSimComponent
from syssimx.core.port import PortSpec, PortType
from syssimx.utilities import Quantity

class NativePendulum(CoSimComponent):

    def __init__(self, name, label = None, group = None):
        super().__init__(name, label, group)

        # Initialize internal variables
        self._theta = 0.0  # Angular position (rad)
        self._omega = 0.0  # Angular velocity (rad/s)
        self._alpha = 0.0  # Angular acceleration (rad/s^2)

        # Define Input Ports
        self.input_specs.update({
            'torque': PortSpec(name="torque", type=PortType.REAL, direction='in'),
            'omega_invert': PortSpec(name="omega_invert", type=PortType.EVENT, direction='in')
        })
        
        # Define Output Ports
        self.output_specs.update({
            "theta": PortSpec(name="theta", type=PortType.REAL, direction="out", unit="rad"),
            "omega": PortSpec(name="omega", type=PortType.REAL, direction="out", unit="rad/s"),
            "alpha": PortSpec(name="alpha", type=PortType.REAL, direction="out", unit="rad/s^2")
        })
        # Set Default Parameter Values
        self._set_default_parameter_values()

    def _set_default_parameter_values(self):
        self.parameters.update({
            "L":       Quantity(0.6, "m"),      # Length of the pendulum rod (m)
            "m":       Quantity(40, "kg"),      # Mass of the pendulum bob (kg)
            "inertia": Quantity(20, "kg*m^2"),  # Moment of inertia (kg*m^2)
            "g":       Quantity(9.81, "m/s^2"), # Gravitational acceleration (m/s^2)
            "q0":      Quantity(0.3, "rad"),    # Initial angle (rad)
            "omega0":  Quantity(0.0, "rad/s")   # Initial angular velocity (rad/s)
        })
    
    def _pendulum_dynamics(self, y: np.ndarray):
        theta, omega = y
        m = self.parameters["m"].magnitude
        g = self.parameters["g"].magnitude
        L = self.parameters["L"].magnitude
        I = self.parameters["inertia"].magnitude

        alpha = -(m * g * L * np.sin(theta)) / I
        return np.array([omega, alpha])
        
    def _initialize_component(self, t0):
        # Set initial conditions
        self._theta = self.parameters["q0"].magnitude
        self._omega = self.parameters["omega0"].magnitude
        y = np.array([self._theta, self._omega])
        self._alpha = self._pendulum_dynamics(y)[1]
    
    def _update_output_states(self, t = None, event_names = ...):
        self.outputs['theta'].set(self._theta)
        self.outputs['omega'].set(self._omega)
        self.outputs['alpha'].set(self._alpha)

    def _do_step_internal(self, t, dt):
        """Solve pendulum ODE over [t, t+dt]."""
        y0 = np.array([self._theta, self._omega])
        
        sol = solve_ivp(
            fun=lambda t, y: self._pendulum_dynamics(y),
            t_span=[t, t + dt],
            y0=y0,
            method='BDF',
            t_eval=[t + dt],
            
        )
        
        self._theta, self._omega = sol.y[:, -1]
        self._alpha = self._pendulum_dynamics(np.array([self._theta, self._omega]))[1]

    def reset(self):
        super().reset()

        self.parameters.clear()
        self._set_default_parameter_values()

        self._theta = 0.0
        self._omega = 0.0
        self._alpha = 0.0