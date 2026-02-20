# ----------------------------------------------------------------------------
# Pendulum configuration parameters
# ----------------------------------------------------------------------------
class GeometryParameters:
    """
    Geometry parameters for the pendulum and wall.
    Args:
        r_rod (float): Radius of the pendulum rod.
        r_hole (float): Radius of the hole in the wall.
        r_head (float): Radius of the pendulum head.
        l_center (float): Length from pivot to center of mass.
        q_wall_deg (float): Angle of the wall in degrees.
        wall_len_x (float): Length of the wall in x-direction.
        wall_len_y (float): Length of the wall in y-direction.
        wall_len_z (float): Length of the wall in z-direction.
    """

    def __init__(
        self,
        r_rod=0.015, #0.015
        r_hole=0.03, #0.03
        r_head=0.06, #0.06
        l_center=0.24, #0.24
        q_wall_deg=0.0,
        wall_len_x=0.025, #0.015
        wall_len_y=0.25, #0.15
        wall_len_z=0.05, #0.03
    ):
        self.r_rod = r_rod
        self.r_hole = r_hole
        self.r_head = r_head
        self.l_center = l_center
        self.q_wall_deg = q_wall_deg
        self.wall_len_x = wall_len_x
        self.wall_len_y = wall_len_y
        self.wall_len_z = wall_len_z
        pass

    def __str__(self):
        return (
            f"Pendulum Geometry:\n"
            f"  Rod Radius:    {self.r_rod}\n"
            f"  Hole Radius:   {self.r_hole}\n"
            f"  Head Radius:   {self.r_head}\n"
            f"  Center Length: {self.l_center}\n"
            f"Wall Geometry:\n"
            f"  Wall Angle:    {self.q_wall_deg}\n"
            f"  Wall Length X: {self.wall_len_x}\n"
            f"  Wall Length Y: {self.wall_len_y}\n"
            f"  Wall Length Z: {self.wall_len_z}"
        )


# ----------------------------------------------------------------------------
class MaterialParameters:
    """
    Material properties for the pendulum and wall.
    Args:
        E_pendulum (float): Young's modulus of the pendulum material in Pa.
        nu_pendulum (float): Poisson's ratio of the pendulum material.
        rho_pendulum (float): Density of the pendulum material in kg/m^3.
        E_wall (float): Young's modulus of the wall material in Pa.
        nu_wall (float): Poisson's ratio of the wall material.
        rho_wall (float): Density of the wall material in kg/m^3.
        thickness (float): Thickness of the pendulum and wall in m.
    """

    def __init__(
        self,
        E_pendulum=70e9,
        nu_pendulum=0.2,
        rho_pendulum=2700,
        E_wall=210e9,
        nu_wall=0.3, #0.2
        rho_wall=7850,
        thickness=0.1, #0.1
    ):
        self.E_pendulum = E_pendulum
        self.nu_pendulum = nu_pendulum
        self.rho_pendulum = rho_pendulum
        self.E_wall = E_wall
        self.nu_wall = nu_wall
        self.rho_wall = rho_wall
        self.thickness = thickness

    def __str__(self):
        return (
            f"Material Parameters Pendulum:\n"
            f"  Young's Modulus: {self.E_pendulum}\n"
            f"  Poisson's Ratio: {self.nu_pendulum}\n"
            f"  Density:         {self.rho_pendulum}\n"
            f"Material Parameters Wall:\n"
            f"  Young's Modulus: {self.E_wall}\n"
            f"  Poisson's Ratio: {self.nu_wall}\n"
            f"  Density:         {self.rho_wall}\n"
            f"General Thickness: {self.thickness}"
        )


# ----------------------------------------------------------------------------
class MeshParameters:
    """
    Mesh generation parameters for the pendulum and wall.
    Args:
        max_element_size (float): Maximum element size in the mesh.
        mesh_order (int): Order of the finite elements.
        curved_elements (bool): Whether to use curved elements.
        refinement_levels (int): Number of refinement levels for the mesh.
    """

    def __init__(
        self, max_element_size=0.03, mesh_order=2, curved_elements=True, refinement_levels=0
    ):
        self.max_element_size = max_element_size
        self.mesh_order = mesh_order
        self.curved_elements = curved_elements
        self.refinement_levels = refinement_levels

    def __str__(self):
        return (
            f"Mesh Parameters:\n"
            f"  Max Element Size: {self.max_element_size}\n"
            f"  Mesh Order:       {self.mesh_order}\n"
            f"  Curved Elements:  {self.curved_elements}\n"
            f"  Refinement Levels:{self.refinement_levels}"
        )


