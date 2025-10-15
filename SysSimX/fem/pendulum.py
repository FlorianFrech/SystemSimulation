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
from ipywidgets import Layout, HBox, VBox, HTML

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

        self._with_contact = self.geom_params.use_wall

        self._geo = None
        self._mesh = None

        self._setup_material_law()

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

    def _compute_mass(self):
        area = Integrate(1, self._mesh, definedon=self._mesh.Materials("pendulum"))
        self.mass = area * self.mat_params.thickness * self.rho_p

    def _compute_inertia(self):
        cx = cy = 0
        self._X_rel = CF((x - cx, y - cy))
        J_area = Integrate(self.rho_p * (self._X_rel[0]*self._X_rel[0] + self._X_rel[1]*self._X_rel[1]),
                           self._mesh, definedon=self._mesh.Materials("pendulum"))
        self.inertia = J_area * self.mat_params.thickness

    def _create_mesh(self):
        self._geo = PendulumGeometry(self.geom_params)._geo
        self._mesh = PendulumMesh(self._geo, self.mesh_params)._mesh
        self._compute_mass()
        self._compute_inertia()
    
    def initialize(self, t0: float):
        self.sim_params.t_start = t0
        
        self._initialize_fe_spaces()
        self._initialize_grid_functions()
        
        self.set_state(theta_deg=self.init_params.angular_position_deg,
                       omega=self.init_params.angular_velocity,
                       alpha=self.init_params.angular_acceleration)
        
        if self._with_contact:
            self._initialize_contact()

        self._initialize_torque_control()
        
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
        #display(Markdown(r"### Velocity in $\frac{m}{s}$"))
        #Draw(self._gf_v.components[0], deformation=self._gf_u.components[0], vectors=True)
        
        # Acceleration
        #display(Markdown(r"### Angular Acceleration in $\frac{m}{s}$"))
        #Draw(self._gf_a.components[0], deformation=self._gf_u.components[0], vectors=True)
        
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
        
    def _initialize_torque_control(self):        
        # Motor torque
        self._normal_rot = specialcf.normal(2)
        self._tangent_rot = CF((-self._normal_rot[1], self._normal_rot[0]))
        r = self._X_rel

        # Smooth localized weight near rotation axis
        sigma = max(1e-9, 0.5 * self.geom_params.r_rod)
        w_core = exp( -(x*x)/(sigma*sigma))

        # Smooth splitter into two patches
        delta = 0.1 * sigma
        H = 0.5 * (1 + x / sqrt(x*x + delta*delta)) # smooth Heaviside function
        self._w_plus = w_core * H                   # right patch weight
        self._w_minus = w_core * (1.0 - H)          # left patch weight
        
        self._cross_rn = -(r[0] * self._normal_rot[1] - r[1] * self._normal_rot[0])
        
        wdiff = self._w_plus - self._w_minus
        mean_w = Integrate(wdiff, self._mesh, definedon=self._mesh.Boundaries("rotation")) / Integrate(1, self._mesh, definedon=self._mesh.Boundaries("rotation"))
        wdiff0 = wdiff - mean_w
        self._q_drive = Parameter(0.0)
        self._t_drive = self._q_drive * wdiff0 * self._normal_rot
        self._D_pair = Integrate( wdiff0 * self._cross_rn,
                                  self._mesh, definedon=self._mesh.Boundaries("rotation"))

    def _get_torque_diagnostics(self, return_force=False):
        # Motor Torque chek
        Mz = Integrate(self._q_drive * (self._w_plus - self._w_minus) * self._cross_rn,
                            self._mesh, definedon=self._mesh.Boundaries("rotation"))
        if return_force:
            Fx = Integrate(self._t_drive[0], self._mesh, definedon=self._mesh.Boundaries("rotation"))
            Fy = Integrate(self._t_drive[1], self._mesh, definedon=self._mesh.Boundaries("rotation"))
            return Fx, Fy, Mz
        else:
            return Mz

    def _setup_bilinear_form(self):
        # Bilinear form
        self._bfa = BilinearForm(self._fes)


        if self._with_contact:
            self._bfa += Variation( self._material_law_w(self._deformation_gradient_w(self._u),
                                                         self._u) * dx("wall") ).Compile()

        # Strain energy pendulum
        self._bfa += Variation(self._material_law_p(self._deformation_gradient_p(self._u),
                                                    self._u) * dx("pendulum")).Compile()
        
        # Rotation constraint
        self._bfa += (InnerProduct(self._u, self._p) + InnerProduct(self._v, self._q)) * ds('rotation')
        
        self.tau = Parameter(self.sim_params.tau)
        vel_new = 2/self.tau * (self._u-self._gf_uold.components[0]) - self._gf_vold.components[0]
        acc_new = 2/self.tau * (vel_new-self._gf_vold.components[0]) - self._gf_aold.components[0]
        
        rhoA_p = self.rho_p * self.mat_params.thickness
        rhoA_w = self.rho_w * self.mat_params.thickness
        g = 9.81
        
        # inertia (mass matrix effect) and gravity force
        if self._with_contact:
            self._bfa += rhoA_w * InnerProduct(acc_new, self._v) * dx("wall")
            self._bfa += InnerProduct(CF((0, rhoA_w*g)), self._v) * dx("wall")

        self._bfa += rhoA_p * InnerProduct(acc_new, self._v) * dx("pendulum")
        self._bfa += InnerProduct(CF((0, rhoA_p*g)), self._v) * dx("pendulum")
        
        # Add traction (torque generating) to bfa as Neumann term on the rotation boundary
        self._bfa += InnerProduct(self._t_drive, self._v) * ds("rotation")
    
    def initialize_scene(self, qref=0.0):
        header = HTML("<h3 style='color:#1565c0; font-family:sans-serif; margin-bottom:10px; text-align:center;'>Simulation Diagnostics</h3>")
        
        self._widget_time   = widgets.FloatText(value=self.sim_params.t_start, description=f'Time: t / {self.sim_params.t_end} s', step=0.001, disabled=True)
        self._widget_tau    = widgets.FloatText(value=self.sim_params.tau, description='Time Step: τ in s', step=0.0001, disabled=True)
        self._widget_mode   = widgets.Text(value="", description="Mode:", disabled=True)
        self._widget_ref    = widgets.FloatText(value=0.0, description='Ref. pos in deg', step=0.001, disabled=True)
        self._widget_theta  = widgets.FloatText(value=0.0, description='Theta: θ in deg', step=0.001, disabled=True)
        self._widget_omega  = widgets.FloatText(value=0.0, description='Omega: ω in rad/s', step=0.01, disabled=True)
        self._widget_torque = widgets.FloatText(value=0.0, description='Torque: Mz in Nm', step=0.01, disabled=True)
        
        if self._with_contact:
            self._widget_gap  = widgets.FloatText(value=0.0, description='Min. Gap in m', step=0.0001, disabled=True)
            self._widgets = [self._widget_time, self._widget_tau, self._widget_mode, self._widget_ref,
                             self._widget_theta, self._widget_omega, self._widget_torque, self._widget_gap]
        
        else:   
            self._widgets = [self._widget_time, self._widget_tau, self._widget_mode, self._widget_ref,
                             self._widget_theta, self._widget_omega, self._widget_torque]
        
        for w in self._widgets:
            w.layout.width = '350px'
            w.layout.margin = '8px 0px 8px 0px'
            w.layout.align_self = 'center'
            w.layout.display = 'flex'
            w.layout.flex_direction = 'column'
            w.style.description_width = '120px'
            w.style.font_weight = 'bold'
            w.style.font_size = '16px'
            w.style.background = '#f5f7fa'
            w.style.border = '1px solid #cfd8dc'
            w.style.border_radius = '8px'
            w.style.padding = '6px 12px'
            w.style.color = '#263238'
            w.style.text_align = 'right'
            
        vbox = VBox([header] + self._widgets)
        display(vbox)        
        self._scene = Draw(Norm(self._gf_sigma), self._mesh, "displacement",
                           deformation = self._gf_u.components[0])

    def _update_widgets(self, mode="FEM", t=0.0, q_ref_rad=0, q_state_rad=0.0, omega_state=0.0, torque=0.0):
        self._widget_time.value = t  
        self._widget_mode.value = mode
        self._widget_ref.value = np.rad2deg(q_ref_rad)
        self._widget_theta.value = np.rad2deg(q_state_rad)
        self._widget_omega.value = omega_state
        self._widget_torque.value = torque

    def step(self, t, h, qref):
        t_step_end = t + h if t + h < self.sim_params.t_end else self.sim_params.t_end
        self._widget_ref.value = np.rad2deg(qref)
        
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
                    self._widget_gap.value = min_gap
                    # Reduce time step if pendulum is close to contact
                    if min_gap < 0.0005:
                        self.tau.Set(1e-3)
                    elif min_gap < 0.001:
                        self.tau.Set(1e-3)
                    elif min_gap < 0.01:
                        self.tau.Set(5e-3)
                    else:
                        self.tau.Set(self.sim_params.tau)
                
                # Update time settings
                tau = self.tau.Get()
                t += tau
                self._widget_time.value = t
                self._widget_tau.value = tau
                
                # Solve nonlinear system with Newton               
                NewtonMinimization(a=self._bfa,
                                   u=self._gf_u,
                                   printing=False,
                                   inverse="sparsecholesky",
                                   maxerr=1e-6, maxit=20)        

                # Update kinematic variables (velocity, acceleration)
                self._gf_v.vec[:] = 2/tau * (self._gf_u.vec-self._gf_uold.vec) - self._gf_vold.vec
                self._gf_a.vec[:] = 2/tau * (self._gf_v.vec-self._gf_vold.vec) - self._gf_aold.vec
                
                # Compute stress
                self._gf_sigma.Interpolate(self._sigma_law_p(self._deformation_gradient_p(self._gf_u.components[0]), self._u))

                # Store results in time series
                self._gf_u_history.AddMultiDimComponent(self._gf_u.components[0].vec)
                
                # Increment frame counter and redraw
                self._scene.Redraw()
                
                # Update widget values
                Mz = self._get_torque_diagnostics()
                q_state, omega_state = self._rigid_proxy()
                self._update_widgets(t=t,
                                     q_ref_rad=qref,
                                     q_state_rad=q_state,
                                     omega_state=omega_state,
                                     torque=Mz)
    
    def update_scene(self, state):
        t, q_ref, q_state, omega_state, torque, mode = state
        self._update_widgets(mode=mode, t=t, q_ref_rad=q_ref, q_state_rad=q_state, omega_state=omega_state, torque=torque)
        theta_deg = np.rad2deg(q_state)        
        self.set_state(theta_deg=theta_deg, omega=omega_state)
        self._scene.Redraw()
    
    def _get_contact_gap_distance(self):
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
    
    def set_drive_torque(self, torque):
        Mz_2d = float(torque) #/ self.mat_params.thickness
        q = Mz_2d / self._D_pair
        self._q_drive.Set(q)
    
    def set_inputs(self, **signals: float):
        if 'torque' in signals:
            self.set_drive_torque(signals['torque'])
            
    def get_outputs(self) -> Dict[str, float]:
        q_state, omega_state = self._rigid_proxy()
        return {'q_state': q_state, 'omega_state': omega_state}

    def reinitialize(self, t, q_state, omega_state):
        self.sim_params.t_start = t
        theta_deg = np.rad2deg(q_state)
        self.set_state(theta_deg=theta_deg, omega=omega_state)
        pass

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