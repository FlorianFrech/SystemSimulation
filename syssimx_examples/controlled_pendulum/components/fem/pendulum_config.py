"""Configuration parameter objects for the FEM pendulum.

Each group of parameters is a small ``@dataclass`` so it carries sensible
defaults, a generated ``__repr__``, and field-level documentation. They are
plain mutable containers — ``FEMPendulum`` overwrites individual fields (e.g.
``sim_params.t_start``) during initialization.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from typing import Any


@dataclass
class GeometryParameters:
    """Geometry of the pendulum and the contact wall.

    Attributes:
        r_rod: Radius of the pendulum rod.
        r_hole: Radius of the hole in the pendulum head.
        r_head: Radius of the pendulum head.
        l_center: Length from pivot to center of mass.
        q_wall_deg: Angle of the wall in degrees.
        wall_len_x: Wall extent in the x-direction.
        wall_len_y: Wall extent in the y-direction.
        wall_len_z: Wall extent in the z-direction.
    """

    r_rod: float = 0.015
    r_hole: float = 0.03
    r_head: float = 0.06
    l_center: float = 0.24
    q_wall_deg: float = 0.0
    wall_len_x: float = 0.025
    wall_len_y: float = 0.25
    wall_len_z: float = 0.05


@dataclass
class MaterialParameters:
    """Material properties for the pendulum and wall.

    Attributes:
        model: Constitutive law key, ``"svk"`` or ``"neo_hookean"``.
        E_pendulum: Young's modulus of the pendulum material in Pa.
        nu_pendulum: Poisson's ratio of the pendulum material.
        rho_pendulum: Density of the pendulum material in kg/m³.
        E_wall: Young's modulus of the wall material in Pa.
        nu_wall: Poisson's ratio of the wall material.
        rho_wall: Density of the wall material in kg/m³.
        thickness: Out-of-plane thickness in m (plane-stress assumption).
    """

    model: str = "svk"
    E_pendulum: float = 2.1e11
    nu_pendulum: float = 0.3
    rho_pendulum: float = 7850
    E_wall: float = 210e9
    nu_wall: float = 0.3
    rho_wall: float = 7850
    thickness: float = 0.01


@dataclass
class MeshParameters:
    """Mesh generation parameters.

    Attributes:
        max_element_size: Maximum element size in the mesh.
        mesh_order: Polynomial order of the finite elements.
        curved_elements: Whether to use curved elements.
        refinement_levels: Number of uniform refinement levels.
    """

    max_element_size: float = 0.03
    mesh_order: int = 2
    curved_elements: bool = True
    refinement_levels: int = 0


@dataclass
class InitialConditionParameters:
    """Initial conditions for the pendulum simulation.

    Attributes:
        angular_position_deg: Initial angular position in degrees.
        angular_velocity: Initial angular velocity in rad/s.
        drive_torque: Initial drive torque in N·m.
    """

    angular_position_deg: float = 0
    angular_velocity: float = 0
    drive_torque: float = 0


@dataclass
class ContactParameters:
    """Contact parameters for the pendulum simulation.

    Attributes:
        kn: Contact (penalty) stiffness in N/m.
    """

    kn: float = 2e9


@dataclass
class SimulationParameters:
    """Time integration and solver parameters.

    Attributes:
        t_start: Start time of the simulation in seconds.
        tau: Internal (macro) time step in seconds.
        t_end: End time of the simulation in seconds.
        max_err: Maximum solver error tolerance.
        max_it: Maximum number of solver iterations.
        use_gravity: Whether to include gravity.
        with_contact: Whether to enable contact modeling.
        torque_traction_distribution: Distribution type for torque traction
            (``"linear"`` or ``"bipolar"`` aka ``"dipole"``).
    """

    t_start: float = 0.0
    tau: float = 0.001
    t_end: float = 2.0
    max_err: float = 1e-6
    max_it: int = 20
    use_gravity: bool = True
    with_contact: bool = True
    torque_traction_distribution: str = "linear"


@dataclass
class AnimationParameters:
    """Animation parameters for the pendulum visualization.

    Attributes:
        animate: Whether to record/render animation frames.
        interval: Interval between frames in milliseconds.
        speed: Speed multiplier for the animation.
    """

    animate: bool = True
    interval: int = 10
    speed: float = 50


def to_json_serializable(obj: Any) -> Any:
    """Recursively convert a config object (or container) to plain JSON types."""
    if is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: to_json_serializable(getattr(obj, f.name)) for f in fields(obj)}
    if hasattr(obj, "__dict__"):
        return {key: to_json_serializable(value) for key, value in obj.__dict__.items()}
    if isinstance(obj, list):
        return [to_json_serializable(item) for item in obj]
    if isinstance(obj, dict):
        return {key: to_json_serializable(value) for key, value in obj.items()}
    return obj
