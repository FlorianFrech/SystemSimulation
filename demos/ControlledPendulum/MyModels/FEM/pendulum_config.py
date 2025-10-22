class GeometryParameters:
    # Pendulum geometry
    r_rod:    float = 0.05
    r_hole:   float = 0.1
    r_head:   float = 0.2
    l_center: float = 0.8
    
    # Wall geometry
    with_contact:   bool  = False
    q_wall_deg: float = 0
    wall_len_x: float = 0.05
    wall_len_y: float = 0.5
    wall_len_z: float = 0.1
    
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
    E_pendulum:        float = 210e9 
    nu_pendulum:       float = 0.2      
    rho_pendulum:      float = 7850      
    E_wall:            float = 210e9     
    nu_wall:           float = 0.2       
    rho_wall:          float = 7850      
    thickness:         float = 0.1
    
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
    max_element_size:  float = 0.03
    mesh_order:        int   = 2
    curved_elements:   bool  = True
    refinement_levels: int   = 0

    def __str__(self):
        return (f"Mesh Parameters:\n"
                f"  Max Element Size: {self.max_element_size}\n"
                f"  Mesh Order:       {self.mesh_order}\n"
                f"  Curved Elements:  {self.curved_elements}\n"
                f"  Refinement Levels:{self.refinement_levels}")
    

class InitialConditionParameters:
    angular_position_deg:  float = 0
    angular_velocity:      float = 0
    drive_torque:          float = 0
    
    def __str__(self):
        return (f"Initial Conditions:\n"
                f"  Angular Position:     {self.angular_position_deg} deg\n"
                f"  Angular Velocity:     {self.angular_velocity} rad/s\n"
                f"  Angular Acceleration: {self.angular_acceleration} rad/s²\n"
                f"  Drive Torque:         {self.drive_torque} Nm")
    
    
class ContactParameters:
    kn:      float = 1e10         # contact stiffness
    def __str__(self):
        return (f"Contact Parameters:\n"
                f"   Contact Stiffness: {self.kn:.2e} N/m")


class SimulationParameters:
    t_start:  float = 0 
    tau:      float = 0.01
    t_end:    float = 1
    use_gravity: bool  = True
    
    def __str__(self):
        return (f"Simulation Parameters:\n"
                f"  Simulation Start Time: {self.t_start} s\n"
                f"  Internal Time Step:    {self.tau} s\n"
                f"  Simulation End Time:   {self.t_end} s")       
    
class AnimationParameters:
    animate: bool  = False
    interval: int   = 10       
    speed:    float = 50

    def __str__(self):
        return (f"Animation Parameters:\n"
                f"  Interval:        {self.interval}\n"
                f"  Speed:           {self.speed}x")