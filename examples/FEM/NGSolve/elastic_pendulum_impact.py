import numpy as np
from ngsolve import *
from ngsolve.webgui import Draw
from netgen.occ import *
from ngsolve.solvers import Newton
from typing import Dict, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum

class PendulumType(Enum):
    """Enumeration for pendulum dimensionality"""
    PLANAR_2D = "2D"
    SPATIAL_3D = "3D"

class MaterialModel(Enum):
    """Enumeration for material models"""
    NEO_HOOKE = "neo_hooke"
    LINEAR_ELASTIC = "linear_elastic"

@dataclass
class GeometryParameters:
    """Geometry configuration parameters"""
    # Pendulum geometry
    pendulum_rod_radius: float = 0.02
    pendulum_head_radius: float = 0.075
    pendulum_length: float = 0.4
    
    # Wall geometry
    wall_height: float = 0.4
    wall_width: float = 0.1
    wall_thickness: float = 0.1

    wall_angle_deg: float = 90.0  # Vertical wall


@dataclass
class MaterialParameters:
    """Material properties"""
    youngs_modulus: float = 21000.0  # Pa
    poisson_ratio: float = 0.2
    density: float = 7e3  # kg/m³
    thickness: float = 0.01  # m (for 2D problems)
    material_model: MaterialModel = MaterialModel.NEO_HOOKE

@dataclass
class MeshParameters:
    """Mesh generation parameters"""
    max_element_size: float = 0.1
    mesh_order: int = 3
    curved_elements: bool = True
    refinement_level: int = 0

@dataclass
class SimulationParameters:
    """Simulation settings"""
    start_time: float = 0.0
    end_time: float = 10.0
    time_step: float = 0.025
    contact_stiffness: float = 1e9
    solver_tolerance: float = 1e-8

@dataclass
class InitialConditions:
    """Initial state parameters"""
    angular_position_deg: float = 0.0
    angular_velocity_rad_s: float = 0.0
    angular_acceleration_rad_s2: float = 0.0

@dataclass
class AnimationSettings:
    """Animation visualization parameters"""
    speed_multiplier: float = 2.0
    show_deformation: bool = True
    show_velocity_vectors: bool = False
    show_stress: bool = False
    color_range_min: float = 0.0
    color_range_max: float = 2.0
    auto_scale: bool = False

