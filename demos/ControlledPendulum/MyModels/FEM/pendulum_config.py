class GeometryParameters:
    def __init__(self):
        self.r_rod = 0.05
        self.r_hole = 0.1
        self.r_head = 0.2
        self.l_center = 0.8
        self.with_contact = False
        self.q_wall_deg = 0
        self.wall_len_x = 0.05
        self.wall_len_y = 0.5   
        self.wall_len_z = 0.1
        pass
    
    def __str__(self):
        return (f"Pendulum Geometry:\n"
                f"  Rod Radius:    {self.r_rod}\n"
                f"  Hole Radius:   {self.r_hole}\n"
                f"  Head Radius:   {self.r_head}\n"
                f"  Center Length: {self.l_center}\n"
                f"Wall Geometry:\n"
                f"  Wall Angle:    {self.q_wall_deg}\n"
                f"  Wall Length X: {self.wall_len_x}\n"
                f"  Wall Length Y: {self.wall_len_y}\n"
                f"  Wall Length Z: {self.wall_len_z}")


class MaterialParameters:
    def __init__(self):
        self.E_pendulum = 210e9 
        self.nu_pendulum = 0.2      
        self.rho_pendulum = 7850      
        self.E_wall = 210e9
        self.nu_wall = 0.2
        self.rho_wall = 7850
        self.thickness = 0.1            
    
    def __str__(self):
            return (f"Material Parameters Pendulum:\n"
                    f"  Young's Modulus: {self.E_pendulum}\n"
                    f"  Poisson's Ratio: {self.nu_pendulum}\n"
                    f"  Density:         {self.rho_pendulum}\n"
                    f"Material Parameters Wall:\n"
                    f"  Young's Modulus: {self.E_wall}\n"
                    f"  Poisson's Ratio: {self.nu_wall}\n"
                    f"  Density:         {self.rho_wall}\n"
                    f"General Thickness: {self.thickness}")


class MeshParameters:
    def __init__(self):
        self.max_element_size = 0.03
        self.mesh_order = 2
        self.curved_elements = True
        self.refinement_levels = 0

    def __str__(self):
        return (f"Mesh Parameters:\n"
                f"  Max Element Size: {self.max_element_size}\n"
                f"  Mesh Order:       {self.mesh_order}\n"
                f"  Curved Elements:  {self.curved_elements}\n"
                f"  Refinement Levels:{self.refinement_levels}")
    

class InitialConditionParameters:
    def __init__(self):
        self.angular_position_deg = 0
        self.angular_velocity = 0
        self.drive_torque = 0

    def __str__(self):
        return (f"Initial Conditions:\n"
                f"  Angular Position:     {self.angular_position_deg} deg\n"
                f"  Angular Velocity:     {self.angular_velocity} rad/s\n"
                f"  Angular Acceleration: {self.angular_acceleration} rad/s²\n"
                f"  Drive Torque:         {self.drive_torque} Nm")
    
    
class ContactParameters:
    def __init__(self):
        self.kn = 1e10
    def __str__(self):
        return (f"Contact Parameters:\n"
                f"   Contact Stiffness: {self.kn:.2e} N/m")


class SimulationParameters:
    def __init__(self):
        self.t_start = 0.0
        self.tau = 0.01
        self.t_end = 2.0
        self.max_err = 1e-6
        self.max_it = 20

        self.use_gravity = True
        self.torque_traction_distribution = 'linear'  # 'linear' or 'bipolar'
    
    def __str__(self):
        return (f"Simulation Parameters:\n"
                f"  Simulation Start Time: {self.t_start} s\n"
                f"  Internal Time Step:    {self.tau} s\n"
                f"  Simulation End Time:   {self.t_end} s")       
    
class AnimationParameters:
    def __init__(self):
        self.animate = True
        self.interval = 10
        self.speed = 50

    def __str__(self):
        return (f"Animation Parameters:\n"
                f"  Interval:        {self.interval}\n"
                f"  Speed:           {self.speed}x")