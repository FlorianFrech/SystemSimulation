from typing import Dict, Any, Optional

from SysSimX.core.port import PortSpec, PortType, PortState
from SysSimX.core.base import CoSimComponent
from SysSimX.components.fem_comp import FEMComponent
from SysSimX.utilities.units import ureg

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
    "torque": PortSpec("torque", PortType.REAL, direction="in", unit="N*m")
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
        
        # Initialize port states based on specifications
        for spec in self.input_specs.values():
            self.inputs[spec.name] = PortState(spec)
        for spec in self.output_specs.values():
            self.outputs[spec.name] = PortState(spec)

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
    def initialize(self, t0:float):
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

        self._update_output_states(t=t0)
    
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
        # Displacement/velocity/accel space (vector H1), and the two scalars already used on 'rotation'
        self._V = VectorH1(self._mesh, order=self.mesh_params.mesh_order, dirichlet="fix")
        self._Q = NumberSpace(self._mesh, definedon=self._mesh.Boundaries('rotation'))  # existing pair

        # NEW: global scalar for generalized hinge rotation (lambda) and its Lagrange multiplier (m)
        self._R = NumberSpace(self._mesh)  # lambda
        self._M = NumberSpace(self._mesh)  # m

        # Mixed FE space: [u,q] × [lambda] × [m]
        self._fes = self._V * self._Q* self._Q * self._R * self._M
        (self._u, self._q1, self._q2, self._lambda, self._m), (self._v, self._p1, self._p2, self._eta, self._mu) = self._fes.TnT()

        # Stress space (unchanged)
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
        # reference radius
        r = self._X_rel                          # 2-vector CF

        # surface deformation gradient on the boundary (IMPORTANT: .Trace())
        F_s = Id(2) + Grad(self._u).Trace()      # 2x2

        # map r to current tangent frame
        v = F_s * r                              # 2-vector

        # 90° rotation without a matrix multiply (avoid dims issues)
        def rot90(vec):                          # returns J*vec = (-vec_y, vec_x)
            return CF((-vec[1], vec[0]))

        phi_foll = rot90(v)                      # follower measurement vector (2-vector)

        # --- normalization MUST NOT depend on the trial function ---
        # use a purely reference quantity for the scale:
        # since J is orthonormal, <J r, J r> = <r, r>
        Lr   = Integrate(1, self._mesh, definedon=self._mesh.Boundaries("rotation"))
        Cint = Integrate(InnerProduct(r, r),      # <-- reference-only
                        self._mesh, definedon=self._mesh.Boundaries("rotation"))
        Cavg = Cint / Lr
        if abs(Cavg) < 1e-12:
            raise RuntimeError("Hinge normalization ~ 0. Check rotation boundary and pivot.")

        self._phi_rot = phi_foll / Cavg          # follower + properly scaled

        # generalized torque parameter (unchanged)
        self._Mz = Parameter(0.0)
        
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
        p_vec = CF((self._p1, self._p2))
        q_vec = CF((self._q1, self._q2))
        self._bfa += (InnerProduct(self._u, p_vec) + InnerProduct(self._v, q_vec)) * ds('rotation')

        # Compute the tangent in the current (deformed) configuration
        # The deformation gradient for the boundary
        F = Id(2) + Grad(self._u).Trace()
        cofF = Cof(F)
        N = specialcf.normal(2)
        
        # Surface Jacobian (stretch of the boundary element)
        J_s = Norm(cofF * N)
        
        # Hinge rotation constraint with torque applied in current configuration
        # The virtual work of the torque is: δW = Mz * δλ
        # The constraint is: ∫ φ · u ds = λ (scaled appropriately)
        E_hinge = (self._m * (InnerProduct(self._phi_rot, self._u) * J_s - self._lambda) 
                - self._Mz * self._lambda)
        self._bfa += Variation(E_hinge * ds("rotation"))

        eps = 1e-12
        self._bfa += Variation(0.5 * eps * self._lambda * self._lambda * ds("rotation"))
        
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
        theta = state['q']['value']
        omega = state['omega']['value']
        torque = -1 * state['torque']['value']       
         
        c, s = np.cos(theta), np.sin(theta)
        
        # rotated radius r0 = R(theta) * (X - P)
        r0 = CF((c * self._X_rel[0] - s * self._X_rel[1],
                 s * self._X_rel[0] + c * self._X_rel[1]))

        # displacement for initial position
        u0 = CF((r0[0] - self._X_rel[0],
                 r0[1] - self._X_rel[1]))

        # Initial velocity: v0 = omega x r0
        v0 = CF((-omega * r0[1],
                  omega * r0[0]))
        
        # Apply the torque
        self.set_drive_torque(torque)
        
        # Set field ICs
        self._gf_u.components[0].Set(u0, definedon=self._mesh.Materials("pendulum"))
        self._gf_v.components[0].Set(v0, definedon=self._mesh.Materials("pendulum"))

        # IMPORTANT: set generalized coords too
        self._gf_u.components[3].vec[0] = theta   # λ
        self._gf_v.components[3].vec[0] = omega   # λ̇
        self._gf_a.components[3].vec[0] = 0.0     # λ̈ (if needed)

        # Copy to "old"
        self._gf_uold.vec[:] = self._gf_u.vec
        self._gf_vold.vec[:] = self._gf_v.vec
        self._gf_aold.vec[:] = self._gf_a.vec

        # History
        self._gf_u_history.AddMultiDimComponent(self._gf_u.components[0].vec)
        self._gf_v_history.AddMultiDimComponent(self._gf_v.components[0].vec)

    def get_state(self):
        state = {}
        q_state, omega_state, _ = self._rigid_proxy()
        torque_state = -self._get_torque_diagnostics()
        state["q"] = {'value': q_state, 'unit': 'rad'}
        state["omega"] = {'value': omega_state, 'unit': 'rad/s'}
        state["torque"] = {'value': torque_state, 'unit': 'rad/s^2'}
        return  state

    #----------------------------------------------------------------------------
    # Time stepping method
    #----------------------------------------------------------------------------
    def do_step(self, t, dt):
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
                    self._widget_gap.value = min_gap
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
                self._widget_time.value = t
                self._widget_tau.value = tau
                
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
                    self._scene.Redraw()
                
                # Update widget values
                Mz = self._get_torque_diagnostics()
                q_state, omega_state, alpha_state = self._rigid_proxy()
                self._update_widgets(t=t,
                                     q_ref_rad=0.0,
                                     q_state_rad=q_state,
                                     omega_state=omega_state,
                                     alpha_state=alpha_state,
                                     torque=Mz)
                self._update_output_states(t=t)

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
        # torque is expected in N*m (out-of-plane, z)
        Mz_2d = float(torque) / self.mat_params.thickness
        self._Mz.Set(Mz_2d)
            
    def get_outputs(self) -> Dict[str, Any]:
        return {name: out_port.get() for name, out_port in self.outputs.items() if out_port.get() is not None}

    def _update_output_states(self, t: float):
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
        theta = float(self._gf_u.components[3].vec[0])  # lambda
        omega = float(self._gf_v.components[3].vec[0])  # dot{lambda}
        alpha = float(self._gf_a.components[3].vec[0])  # ddot{lambda}

        return theta, omega, alpha
    
    def _get_torque_diagnostics(self, return_force=False):
        m_val = float(self._gf_u.components[4].vec[0]) * self.mat_params.thickness  # m (scaled back to 3D)
        return m_val
    
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
    def setup_simulation_diagnostics(self, qref=0.0):
        header = HTML("<h3 style='color:#1565c0; font-family:sans-serif; margin-bottom:10px; text-align:center;'>Simulation Diagnostics</h3>")
        
        theta, omega, alpha = self._rigid_proxy()
        torque = self._get_torque_diagnostics()

        self._widget_time   = widgets.FloatText(value=self.sim_params.t_start, description=f'Time: t / {self.sim_params.t_end} s', step=0.001, disabled=True)
        self._widget_tau    = widgets.FloatText(value=self.sim_params.tau, description='Time Step: dt in s', step=0.0001, disabled=True)
        self._widget_mode   = widgets.Text(value="", description="Mode:", disabled=True)
        self._widget_ref    = widgets.FloatText(value=0.0, description='Ref. pos in deg', step=0.001, disabled=True)
        self._widget_theta  = widgets.FloatText(value=np.rad2deg(theta), description='Ang. Pos: θ in deg', step=0.001, disabled=True)
        self._widget_omega  = widgets.FloatText(value=omega, description='Ang. Vel: ω in rad/s', step=0.01, disabled=True)
        self._widget_alpha  = widgets.FloatText(value=alpha, description='Ang. Acc: α in rad/s²', step=0.01, disabled=True)
        self._widget_torque = widgets.FloatText(value=torque, description='Torque: Mz in Nm', step=0.01, disabled=True)
        self._widget_gap    = widgets.FloatText(value=0.0, description='Min. Gap in m', step=0.0001, disabled=True)

        self._widgets = [self._widget_time, self._widget_tau,
                         self._widget_mode, self._widget_ref,
                         self._widget_theta, self._widget_omega,
                         self._widget_alpha, self._widget_torque,
                         self._widget_gap]

        h_box_time = HBox([self._widget_time, self._widget_tau])
        h_box_mode = HBox([self._widget_mode, self._widget_ref])
        h_box_state1 = HBox([self._widget_theta, self._widget_omega])
        h_box_state2 = HBox([self._widget_alpha, self._widget_torque])
        h_box_contact = HBox([self._widget_gap])
        if self._with_contact:
            self._hboxes = [h_box_time, h_box_mode, h_box_state1, h_box_state2, h_box_contact]
        else:
            self._hboxes = [h_box_time, h_box_mode, h_box_state1, h_box_state2]

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

        # Create a vertical box layout to hold all widgets
        vbox = VBox([header] + self._hboxes,
                    layout=Layout(
                        width='710px',
                        display='flex',
                        flex_direction='column',
                        justify_content='center',
                        align_items='stretch',
                        margin='0 auto',
                        align_self='center'
                    ))

        display(vbox)
        
        self._scene = Draw(Norm(self._gf_sigma), self._mesh, "displacement",
                           deformation = self._gf_u.components[0], show=True)     

    def _update_widgets(self, mode="FEM", t=0.0, q_ref_rad=0, q_state_rad=0.0, omega_state=0.0, alpha_state=0.0, torque=0.0):
        self._widget_time.value = t  
        self._widget_mode.value = mode
        self._widget_ref.value = np.rad2deg(q_ref_rad)
        self._widget_theta.value = np.rad2deg(q_state_rad)
        self._widget_omega.value = omega_state
        self._widget_alpha.value = alpha_state
        self._widget_torque.value = torque

    def update_scene(self, state):
        t, q_ref, q_state, omega_state, alpha_state, torque, mode = state
        self._update_widgets(mode=mode, t=t, q_ref_rad=q_ref, q_state_rad=q_state, omega_state=omega_state, alpha_state=alpha_state, torque=torque)
        theta_deg = np.rad2deg(q_state)
        self.set_state(theta_deg=theta_deg, omega=omega_state)
        self._scene.Redraw()

    def visualize_state(self):
        # Displacement
        Draw(self._gf_u.components[0], deformation=True)
        
        # Velocity
        Draw(self._gf_v.components[0], deformation=self._gf_u.components[0], vectors=True)
        
        # Acceleration
        Draw(self._gf_a.components[0], deformation=self._gf_u.components[0], vectors=True)