"""
Simple pendulum module for SysSimX framework demonstration.

Physical system: A point mass attached to a rigid rod of fixed length,
swinging under gravity with optional damping.

Equations of motion:
ang_acc = -(g/L) * sin(ang_pos) - (b/mL²) * ang_vel

Where:
- ang_pos: angular position (rad)
- ang_vel: angular velocity (rad/s)  
- ang_acc: angular acceleration (rad/s²)
- g: gravitational acceleration (m/s²)
- L: pendulum length (m)
- b: damping coefficient (N⋅m⋅s/rad)
- m: mass (kg)
"""

from core.module import algebraic, differential, internal, common
from core.physical_value import PhysicalValue
import numpy as np

# Module parameters
PARAMETERS = [
    PhysicalValue("length", 1.0, "m"),          # pendulum length
    PhysicalValue("mass", 1.0, "kg"),           # point mass
    PhysicalValue("gravity", 9.81, "m/s^2"),    # gravitational acceleration
    PhysicalValue("damping", 0.1, "N*m*s/rad")  # damping coefficient
]


# Module outputs
MODULE_OUTPUTS = [
    PhysicalValue("angle", unit="rad"),
    PhysicalValue("angular_velocity", unit="rad/s"),
    PhysicalValue("angular_acceleration", unit="rad/s^2"),
    PhysicalValue("kinetic_energy", unit="J"),
    PhysicalValue("potential_energy", unit="J"),
    PhysicalValue("x_pos", unit="m"),
    PhysicalValue("y_pos", unit="m"),
]

# Initial values for the module
INITIAL_VALUES = [
    PhysicalValue("angle", np.pi/4, "rad"),
    PhysicalValue("angular_velocity", 0.0, "rad/s"),
]


# functions always have t, dt as arguments (in that order); regardless weather they use them or not
@internal(outputs=["", ""])
def func1(t, dt):
    pass

@algebraic(outputs=[""])
def func2(t, dt):
    pass

@differential(['angular_velocity', 'angle'])
def pendulum_dynamics(angle, angular_velocity, length, mass, gravity, damping):
    """
    Compute derivatives for pendulum motion.
    
    Returns:
        (d_angle/dt, d_angular_velocity/dt)
    """
    # Angular acceleration from equation of motion
    angular_acceleration = -(gravity / length) * np.sin(angle) - (damping / (mass * length**2)) * angular_velocity
    
    # State derivatives
    d_angle_dt = angular_velocity
    d_angular_velocity_dt = angular_acceleration
    
    return d_angle_dt, d_angular_velocity_dt


@common(['angular_acceleration', 'kinetic_energy', 'potential_energy', 'total_energy', 'x_position', 'y_position'])
def pendulum_outputs(angle, angular_velocity, length, mass, gravity, damping):
    """
    Compute output quantities for the pendulum.
    
    Returns:
        (angular_acceleration, kinetic_energy, potential_energy, total_energy, x_position, y_position)
    """
    # Angular acceleration (same as in dynamics)
    angular_acceleration = -(gravity / length) * np.sin(angle) - (damping / (mass * length**2)) * angular_velocity
    
    # Energy calculations
    kinetic_energy = 0.5 * mass * (length * angular_velocity)**2
    potential_energy = mass * gravity * length * (1 - np.cos(angle))  # Reference at bottom
    total_energy = kinetic_energy + potential_energy
    
    # Cartesian position (for visualization)
    x_position = length * np.sin(angle)
    y_position = -length * np.cos(angle)  # Negative because hanging down
    
    return angular_acceleration, kinetic_energy, potential_energy, total_energy, x_position, y_position
