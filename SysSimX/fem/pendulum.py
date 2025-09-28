from .config.config import GeometryParameters, MaterialParameters, MeshParameters, InitialConditionParameters, ContactParameters, SimulationParameters, AnimationParameters
from .geometry.geometry_builder import PendulumGeometry
from .geometry.mesh_builder import PendulumMesh
from .materials.neo_hookean import NeoHookeanMaterial
from .materials.linear_elastic import LinearElasticMaterial

import numpy as np
from ngsolve import *
from ngsolve.webgui import Draw
from netgen.occ import *
from ngsolve.solvers import NewtonMinimization
from IPython.display import display, Markdown
import ipywidgets as widgets

from typing import Dict

class FEMPendulum:
    def __init__(self,
                 geom_params: GeometryParameters = GeometryParameters(),
                 mat_params: MaterialParameters = MaterialParameters(),
                 mesh_params: MeshParameters = MeshParameters(),
                 init_params: InitialConditionParameters = InitialConditionParameters(),
                 contact_params: ContactParameters = ContactParameters(),
                 sim_params: SimulationParameters = SimulationParameters(),
                 anim_params: AnimationParameters = AnimationParameters()):
        self.geom_params = geom_params
        self.mat_params = mat_params
        self.mesh_params = mesh_params
        self.init_params = init_params
        self.contact_params = contact_params
        self.sim_params = sim_params
        self.anim_params = anim_params

        self._geo = PendulumGeometry(self.geom_params)._geo
        self._mesh = PendulumMesh(self._geo, self.mesh_params)._mesh

        self._setup_material_law()
        self._compute_mass()
        self._compute_inertia()

    def _setup_material_law(self):
        self.E_p, self.E_w     = self.mat_params.E_pendulum, self.mat_params.E_wall
        self.nu_p, self.nu_w   = self.mat_params.nu_pendulum, self.mat_params.nu_wall
        self.rho_p, self.rho_w = self.mat_params.rho_pendulum, self.mat_params.rho_wall
        
        self._material_wall = LinearElasticMaterial(self.E_w, self.nu_w)
        
        self._mat_type_pendulum = self.mat_params.material_type
        self._mat_type_wall = "Linear Elastic"  # wall is always linear elastic

        if self._mat_type_pendulum == "Neo-Hookean":
            self._material_pendulum = NeoHookeanMaterial(self.E_p, self.nu_p)
            self._deformation_gradient = self._material_pendulum.C
            self._material_law = self._material_pendulum.energy_density
            self._sigma_law = self._material_pendulum.sigma
        elif self._mat_type_pendulum == "Linear Elastic":
            self._material_pendulum = LinearElasticMaterial(self.E_p, self.nu_p)
            self._deformation_gradient = self._material_pendulum.eps
            self._material_law = self._material_pendulum.energy_density
            self._sigma_law = self._material_pendulum.sigma
        else:
            raise ValueError(f"Unknown material type: {self.mat_params.material_type}")
        pass

    def _compute_mass(self):
        area = Integrate(1, self._mesh, definedon=self._mesh.Materials("pendulum"))
        self.mass = area * self.mat_params.thickness * self.rho_p

    def _compute_inertia(self):
        cx = cy = 0
        self._X_rel = CF((x - cx, y - cy))
        J_area = Integrate(self.rho_p * (self._X_rel[0]*self._X_rel[0] + self._X_rel[1]*self._X_rel[1]),
                           self._mesh, definedon=self._mesh.Materials("pendulum"))
        self.inertia = J_area * self.mat_params.thickness
    
    def initialize(self, t0: float):
        self.sim_params.t_start = t0

        self._setup_material_law()
        
        self._compute_mass()
        self._compute_inertia()
        
        self._initialize_fe_spaces()
        self._initialize_grid_functions()
        
        self.set_state(theta_deg=self.init_params.angular_position_deg,
                       omega=self.init_params.angular_velocity,
                       alpha=self.init_params.angular_acceleration)
        
        self._initialize_contact()
        
        self._setup_bilinear_form()
        pass
    
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
        
        self._setup_material_law()      
        
        pass
    
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
    
    def set_state(self, theta_deg=0, omega=0, alpha=0):        
        theta_rad = np.deg2rad(theta_deg)
        c, s = np.cos(theta_rad), np.sin(theta_rad)
        
        # rotated radius r0 = R(theta) * (X - P)
        r0 = CF((c * self._X_rel[0] - s * self._X_rel[1],
                 s * self._X_rel[0] + c * self._X_rel[1]))

        # displacement for initial position
        u0 = CF((r0[0] - self._X_rel[0],
                 r0[1] - self._X_rel[1]))

        # Initial velocity: v0 = omega x r0
        v0 = CF((-omega * r0[1],
                  omega * r0[0]))
        
        # Initial acceleration: a0 = alpha x r0
        a0 = CF(( -alpha * r0[1],
                   alpha * r0[0] ))
        
        self._torque = 0.0  # initial torque
        
        # Set initial conditions
        self._gf_u.components[0].Set(u0, definedon=self._mesh.Materials("pendulum"))
        self._gf_v.components[0].Set(v0, definedon=self._mesh.Materials("pendulum"))
        self._gf_a.components[0].Set(a0, definedon=self._mesh.Materials("pendulum"))

        # Copy to "old" variables
        self._gf_uold.vec[:] = self._gf_u.vec
        self._gf_vold.vec[:] = self._gf_v.vec
        self._gf_aold.vec[:] = self._gf_a.vec
        
        # Add to history
        self._gf_u_history.AddMultiDimComponent(self._gf_u.components[0].vec)
        self._gf_v_history.AddMultiDimComponent(self._gf_v.components[0].vec)
        
    def visualize_state(self):
        # Displacement
        display(Markdown(r"### Displacement in $m$"))
        Draw(self._gf_u.components[0], deformation=True)
        
        # Velocity
        display(Markdown(r"### Velocity in $\frac{m}{s}$"))
        Draw(self._gf_v.components[0], deformation=self._gf_u.components[0], vectors=True)
        
        # Acceleration
        display(Markdown(r"### Angular Acceleration in $\frac{m}{s}$"))
        Draw(self._gf_a.components[0], deformation=self._gf_u.components[0], vectors=True)
        
    
    def _initialize_contact(self):
        kn = self.contact_params.kn
        gap_type = self.contact_params.gap_type
        
        master = self._mesh.Boundaries("contact_wall")
        slave = self._mesh.Boundaries("contact_head")
        self._contact = ContactBoundary(master, slave)

        u = self._u
        u_old = self._gf_uold.components[0]
    
        X_M = CoefficientFunction((x,y))
        X_S = X_M.Other()
        n_S = -specialcf.normal(2).Other()
        
        if gap_type == "absolute":
            cur_pos_master = X_M + u
            cur_pos_slave = X_S + u.Other()
            self._cf = (cur_pos_master - cur_pos_slave) * n_S
        
        elif gap_type == "incremental":
            increment_master = X_M + u - u_old
            increment_slave = X_S + u.Other() - u_old.Other()
            self._cf = (increment_master - increment_slave) * n_S

        penalty_energy = kn * self._cf * self._cf
        self._contact.AddEnergy(IfPos(self._cf, penalty_energy, 0), deformed = True)

    def _setup_bilinear_form(self):
        # Bilinear form
        self._bfa = BilinearForm(self._fes)
        
        # Strain energy wall (always linear elastic)
        ed_w = self._material_wall.energy_density
        eps_w = self._material_wall.eps
        self._bfa += Variation(ed_w(eps_w(self._u)) * dx("wall")).Compile()
        
        # Strain energy pendulum (material law configurable)
        self._bfa += Variation(self._material_law(self._deformation_gradient(self._u), self._u) * dx("pendulum")).Compile()
        
        # Rotation constraint
        self._bfa += (InnerProduct(self._u, self._p) + InnerProduct(self._v, self._q)) * ds('rotation')
        
        self.tau = self.sim_params.tau
        vel_new = 2/self.tau * (self._u-self._gf_uold.components[0]) - self._gf_vold.components[0]
        acc_new = 2/self.tau * (vel_new-self._gf_vold.components[0]) - self._gf_aold.components[0]
        
        rhoA_p = self.rho_p * self.mat_params.thickness
        rhoA_w = self.rho_w * self.mat_params.thickness
        g = 9.81
        
        # inertia (mass matrix effect)
        self._bfa += rhoA_p * InnerProduct(acc_new, self._v) * dx("pendulum")
        self._bfa += rhoA_w * InnerProduct(acc_new, self._v) * dx("wall")
        
        # gravity force
        self._bfa += InnerProduct(CF((0, rhoA_p*g)), self._v) * dx("pendulum")
        self._bfa += InnerProduct(CF((0, rhoA_w*g)), self._v) * dx("wall")
        
        # torque from motor on pendulum around rotation axis
        self._alpha_param = Parameter(0.0)
        b_alpha = self.rho_p * CF( (-self._alpha_param * self._X_rel[1], self._alpha_param * self._X_rel[0]) )
        self._bfa += InnerProduct(b_alpha, self._v) * dx("pendulum")
    
    def initialize_scene(self, qref=0.0):
        # Display Title and Scene
        display(Markdown(r"### Pendulum Simulation: Stress and Displacement"))
        self._scene = Draw(Norm(self._gf_sigma), self._mesh, "displacement",
                            deformation = self._gf_u.components[0])
        # Display Mode
        self._mode_widget = widgets.Text(value=f"Mode: FEM")
        display(self._mode_widget)
        
        # Display Current Time
        self._time_widget = widgets.Text(value=f"Time: 0.0 / {self.sim_params.t_end}s")
        display(self._time_widget)

        # Display Current Torque
        self._torque_widget = widgets.Text(value=f"Torque: {self._torque:.2f} Nm")
        display(self._torque_widget)

        # Display Reference Angle
        self._ref_widget = widgets.Text(value=f"q_ref: {np.rad2deg(qref):.2f} deg")
        display(self._ref_widget)
        
        # Display Angular Position and Angular Velocity
        theta, omega = self._rigid_proxy()
        self._state_widget = widgets.Text(value=f"q: {np.rad2deg(theta):.2f} deg\t"
                                                f"omega: {omega:.2f} rad/s")
        display(self._state_widget)

    def step(self, t, h, qref=None):
        t_step_end = t + h if t + h < self.sim_params.t_end else self.sim_params.t_end
        with TaskManager():
            while t < t_step_end:
                t += self.tau

                self._mode_widget.value = f"Mode: FEM"
                self._time_widget.value = f"Time: {t:.4f} / {self.sim_params.t_end}s"
                # Time step update
                self._gf_uold.vec[:] = self._gf_u.vec
                self._gf_vold.vec[:] = self._gf_v.vec
                self._gf_aold.vec[:] = self._gf_a.vec
                
                # Set motor torque parameter for this time step
                self._alpha_param.Set(-self._torque / self.inertia)

                # Update contact with the current displacement
                self._contact.Update(self._gf_u.components[0], self._bfa, 5, 0.01)
                
                # Solve nonlinear system with Newton               
                NewtonMinimization(a=self._bfa, u=self._gf_u, printing=False, inverse="sparsecholesky")          

                # Update kinematic variables (velocity, acceleration)
                self._gf_v.vec[:] = 2/self.tau * (self._gf_u.vec-self._gf_uold.vec) - self._gf_vold.vec
                self._gf_a.vec[:] = 2/self.tau * (self._gf_v.vec-self._gf_vold.vec) - self._gf_aold.vec
                
                # Compute stress
                self._gf_sigma.Interpolate(self._sigma_law(self._deformation_gradient(self._gf_u.components[0]), self._u))
                
                # Store results in time series
                self._gf_u_history.AddMultiDimComponent(self._gf_u.components[0].vec)
                self._gf_v_history.AddMultiDimComponent(self._gf_v.components[0].vec)
                self._gf_stress_history.AddMultiDimComponent(self._gf_sigma.vec)
                
                # Increment frame counter and redraw
                self._scene.Redraw()
                
                # Update widget values
                if qref is not None:
                    self._ref_widget.value = f"Ref. Angle: {np.rad2deg(qref):.2f} deg"
                self._torque_widget.value = f"Torque: {self._torque:.2f} Nm"
                theta, omega = self._rigid_proxy()
                self._state_widget.value = f"theta: {np.rad2deg(theta):.2f} deg, omega: {omega:.2f} rad/s"
    
    def update_scene(self, state):
        t, q_ref, q_state, omega_state, torque, mode = state
        theta_deg = np.rad2deg(q_state)
        
        self._mode_widget.value = f"Mode: {mode}"
        self._time_widget.value = f"Time: {t:.4f} / {self.sim_params.t_end} s"
        self._torque_widget.value = f"Torque: {torque:.2f} Nm"
        self._ref_widget.value = f"q_ref: {np.rad2deg(q_ref):.2f} deg"
        self._state_widget.value = f"q: {theta_deg:.2f} deg\tomega: {omega_state:.2f} rad/s"
        
        self.set_state(theta_deg=theta_deg, omega=omega_state)
        self._scene.Redraw()
        

    def _rigid_proxy(self):
        r = self._X_rel
        rhoA = self.rho_p * self.mat_params.thickness
        
        # Angular position
        u = self._gf_u.components[0]
        num_u = Integrate( rhoA * (r[0] * u[1] - r[1] * u[0]),
                           self._mesh, definedon=self._mesh.Materials("pendulum") )
        denom = Integrate( rhoA * InnerProduct(r, r),
                           self._mesh, definedon=self._mesh.Materials("pendulum") )
        theta = np.arcsin(np.clip(num_u / denom, -1, 1))
        
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

        return theta, omega
    
    def set_inputs(self, **signals: float):
        if 'torque' in signals:
            self._torque = signals['torque']
            
    def get_outputs(self) -> Dict[str, float]:
        theta, omega = self._rigid_proxy()
        return {'q': theta, 'omega': omega}
            