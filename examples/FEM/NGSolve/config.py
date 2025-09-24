class GeometryParameters:
    # Pendulum geometry
    r_rod:    float = 0.05
    r_hole:   float = 0.1
    r_head:   float = 0.2
    l_center: float = 0.8
    
    # Wall geometry
    q_wall_deg: float = 0
    wall_len_x: float = 0.05
    wall_len_y: float = 0.5
    wall_len_z: float = 0.1
    

class MaterialParameters:
    material_law:      str   = "neo_hookean" # "linear_elastic" or "neo_hookean"
    E_pendulum:        float = 5e5    
    nu_pendulum:       float = 0.45       
    rho_pendulum:      float = 1000      
    E_wall:            float = 2.10e9     
    nu_wall:           float = 0.2       
    rho_wall:          float = 7850      
    thickness:         float = 0.1       
    
class MeshParameters:
    max_element_size:  float = 0.035
    mesh_order:        int   = 3
    curved_elements:   bool  = True
    refinement_levels: int   = 0
    

class InitialConditionParameters:
    angular_position_deg:  float = 1
    angular_velocity:      float = -1
    angular_acceleration:  float = -0.5
    

class ContactParameters:
    gap_type: str = 'incremental' # 'incremental' or 'absolute'
    kn:      float = 1e7         # contact stiffness
    

class SimulationParameters:
    t_start:  float = 0 
    tau:      float = 1e-3  
    t_end:    float = 0.20       
    
class AnimationParameters:
    interval: int   = 10       
    speed:    float = 3.0      