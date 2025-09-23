class GeometryParameters:
    # Pendulum geometry
    r_rod:    float = 0.05
    r_hole:   float = 0.1
    r_head:   float = 0.2
    l_center: float = 0.8
    
    # Wall geometry
    q_wall_deg: float = 0
    wall_len_x: float = 0.15
    wall_len_y: float = 0.8
    wall_len_z: float = 0.1

    def __init__(self, r_rod=None, r_hole=None, r_head=None, l_center=None, q_wall_deg=None, wall_len_x=None, wall_len_y=None, wall_len_z=None):
        if r_rod is not None:
            self.r_rod = r_rod
        if r_hole is not None:
            self.r_hole = r_hole
        if r_head is not None:
            self.r_head = r_head
        if l_center is not None:
            self.l_center = l_center
        if q_wall_deg is not None:
            self.q_wall_deg = q_wall_deg
        if wall_len_x is not None:
            self.wall_len_x = wall_len_x
        if wall_len_y is not None:
            self.wall_len_y = wall_len_y
        if wall_len_z is not None:
            self.wall_len_z = wall_len_z


class MaterialParameters:
    material_law:      str   = "linear_elastic" # "linear_elastic" or "neo_hookean"
    E_pendulum:        float = 2.10e9     
    nu_pendulum:       float = 0.35       
    rho_pendulum:      float = 1040      
    E_wall:            float = 2.10e9     
    nu_wall:           float = 0.35       
    rho_wall:          float = 1040      
    thickness:         float = 0.1       
    contact_stiffness: float = 1e9       
    
class MeshParameters:
    max_element_size:  float = 0.035
    mesh_order:        int   = 3
    curved_elements:   bool  = True
    refinement_levels: int   = 0
    

class InitialConditionParameters:
    angular_position_deg:  float = 5
    angular_velocity:      float = -0.1
    angular_acceleration:  float = -0.01
    

class SimulationParameters:
    t_start:  float = 0 
    tau:      float = 0.025  
    t_end:    float = 1       
    
class AnimationParameters:
    interval: int   = 10       
    speed:    float = 3.0   