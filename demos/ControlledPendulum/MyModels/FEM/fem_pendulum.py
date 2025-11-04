from ast import If
from typing import Dict, Any, Optional

from SysSimX.core.port import PortSpec, PortType, PortState
from SysSimX.core.base import CoSimComponent
from SysSimX.components.fem_comp import FEMComponent
from SysSimX.utilities.units import ureg, Quantity

from MyModels.FEM.pendulum_mesh import build_mesh
from MyModels.FEM.material_laws import NeoHookeanMaterial
from MyModels.FEM.pendulum_config import *

import numpy as np
from ngsolve import *
from ngsolve.webgui import Draw
from netgen.occ import *
from ngsolve.solvers import NewtonMinimization

from IPython.display import display, Markdown
import ipywidgets as widgets
from ipywidgets import Layout, HBox, VBox, HTML

#----------------------------------------------------------------------------
# Port specifications
#----------------------------------------------------------------------------   
INPUT_SPECS = {
    "torque": PortSpec("torque", PortType.REAL, direction="in", unit="N.m")
}

OUTPUT_SPECS = {
    "q": PortSpec("q", PortType.REAL, direction="out", unit="rad"),
    "omega": PortSpec("omega", PortType.REAL, direction="out", unit="rad/s"),
    "alpha": PortSpec("alpha", PortType.REAL, direction="out", unit="rad/s^2")
}