class ElasticPendulumContact:
    """
    A comprehensive FEM elastic pendulum with contact simulation class.
    
    This class encapsulates all NGSolve complexity and provides a clean,
    user-friendly interface for pendulum contact simulations.
    """
    
    def __init__(self, 
                 pendulum_type: PendulumType = PendulumType.PLANAR_2D,
                 geometry_params: Optional[GeometryParameters] = None,
                 material_params: Optional[MaterialParameters] = None,
                 mesh_params: Optional[MeshParameters] = None):
        """
        Initialize the elastic pendulum contact model.
        
        Args:
            pendulum_type: 2D or 3D pendulum simulation
            geometry_params: Geometric configuration
            material_params: Material properties
            mesh_params: Mesh generation settings
        """
        self.pendulum_type = pendulum_type
        self.geometry_params = geometry_params or GeometryParameters()
        self.material_params = material_params or MaterialParameters()
        self.mesh_params = mesh_params or MeshParameters()
        
        # Internal state
        self._mesh = None
        self._fes = None
        self._contact = None
        self._material_law = None
        self._simulation_results = []
        
        # Grid functions
        self._gfu = None  # Current displacement/Lagrange multipliers
        self._gfv = None  # Current velocity
        self._gfa = None  # Current acceleration
        self._gfut = None  # Time series displacement
        self._gfvt = None  # Time series velocity
        
        # Setup material law
        self._setup_material_law()
    
    def create_geometry_and_mesh(self) -> 'ElasticPendulumContact':
        """
        Create pendulum geometry and generate mesh.
        
        Returns:
            Self for method chaining
        """
        if self.pendulum_type == PendulumType.PLANAR_2D:
            self._create_2d_geometry()
        else:
            self._create_3d_geometry()
        
        self._generate_mesh()
        self._setup_finite_element_spaces()
        self._setup_contact()
        return self
    
    def _create_2d_geometry(self):
        """Create 2D pendulum geometry with wall"""
        gp = self.geometry_params
        
        # Pendulum rod
        rod = MoveTo(-gp.pendulum_rod_radius,0).Rectangle(gp.pendulum_rod_radius * 2, gp.pendulum_length).Face()
        rod.edges.Min(Y).name = "rotation"
        rod.faces.name = "rod"
        rod.faces.maxh = self.mesh_params.max_element_size

        # Pendulum head       
        circ = Circle((0, gp.pendulum_length), gp.pendulum_head_radius).Face()
        circ.faces.name = "circ"
        circ.faces.maxh = self.mesh_params.max_element_size * 0.66
        circ.edges.name = "contact_head"
        
        # Combine pendulum parts
        pendulum = rod + circ
        pendulum.name = "pendulum"
        
        # Wall
        q_wall = np.deg2rad(gp.wall_angle_deg)
        wall_x_pos = -gp.wall_width - gp.pendulum_head_radius
        wall_y_pos = - gp.pendulum_length - gp.wall_height/2

        wall = MoveTo(wall_x_pos, wall_y_pos).Rectangle(
            gp.wall_width, gp.wall_height
        ).Face()
        wall.faces.maxh = self.mesh_params.max_element_size * 0.66
        wall.edges.Max(X).name = "contact_wall"
        wall.edges.Max(Y).name = "fix"
        wall.edges.Min(Y).name = "fix"
        wall.name = "wall"
        
        self._geometry = Compound([pendulum, wall])
    
    def _create_3d_geometry(self):
        """Create 3D pendulum geometry with wall"""
        # Placeholder for 3D geometry creation
        pass
    
    def _generate_mesh(self):
        """Generate finite element mesh"""
        dim = 2 #if self.pendulum_type == PendulumType.PLANAR_2D else 3
        
        self._mesh = Mesh(
            OCCGeometry(self._geometry, dim=dim).GenerateMesh(
                maxh=self.mesh_params.max_element_size
            )
        )
        
        if self.mesh_params.curved_elements:
            self._mesh.Curve(self.mesh_params.mesh_order)
    
    def _setup_finite_element_spaces(self):
        """Setup finite element spaces and grid functions"""
        # Vector space for displacement
        V = VectorH1(
            self._mesh, 
            order=self.mesh_params.mesh_order,
            dirichlet="fix" #if self.pendulum_type == PendulumType.PLANAR_2D else "base"
        )
        
        # Number space for Lagrange multipliers (constraint mean values)
        constraint_boundary = "rotation"
        multiplier_dim = 2 #if self.pendulum_type == PendulumType.PLANAR_2D else 3
        
        Q = NumberSpace(self._mesh, definedon=self._mesh.Boundaries(constraint_boundary))
        self._fes = V * Q**multiplier_dim
        
        # Initialize grid functions
        self._gfu = GridFunction(self._fes)  # Current state
        self._gfv = GridFunction(self._fes)  # Velocity
        self._gfa = GridFunction(self._fes)  # Acceleration
        
        self._gfuold = GridFunction(self._fes)  # Previous displacement
        self._gfvold = GridFunction(self._fes)  # Previous velocity
        self._gfaold = GridFunction(self._fes)  # Previous acceleration
        
        # Time series storage
        self._gfut = GridFunction(V, multidim=0)
        self._gfvt = GridFunction(V, multidim=0)
    
    def _setup_material_law(self):
        """Setup material constitutive law"""
        E = 2100 #self.material_params.youngs_modulus
        nu = 0.2 #self.material_params.poisson_ratio
        
        # Lamé parameters
        self._mu = E / (2 * (1 + nu))
        self._lam = E * nu / ((1 + nu) * (1 - 2 * nu))
        
        if self.material_params.material_model == MaterialModel.NEO_HOOKE:
            if self.pendulum_type == PendulumType.PLANAR_2D:
                self._material_law = self._neo_hooke_2d
                self._deformation_tensor = self._right_cauchy_green_2d
            else:
                self._material_law = self._neo_hooke_3d
                self._deformation_tensor = self._right_cauchy_green_3d
        else:
            self._material_law = self._linear_elastic
    
    def _neo_hooke_2d(self, C):
        """2D Neo-Hookean strain energy density"""
        return 0.5 * self._mu * (Trace(C - Id(2)) + 
                                2 * self._mu / self._lam * 
                                Det(C)**(-self._lam / 2 / self._mu) - 1)
    
    def _neo_hooke_3d(self, C):
        """3D Neo-Hookean strain energy density"""
        return 0.5 * self._mu * (Trace(C - Id(3)) + 
                                2 * self._mu / self._lam * 
                                Det(C)**(-self._lam / 2 / self._mu) - 1)
    
    def _right_cauchy_green_2d(self, u):
        """2D Right Cauchy-Green deformation tensor"""
        F = Id(2) + Grad(u)
        return F.trans * F
    
    def _right_cauchy_green_3d(self, u):
        """3D Right Cauchy-Green deformation tensor"""
        F = Id(3) + Grad(u)
        return F.trans * F
    
    def _linear_elastic(self, u):
        """Linear elastic strain energy density"""
        eps = 0.5 * (Grad(u) + Grad(u).trans)
        return 0.5 * self._lam * Trace(eps)**2 + self._mu * InnerProduct(eps, eps)
    
    def _setup_contact(self):
        """Setup contact boundary conditions"""
        contact_boundaries = "contact_head|contact_wall"
        self._contact = ContactBoundary(
            self._mesh.Boundaries(contact_boundaries),
            self._mesh.Boundaries(contact_boundaries)
        )
        
        # Contact formulation
        X = CoefficientFunction((x, y) if self.pendulum_type == PendulumType.PLANAR_2D else (x, y, z))
        (u, _), (_, _) = self._fes.TnT()
        
        uold = self._gfuold.components[0]
        
        # Gap function
        gap = ((X + u - uold) - (X.Other() + u.Other() - uold.Other())) * (-specialcf.normal(2 if self.pendulum_type == PendulumType.PLANAR_2D else 3).Other())
        
        # Penalty method for contact
        contact_stiffness = 1e9  # Could be made configurable
        self._contact.AddEnergy(
            IfPos(gap, contact_stiffness * gap * gap, 0),
            deformed=True
        )
    
    def show_geometry(self) -> 'ElasticPendulumContact':
        """Display the generated mesh geometry"""
        if self._mesh is None:
            raise RuntimeError("Mesh not created. Call create_geometry_and_mesh() first.")
        
        Draw(self._mesh, "Pendulum Mesh")
        return self
    
    def set_initial_conditions(self, initial_conditions: InitialConditions) -> 'ElasticPendulumContact':
        """
        Set initial angular position, velocity, and acceleration.
        
        Args:
            initial_conditions: Initial state parameters
        """
        if self._fes is None:
            raise RuntimeError("FE spaces not setup. Call create_geometry_and_mesh() first.")
        
        # Convert to radians
        theta = np.deg2rad(initial_conditions.angular_position_deg)
        omega = initial_conditions.angular_velocity_rad_s
        alpha = initial_conditions.angular_acceleration_rad_s2
        
        c, s = np.cos(theta), np.sin(theta)
        
        # Rotation center (could be made configurable)
        cx = cy = 0.0
        
        if self.pendulum_type == PendulumType.PLANAR_2D:
            # 2D rotation displacement field
            u_rot = CF(((c - 1.0) * (x - cx) - s * (y - cy),
                       s * (x - cx) + (c - 1.0) * (y - cy)))
            
            # 2D angular velocity field
            v_rot = CF((-omega * (y - cy), omega * (x - cx)))
            
            # 2D angular acceleration field
            a_rot = CF((-alpha * (y - cy), alpha * (x - cx)))
        else:
            # 3D rotation (around Z-axis)
            u_rot = CF(((c - 1.0) * (x - cx) - s * (y - cy),
                       s * (x - cx) + (c - 1.0) * (y - cy),
                       0.0))
            
            v_rot = CF((-omega * (y - cy), omega * (x - cx), 0.0))
            a_rot = CF((-alpha * (y - cy), alpha * (x - cx), 0.0))
        
        # Set initial conditions
        self._gfu.components[0].Set(u_rot, definedon=self._mesh.Materials("pendulum"))
        self._gfv.components[0].Set(v_rot, definedon=self._mesh.Materials("pendulum"))
        self._gfa.components[0].Set(a_rot, definedon=self._mesh.Materials("pendulum"))

        # Copy to "old" variables
        self._gfuold.vec[:] = self._gfu.vec
        self._gfvold.vec[:] = self._gfv.vec
        self._gfaold.vec[:] = self._gfa.vec
        
        return self
    
    def setup_simulation(self, sim_params: SimulationParameters) -> 'ElasticPendulumContact':
        """
        Configure simulation parameters.
        
        Args:
            sim_params: Simulation configuration
        """
        self._sim_params = sim_params
        return self
    
    def simulate(self, verbose: bool = True) -> 'ElasticPendulumContact':
        """
        Run the dynamic simulation.
        
        Args:
            verbose: Print simulation progress
        
        Returns:
            Self for method chaining
        """
        if self._sim_params is None:
            raise RuntimeError("Simulation parameters not set. Call setup_simulation() first.")
        
        # Setup bilinear form
        (u, q), (v, p) = self._fes.TnT()
       
        
        bfa = BilinearForm(self._fes)
        
        # Material energy
        if self.material_params.material_model == MaterialModel.NEO_HOOKE:
            C = self._deformation_tensor(u)
            bfa += Variation(self._material_law(C) * dx).Compile()
        else:
            bfa += Variation(self._material_law(u) * dx).Compile()
        
        # Constraint terms
        rotation_facet = "rotation"
        bfa += (InnerProduct(u, p) + InnerProduct(v, q)) * ds(rotation_facet)
        
        # Time stepping scheme (Newmark)
        tau = self._sim_params.time_step
        rho = self.material_params.density
        
        vel_new = 2/tau * (u - self._gfuold.components[0]) - self._gfvold.components[0]
        acc_new = 2/tau * (vel_new - self._gfvold.components[0]) - self._gfaold.components[0]
        
        # Inertial and gravity terms
        gravity = -1  # m/s²
        if self.pendulum_type == PendulumType.PLANAR_2D:
            rhoA = rho * self.material_params.thickness
            gravity_force = CF((0, gravity))
        else:
            rhoA = rho
            gravity_force = CF((0, gravity, 0))
        
        #bfa += rhoA * InnerProduct(acc_new, v) * dx
        bfa += acc_new * v * dx
        bfa += - gravity_force * v * dx
        
        # Clear previous results
        self._simulation_results = []
        self._gfut = GridFunction(self._fes.components[0], multidim=0)
        self._gfvt = GridFunction(self._fes.components[0], multidim=0)
        
        # Time stepping loop
        t = self._sim_params.start_time
        i = 0
        
        with TaskManager():
            while t < self._sim_params.end_time:
                i += 1
                t += tau
                
                # Update contact
                self._contact.Update(self._gfuold.components[0], bfa)
                
                # Solve nonlinear system
                Newton(a=bfa, u=self._gfu, printing=verbose, inverse="sparsecholesky")
                
                # Store results every few steps
                if i % 5 == 0:
                    self._gfut.AddMultiDimComponent(self._gfu.components[0].vec)
                    self._gfvt.AddMultiDimComponent(self._gfv.components[0].vec)
                    
                    if verbose and i % 50 == 0:
                        print(f"Time: {t:.3f}s")
                
                # Update velocity and acceleration
                self._gfv.vec[:] = 2/tau * (self._gfu.vec - self._gfuold.vec) - self._gfvold.vec
                self._gfa.vec[:] = 2/tau * (self._gfv.vec - self._gfvold.vec) - self._gfaold.vec
                
                # Update old values
                self._gfuold.vec[:] = self._gfu.vec
                self._gfvold.vec[:] = self._gfv.vec
                self._gfaold.vec[:] = self._gfa.vec
        
        if verbose:
            print(f"Simulation completed: {i} time steps")
        
        return self
    
    def get_displacement_field(self) -> GridFunction:
        """Get current displacement field"""
        return self._gfu.components[0] if self._gfu else None
    
    def get_velocity_field(self) -> GridFunction:
        """Get current velocity field"""
        return self._gfv.components[0] if self._gfv else None
    
    def get_displacement_time_series(self) -> GridFunction:
        """Get displacement field time series"""
        return self._gfut
    
    def get_velocity_time_series(self) -> GridFunction:
        """Get velocity field time series"""
        return self._gfvt
    
    def set_displacement_field(self, displacement_cf) -> 'ElasticPendulumContact':
        """Set displacement field from CoefficientFunction"""
        if self._gfu is None:
            raise RuntimeError("Grid functions not initialized")
        
        self._gfu.components[0].Set(displacement_cf)
        self._gfuold.vec[:] = self._gfu.vec
        return self
    
    def set_velocity_field(self, velocity_cf) -> 'ElasticPendulumContact':
        """Set velocity field from CoefficientFunction"""
        if self._gfv is None:
            raise RuntimeError("Grid functions not initialized")
            
        self._gfv.components[0].Set(velocity_cf)
        self._gfvold.vec[:] = self._gfv.vec
        return self
    
    def show_current_state(self, show_deformation: bool = True) -> 'ElasticPendulumContact':
        """Display current displacement field"""
        if self._gfu is None:
            raise RuntimeError("No simulation data available")
        
        Draw(self._gfu.components[0], self._mesh, "Current Displacement", 
             deformation=show_deformation)
        return self
    
    def animate_results(self, animation_settings: Optional[AnimationSettings] = None) -> 'ElasticPendulumContact':
        """
        Create animated visualization of simulation results.
        
        Args:
            animation_settings: Animation configuration parameters
        """
        if self._gfut is None:
            raise RuntimeError("No time series data available. Run simulate() first.")
        
        settings = animation_settings or AnimationSettings()
        
        draw_settings = {
            "Multidim": {"speed": settings.speed_multiplier}
        }
        
        if settings.show_velocity_vectors:
            draw_settings["Vectors"] = {
                "draw": True,
                "scale": 0.1,
                "grid_size": 10
            }
        
        Draw(self._gfut, self._mesh,
             interpolate_multidim=True,
             deformation=settings.show_deformation,
             animate=True,
             autoscale=settings.auto_scale,
             min=settings.color_range_min,
             max=settings.color_range_max,
             settings=draw_settings)
        
        return self
    
    def export_results(self, filename: str, format: str = "vtk") -> 'ElasticPendulumContact':
        """Export simulation results to file"""
        # Implementation would depend on desired output format
        # Could use NGSolve's VTKOutput or custom export functions
        pass
    
    # Property accessors
    @property
    def mesh(self):
        """Access to the generated mesh"""
        return self._mesh
    
    @property
    def num_degrees_of_freedom(self) -> int:
        """Number of degrees of freedom in the system"""
        return self._fes.ndof if self._fes else 0
    
    @property
    def simulation_time_span(self) -> Tuple[float, float]:
        """Get simulation time span"""
        if self._sim_params:
            return (self._sim_params.start_time, self._sim_params.end_time)
        return (0.0, 0.0)