# ----------------------------------------------------------------------------
class InitialConditionParameters:
    """
    Initial conditions for the pendulum simulation.
    Args:
        angular_position_deg (float): Initial angular position in degrees.
        angular_velocity (float): Initial angular velocity in rad/s.
        drive_torque (float): Initial drive torque in Nm.
    """

    def __init__(self, angular_position_deg=0, angular_velocity=0, drive_torque=0):
        self.angular_position_deg = angular_position_deg
        self.angular_velocity = angular_velocity
        self.drive_torque = drive_torque

    def __str__(self):
        return (
            f"Initial Conditions:\n"
            f"  Angular Position:     {self.angular_position_deg} deg\n"
            f"  Angular Velocity:     {self.angular_velocity} rad/s\n"
            f"  Drive Torque:         {self.drive_torque} Nm"
        )


# ----------------------------------------------------------------------------
class ContactParameters:
    """
    Contact parameters for the pendulum simulation.
    Args:
        kn (float): Contact stiffness in N/m.
    """

    def __init__(self, kn=1e10):
        self.kn = kn

    def __str__(self):
        return f"Contact Parameters:\n   Contact Stiffness: {self.kn:.2e} N/m"


# ----------------------------------------------------------------------------
class SimulationParameters:
    """
    Simulation parameters for the pendulum simulation.
    Args:
        t_start (float): Start time of the simulation in seconds.
        tau (float): Internal time step in seconds.
        t_end (float): End time of the simulation in seconds.
        max_err (float): Maximum solver error tolerance.
        max_it (int): Maximum number of solver iterations.
        use_gravity (bool): Whether to include gravity in the simulation.
        with_contact (bool): Whether to enable contact modeling.
        torque_traction_distribution (str): Distribution type for torque traction
            ('linear', 'bipolar' aka 'dipole').
    """

    def __init__(
        self,
        t_start=0.0,
        tau=0.01,
        t_end=2.0,
        max_err=1e-6,
        max_it=20,
        use_gravity=True,
        with_contact=True,
        torque_traction_distribution="linear",
    ):
        self.t_start = t_start
        self.tau = tau
        self.t_end = t_end
        self.max_err = max_err
        self.max_it = max_it

        self.use_gravity = use_gravity
        self.with_contact = with_contact
        self.torque_traction_distribution = torque_traction_distribution

    def __str__(self):
        return (
            f"Simulation Parameters:\n"
            f"  Simulation Start Time: {self.t_start} s\n"
            f"  Internal Time Step:    {self.tau} s\n"
            f"  Simulation End Time:   {self.t_end} s\n"
            f"  Max Solver Error:      {self.max_err}\n"
            f"  Max Solver Iterations: {self.max_it}\n"
            f"  Use Gravity:           {self.use_gravity}\n"
            f"  With Contact:          {self.with_contact}\n"
            f"  Torque Traction Dist.: {self.torque_traction_distribution}"
        )


# ----------------------------------------------------------------------------
class AnimationParameters:
    """Animation parameters for the pendulum simulation.
    Args:
        animate (bool): Whether to enable animation.
        interval (int): Interval between frames in milliseconds.
        speed (float): Speed multiplier for the animation.
    """

    def __init__(self, animate=True, interval=10, speed=50):
        self.animate = animate
        self.interval = interval
        self.speed = speed

    def __str__(self):
        return (
            f"Animation Parameters:\n"
            f"  Animate:        {self.animate}\n"
            f"  Interval:       {self.interval}\n"
            f"  Speed:          {self.speed}x"
        )


# ----------------------------------------------------------------------------
def to_json_serializable(obj):
    """Convert configuration object to a JSON-serializable dictionary."""
    if hasattr(obj, "__dict__"):
        return {key: to_json_serializable(value) for key, value in obj.__dict__.items()}
    elif isinstance(obj, list):
        return [to_json_serializable(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: to_json_serializable(value) for key, value in obj.items()}
    else:
        return obj