#----------------------------------------------------------------------------
# Pendulum FEM component
#----------------------------------------------------------------------------  
class FEMPendulum(FEMComponent):
    def __init__(self, name: str, group: str = "Plant"):
        super().__init__(name, group=group)
        
        # Define input and output specifications
        self.input_specs = INPUT_SPECS
        self.output_specs = OUTPUT_SPECS
        self._initialize_ports_from_specs()

        # Pendulum configuration parameters
        self.geom_params    = GeometryParameters()
        self.mat_params     = MaterialParameters()
        self.mesh_params    = MeshParameters()
        self.init_params    = InitialConditionParameters()
        self.contact_params = ContactParameters()
        self.sim_params     = SimulationParameters()
        self.anim_params    = AnimationParameters()

        self.parameters = {
            "Geometry": self.geom_params,
            "Material": self.mat_params,
            "Mesh": self.mesh_params,
            "Initial Conditions": self.init_params,
            "Contact": self.contact_params,
            "Simulation": self.sim_params,
            "Animation": self.anim_params
        }

        self._with_contact = self.geom_params.with_contact
        self._use_gravity = self.sim_params.use_gravity
    
    #----------------------------------------------------------------------------
    # Initialization method
    #----------------------------------------------------------------------------   
    def _initialize_component(self, t0:float):
        """
        Netgen/NGSolve pendulum specific initialization (called by base-class).
        """
        self.sim_params.t_start = t0

        self._setup_material_law()
        
        self._create_mesh()
        self._compute_mass()
        self._compute_inertia()
        
        self._initialize_fe_spaces()
        self._initialize_grid_functions()
        
        if self._with_contact:
            self._initialize_contact()

        self._initialize_torque_control()
        
        self._setup_bilinear_form()

        state = {'q': {'value': np.deg2rad(self.init_params.angular_position_deg)},
                 'omega': {'value': self.init_params.angular_velocity},
                 'torque':{'value': self.init_params.drive_torque}}

        self.set_state(state=state, t=t0)

        self.setup_widgets()

    #----------------------------------------------------------------------------
    # Initialization helper methods
    #----------------------------------------------------------------------------
    def _setup_material_law(self):
        self.E_p, self.E_w     = self.mat_params.E_pendulum, self.mat_params.E_wall
        self.nu_p, self.nu_w   = self.mat_params.nu_pendulum, self.mat_params.nu_wall
        self.rho_p, self.rho_w = self.mat_params.rho_pendulum, self.mat_params.rho_wall
    
        self._material_pendulum = NeoHookeanMaterial(self.E_p, self.nu_p)
        self._deformation_gradient_p = self._material_pendulum.C
        self._material_law_p = self._material_pendulum.energy_density
        self._sigma_law_p = self._material_pendulum.sigma
        
        self._material_wall = NeoHookeanMaterial(self.E_w, self.nu_w)
        self._deformation_gradient_w = self._material_wall.C
        self._material_law_w = self._material_wall.energy_density
        self._sigma_law_w = self._material_wall.sigma

    def _create_mesh(self):
        self._mesh = build_mesh(self.geom_params, self.mesh_params, self._with_contact)

    def _compute_mass(self):
        area = Integrate(1, self._mesh, definedon=self._mesh.Materials("pendulum"))
        self.mass = area * self.mat_params.thickness * self.rho_p

    def _compute_inertia(self):
        cx = cy = 0
        self._X_rel = CF((x - cx, y - cy))
        J_area = Integrate(self.rho_p * (self._X_rel[0]*self._X_rel[0] + self._X_rel[1]*self._X_rel[1]),
                           self._mesh, definedon=self._mesh.Materials("pendulum"))
        self.inertia = J_area * self.mat_params.thickness

    def _initialize_fe_spaces(self):
        # Create H1 vector space for 3D quantities (displacement, velocity, acceleration)
        self._V = VectorH1(self._mesh, order=self.mesh_params.mesh_order, dirichlet="fix")
        
        # Create NumberSpace for Lagrange multipliers (rotation constraint)
        self._Q = NumberSpace(self._mesh, definedon=self._mesh.Boundaries('rotation'))
        
        # Mixed FE space
        self._fes = self._V * self._Q**2
        (self._u, self._q), (self._v, self._p) = self._fes.TnT()
        
        # Scalar H1 space for stress in pendulum
        self._S = MatrixValued(H1(self._mesh, order=self.mesh_params.mesh_order,
                                  definedon=self._mesh.Materials("pendulum")))    
        
    def _initialize_grid_functions(self):
        # Initialize grid functions
        self._gf_u = GridFunction(self._fes)  # Current state
        self._gf_v = GridFunction(self._fes)  # Velocity
        self._gf_a = GridFunction(self._fes)  # Acceleration
        
        self._gf_uold = GridFunction(self._fes)  # Previous displacement
        self._gf_vold = GridFunction(self._fes)  # Previous velocity
        self._gf_aold = GridFunction(self._fes)  # Previous acceleration
        
        self._gf_sigma = GridFunction(self._S) # Stress
                
        # Time series storage
        self._gf_u_history = GridFunction(self._V, multidim=0)
        self._gf_v_history = GridFunction(self._V, multidim=0)
        self._gf_stress_history = GridFunction(self._S, multidim=0)

    def _initialize_contact(self):
        kn = self.contact_params.kn
        
        master = self._mesh.Boundaries("contact_wall")
        slave = self._mesh.Boundaries("contact_head")
        self._contact = ContactBoundary(master, slave)

        u = self._u
        u_old = self._gf_uold.components[0]
    
        X_M = CoefficientFunction((x,y))
        X_S = X_M.Other()
        n_S = -specialcf.normal(2).Other()

        increment_master = X_M + u - u_old
        increment_slave = X_S + u.Other() - u_old.Other()
        self._cf = (increment_master - increment_slave) * n_S

        penalty_energy = kn * self._cf * self._cf
        self._contact.AddEnergy(IfPos(self._cf, penalty_energy, 0), deformed = True)

    def _initialize_torque_control(self):
        """
        Initialize torque control system using distributed traction on rotation boundary.
        
        This method creates a smooth, bipolar weight distribution that generates a
        pure torque around the hinge axis when multiplied by the drive parameter.
        """
        
        # --- Geometric quantities ---
        reference_normal = specialcf.normal(2)  # Normal vector in reference configuration
        radius_vector = self._X_rel             # Position vector from pivot to boundary points
        
        # Deformation gradient and surface jacobian for current configuration
        deformation_gradient = Id(2) + Grad(self._u).Trace()
        cofactor_matrix = Cof(deformation_gradient)
        
        # Current surface normal (unnormalized)
        current_normal_unnorm = cofactor_matrix * reference_normal
        surface_jacobian = Norm(current_normal_unnorm)
        current_normal_unit = current_normal_unnorm / IfPos(surface_jacobian, surface_jacobian, 1)
        
        # Cross product for torque calculation: r × n (2D cross product gives scalar)
        self._torque_moment_arm = -(radius_vector[0] * reference_normal[1] - radius_vector[1] * reference_normal[0])

        self._torque_drive_parameter = Parameter(0.0)

        distribution = self.sim_params.torque_traction_distribution
        
        if distribution == 'linear':
            # Linear weight
            self._weight = x
                    
        if distribution == 'bipolar':
            # Create localized weight function near the rotation axis
            hinge_radius = self.geom_params.r_rod
            smoothing_width = max(1e-9, 0.5 * hinge_radius)
            core_weight = exp(-(x*x) / (smoothing_width*smoothing_width))
        
            # Split the weight into positive and negative regions using smooth Heaviside
            heaviside_smoothing = 0.1 * smoothing_width  
            smooth_heaviside = 0.5 * (1 + x / sqrt(x*x + heaviside_smoothing*heaviside_smoothing))
        
            weight_positive_side = core_weight * smooth_heaviside           # Right side weight
            weight_negative_side = core_weight * (1.0 - smooth_heaviside)   # Left side weight
        
            # --- Zero-mean bipolar distribution ---
            # Ensure the weight distribution has zero net force (pure torque)
            weight_difference = weight_positive_side - weight_negative_side
        
            # Remove mean to ensure ∫ w dA = 0 (no net force)
            rotation_edge_length = Integrate(1, self._mesh, definedon=self._mesh.Boundaries("rotation"))
            weight_mean = Integrate(weight_difference, self._mesh, definedon=self._mesh.Boundaries("rotation")) / rotation_edge_length
            self._weight = weight_difference - weight_mean
        
        # Traction amplitude scaled by zero-mean weight distribution
        self._traction_amplitude = self._torque_drive_parameter * self._weight
            
        # Applied traction in current configuration (includes surface jacobian)
        self._applied_traction = self._traction_amplitude * current_normal_unit * surface_jacobian
            
        # --- Effective moment arm calculation ---
        # Compute the effective lever arm for torque-to-parameter conversion
        self._effective_moment_arm = Integrate(self._weight * self._torque_moment_arm, 
                                               self._mesh, definedon=self._mesh.Boundaries("rotation"))

    def _setup_bilinear_form(self):
        # Bilinear form
        self._bfa = BilinearForm(self._fes)
        
        # Strain energy wall
        if self._with_contact:
            self._bfa += Variation( self._material_law_w(self._deformation_gradient_w(self._u),
                                                         self._u) * dx("wall") ).Compile()

        # Strain energy pendulum
        self._bfa += Variation(self._material_law_p(self._deformation_gradient_p(self._u),
                                                    self._u) * dx("pendulum")).Compile()
        
        # Rotation constraint
        self._bfa += (InnerProduct(self._u, self._p) + InnerProduct(self._v, self._q)) * ds('rotation')

        # Apply distributed traction for torque generation
        self._bfa += InnerProduct(self._applied_traction, self._v) * ds("rotation")
        
        # inertia
        self.tau = Parameter(self.sim_params.tau)
        vel_new = 2/self.tau * (self._u-self._gf_uold.components[0]) - self._gf_vold.components[0]
        acc_new = 2/self.tau * (vel_new-self._gf_vold.components[0]) - self._gf_aold.components[0]
        
        #  gravity force
        rhoA_p = self.rho_p * self.mat_params.thickness
        rhoA_w = self.rho_w * self.mat_params.thickness
        
        if self._with_contact:
            self._bfa += rhoA_w * InnerProduct(acc_new, self._v) * dx("wall")
        self._bfa += rhoA_p * InnerProduct(acc_new, self._v) * dx("pendulum")

        g = 9.81
        if self._use_gravity:
            self._bfa += InnerProduct(CF((0, rhoA_w*g)), self._v) * dx("wall")
            self._bfa += InnerProduct(CF((0, rhoA_p*g)), self._v) * dx("pendulum")
        
    #----------------------------------------------------------------------------
    # State methods for setting and getting simulation state
    #----------------------------------------------------------------------------
    def set_state(self, state: Dict[str, Any], t: float):
        if 'q' in state:
            theta = state['q']['value']
            if hasattr(theta, 'magnitude'): theta = theta.magnitude
            c, s = np.cos(theta), np.sin(theta)
            # rotated radius r0 = R(theta) * (X - P)
            r0 = CF((c * self._X_rel[0] - s * self._X_rel[1],
                 s * self._X_rel[0] + c * self._X_rel[1]))
            # rotated radius r0 = R(theta) * (X - P)
            r0 = CF((c * self._X_rel[0] - s * self._X_rel[1],
                 s * self._X_rel[0] + c * self._X_rel[1]))
            # displacement for initial position
            u0 = CF((r0[0] - self._X_rel[0],
                 r0[1] - self._X_rel[1]))
            # Update displacement grid function
            self._gf_u.components[0].Set(u0, definedon=self._mesh.Materials("pendulum"))
            self._gf_uold.vec[:] = self._gf_u.vec
            self._gf_u_history.AddMultiDimComponent(self._gf_u.components[0].vec)

        if 'omega' in state:
            omega = state['omega']['value']
            # Initial velocity: v0 = omega x r0
            v0 = CF((-omega * r0[1],
                      omega * r0[0]))
            # Update velocity grid function
            self._gf_v.components[0].Set(v0, definedon=self._mesh.Materials("pendulum"))
            self._gf_vold.vec[:] = self._gf_v.vec
            self._gf_v_history.AddMultiDimComponent(self._gf_v.components[0].vec)


        if 'alpha' in state:
            alpha = state['alpha']['value']
            a0 = CF((-alpha * r0[1],
                      alpha * r0[0]))
            # Update acceleration grid function
            self._gf_a.components[0].Set(a0, definedon=self._mesh.Materials("pendulum"))
            self._gf_aold.vec[:] = self._gf_a.vec

        if 'torque' in state:
            torque = state['torque']['value']
            # Apply the torque
            self.set_drive_torque(torque)        
        
    def get_state(self):
        state = {}
        q_state, omega_state, alpha_state = self._rigid_proxy()
        torque_state = self._get_torque_diagnostics()  # Remove sign flip
        state["q"] = {'value': q_state, 'unit': 'rad'}
        state["omega"] = {'value': omega_state, 'unit': 'rad/s'}
        state["alpha"] = {'value': alpha_state, 'unit': 'rad/s**2'}
        state["torque"] = {'value': torque_state, 'unit': 'N*m'}  # Correct unit
        return  state

    #----------------------------------------------------------------------------
    # Time stepping method
    #----------------------------------------------------------------------------
    def _do_step_internal(self, t, dt):
        """
        Advance FEM pendulum simulation from t to t+dt (called by base-class).
        """
        t_step_end = t + dt if t + dt < self.sim_params.t_end else self.sim_params.t_end
        
        with TaskManager():
            while t < t_step_end:
                # Time step update
                self._gf_uold.vec[:] = self._gf_u.vec
                self._gf_vold.vec[:] = self._gf_v.vec
                self._gf_aold.vec[:] = self._gf_a.vec
                
                # Update contact with the current displacement
                if self._with_contact:
                    self._contact.Update(self._gf_u.components[0], self._bfa, intorder=10, maxdist=0.5)
                    min_gap = self._get_contact_gap_distance()
                    self.w_gap.value = min_gap
                    # Reduce time step if pendulum is close to contact
                    if min_gap < 0.0005:
                        self.tau.Set(1e-4)
                    elif min_gap < 0.001:
                        self.tau.Set(5e-4)
                    elif min_gap < 0.01:
                        self.tau.Set(1e-3)
                    else:
                        self.tau.Set(self.sim_params.tau)
                
                # Adapt time step if exceeding end time
                if t + self.tau.Get() > t_step_end:
                    self.tau.Set(t_step_end - t)
                
                # Update time settings
                tau = self.tau.Get()
                t += tau
                self.w_time.value = t
                self.w_tau.value = tau
                
                # Solve nonlinear system with Newton               
                NewtonMinimization(a=self._bfa,
                                   u=self._gf_u,
                                   printing=False,
                                   inverse="sparsecholesky",
                                   maxerr=self.sim_params.max_err,
                                   maxit=self.sim_params.max_it
                                   )        

                # Update kinematic variables (velocity, acceleration)
                self._gf_v.vec[:] = 2/tau * (self._gf_u.vec-self._gf_uold.vec) - self._gf_vold.vec
                self._gf_a.vec[:] = 2/tau * (self._gf_v.vec-self._gf_vold.vec) - self._gf_aold.vec
                
                # Compute stress
                self._gf_sigma.Interpolate(self._sigma_law_p(self._deformation_gradient_p(self._gf_u.components[0]), self._u))

                # Store results in time series
                self._gf_u_history.AddMultiDimComponent(self._gf_u.components[0].vec)
                
                if self.anim_params.animate:
                    self.scene.Redraw()
                self._update_output_states(t)
                
    #----------------------------------------------------------------------------
    # Input/output methods
    #----------------------------------------------------------------------------
    def set_inputs(self, signals: Dict[str, Any], t: Optional[float]) -> None:
        for name, value in signals.items():
            if name in self.inputs:
                self.inputs[name].set(value, t=t)
                if name == 'torque':
                    self.set_drive_torque(value)
    
    def set_drive_torque(self, torque):
        """
        Set the drive torque by converting to the appropriate parameter value.
        
        Args:
            torque (float): Applied torque in N·m
        """
        if isinstance(torque, Quantity):
            torque_2d = torque.magnitude  # 2D torque per unit thickness
        else:
            torque_2d = float(torque)
        drive_parameter = torque_2d / self._effective_moment_arm
        self._torque_drive_parameter.Set(drive_parameter)
            
    def get_outputs(self) -> Dict[str, Any]:
        return {name: out_port.get() for name, out_port in self.outputs.items() if out_port.get() is not None}

    def _update_output_states(self, t: float):
        """
        Convert rigid-body proxy to output ports (called by base-class).
        """
        q_state, omega_state, alpha_state = self._rigid_proxy()
        q_state = q_state * ureg('rad')
        omega_state = omega_state * ureg('rad/s')
        alpha_state = alpha_state * ureg('rad/s^2')
        self.outputs['q'].set(q_state, t=t)
        self.outputs['omega'].set(omega_state, t=t)
        self.outputs['alpha'].set(alpha_state, t=t)

    #----------------------------------------------------------------------------
    # Reset method
    #----------------------------------------------------------------------------
    def reset(self):
        # Reset all grid functions and time series
        self._gf_u.vec[:] = 0
        self._gf_v.vec[:] = 0
        self._gf_a.vec[:] = 0
        self._gf_uold.vec[:] = 0
        self._gf_vold.vec[:] = 0
        self._gf_aold.vec[:] = 0
        self._gf_sigma.vec[:] = 0
        self._gf_u_history = GridFunction(self._V, multidim=0)
        self._gf_v_history = GridFunction(self._V, multidim=0)
        self._gf_stress_history = GridFunction(self._S, multidim=0)

    #----------------------------------------------------------------------------
    # Helpers for diagnostics and visualization
    #----------------------------------------------------------------------------
    def _get_contact_gap_distance(self):
        self._contact.Update(self._gf_u.components[0], self._bfa, intorder=10, maxdist=0.5)
        gap_vec_master = self._contact.gap
        n_master = self._contact.normal
        gap_n_master = InnerProduct(gap_vec_master, n_master)
        gap_values = []
        for el in self._mesh.Elements(BND):
            if el.mat == "contact_wall":
                trafo = self._mesh.GetTrafo(el)
                ir = IntegrationRule(el.type, order=3*self.mesh_params.mesh_order)
                for ip in ir:
                    mapped_ip = trafo(ip)
                    try:
                        gap_val = gap_n_master(mapped_ip)
                        gap_values.append(gap_val)
                    except:
                        continue
        min_gap = min(gap_values) if gap_values else 0.0
        return min_gap   

    def _rigid_proxy(self):
        r   = self._X_rel
        rhoA = self.rho_p * self.mat_params.thickness
        u   = self._gf_u.components[0]

        denom = Integrate(rhoA * InnerProduct(r, r),
                        self._mesh, definedon=self._mesh.Materials("pendulum"))

        s_num = Integrate(rhoA * (r[0]*u[1] - r[1]*u[0]),
                        self._mesh, definedon=self._mesh.Materials("pendulum"))
        c_num = Integrate(rhoA * InnerProduct(r, r + u),
                        self._mesh, definedon=self._mesh.Materials("pendulum"))

        s = s_num / denom   # ~ sin(theta)
        c = c_num / denom   # ~ cos(theta)

        theta = np.arctan2(s, c)
        
        # Angular velocity
        c, s = np.cos(theta), np.sin(theta)
        # rotated radius r = R(theta) * (X - P)
        r = CF((c * r[0] - s * r[1],
                s * r[0] + c * r[1]))
        
        v = self._gf_v.components[0]
        
        num_omega_x = Integrate( rhoA * v[0] * (-r[1]),
                           self._mesh, definedon=self._mesh.Materials("pendulum") )
        num_omega_y = Integrate( rhoA * v[1] * ( r[0]),
                           self._mesh, definedon=self._mesh.Materials("pendulum") )
        num_v = num_omega_x + num_omega_y
        omega = num_v / denom

        # Angular acceleration
        a = self._gf_a.components[0]
        num_alpha_x = Integrate( rhoA * a[0] * (-r[1]),
                           self._mesh, definedon=self._mesh.Materials("pendulum") )
        num_alpha_y = Integrate( rhoA * a[1] * ( r[0]),
                           self._mesh, definedon=self._mesh.Materials("pendulum") )
        num_a = num_alpha_x + num_alpha_y
        alpha = num_a / denom

        return theta, omega, alpha

    def _get_torque_diagnostics(self, return_force=False):
        """
        Compute the actual applied torque from the distributed traction.
        
        Args:
            return_force (bool): If True, also return force components
            
        Returns:
            float or tuple: Applied torque in N·m, optionally with (Fx, Fy, Mz)
        """
        # Calculate actual applied torque by integrating moment contributions
        effective_traction = self._traction_amplitude * self._torque_moment_arm
        applied_torque = Integrate(effective_traction, self._mesh, definedon=self._mesh.Boundaries("rotation"))
        if return_force:
            # Calculate net force components (should be near zero for pure torque)
            force_x = Integrate(self._applied_traction[0], self._mesh, definedon=self._mesh.Boundaries("rotation"))
            force_y = Integrate(self._applied_traction[1], self._mesh, definedon=self._mesh.Boundaries("rotation"))
            return force_x, force_y, applied_torque
        else:
            return applied_torque
    
    def calculate_energy(self):
        # Kinetic energy
        rhoA = self.rho_p * self.mat_params.thickness
        KE = 0.5 * Integrate( rhoA * InnerProduct(self._gf_v.components[0], self._gf_v.components[0]),
                              self._mesh, definedon=self._mesh.Materials("pendulum") )
        
        # Potential energy
        g = 9.81
        PE = Integrate( rhoA * g * self._gf_u.components[0][1],
                        self._mesh, definedon=self._mesh.Materials("pendulum") )
        
        # Strain energy
        SE = Integrate( self._material_law_p(self._deformation_gradient_p(self._gf_u.components[0]),
                                             self._u),
                        self._mesh, definedon=self._mesh.Materials("pendulum") )
        
        return KE, PE, SE
    
    #----------------------------------------------------------------------------
    # Visualization methods
    #----------------------------------------------------------------------------
    def setup_widgets(self) -> None:
        self.w_time = widgets.FloatText(value=0,
                                        description=f'Time: t / {self.sim_params.t_end} s',
                                        step=0.001,
                                        disabled=True)
        
        self.w_tau  = widgets.FloatText(value=self.sim_params.tau,
                                        description='Time Step: dt in s',
                                        step=0.0001,
                                        disabled=True)
        
        self.w_gap  = widgets.FloatText(value=0.0,
                                        description='Min. Gap in m',
                                        step=0.0001,
                                        disabled=True)


    def initialize_scene(self):
        self.scene = Draw(Norm(self._gf_sigma), self._mesh, "displacement",
                            deformation = self._gf_u.components[0], show=True)
    
    def update_scene(self, q, t):
        self.set_state({'q': {'value': q}}, t)            
        self.scene.Redraw()

    def visualize_state(self):
        # Displacement
        Draw(self._gf_u.components[0], deformation=True)
        
        # Velocity
        Draw(self._gf_v.components[0], deformation=self._gf_u.components[0], vectors=True)
        
        # Acceleration
        Draw(self._gf_a.components[0], deformation=self._gf_u.components[0], vectors=True)