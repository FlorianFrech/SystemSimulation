from .config import GeometryParameters, MaterialParameters, MeshParameters, InitialConditionParameters, ContactParameters, SimulationParameters, AnimationParameters
from .material_laws import eps, C, linear_elastic, neo_hooke, sigma_neo_hooke, von_mises_2d, sigma_linear, 

import numpy as np
from ngsolve import *
from ngsolve.webgui import Draw
from netgen.occ import *
from ngsolve.solvers import NewtonMinimization

class SimpleFEMPendulum:
    def __init__(self):
        # Parameters
        self.geom_params    = GeometryParameters()
        self.mat_params     = MaterialParameters()
        self.mesh_params    = MeshParameters()
        self.init_params    = InitialConditionParameters()
        self.contact_params = ContactParameters()
        self.sim_params     = SimulationParameters()
        self.anim_params    = AnimationParameters()
        
        # Internal states
        self._mesh = None
        self._fes = None
        self._contact = None
        self._material_law = None
        self._simulation_results = []
        
        # Grid Functions
        self._gf_u = None
        self._gf_v = None
        self._gf_a = None
        self._gf_uold = None
        self._gf_vold = None
        
        # Results history
        self._gf_u_history = None
        self._gf_v_history = None
        
        self._setup_material_law()

        pass
    
    def _setup_material_law(self):
        self.E_p, self.E_w     = self.mat_params.E_pendulum, self.mat_params.E_wall
        self.nu_p, self.nu_w   = self.mat_params.nu_pendulum, self.mat_params.nu_wall
        self.rho_p, self.rho_w = self.mat_params.rho_pendulum, self.mat_params.rho_wall
        
        # Lamé parameters
        self.mu_p = self.E_p / 2 / (1+self.nu_p)
        self.lam_p = self.E_p * self.nu_p / ((1+self.nu_p)*(1-2*self.nu_p))
        self.mu_w = self.E_w / 2 / (1+self.nu_w)
        self.lam_w = self.E_w * self.nu_w / ((1+self.nu_w)*(1-2*self.nu_w))
        
        if self.mat_params.material_law == "linear_elastic":
            self._deformation_tensor = self.eps
            self._material_law = self.linear_elastic
        
        elif self.mat_params.material_law == "neo_hookean":
            self._deformation_tensor = self.C
            self._material_law = self.neo_hooke
        pass
    
    def create_mesh(self):
        self._create_geometry()
        
        mp = self.mesh_params

        self._mesh = Mesh(OCCGeometry(self._geo, dim=2).GenerateMesh(maxh=mp.max_element_size))

        if mp.curved_elements:
            self._mesh.Curve(mp.mesh_order)
        
        for _ in range(mp.refinement_levels):
            self._mesh.Refine()
    
    def _create_geometry(self):
        gp = self.geom_params

        bar = MoveTo(-gp.r_rod,0).Rectangle(2*gp.r_rod, gp.l_center).Face()
        bar.edges.Min(Y).name="rotation"
        bar.faces.name="bar"
        bar.faces.maxh=gp.r_rod/2

        hole = Circle((0, gp.l_center), gp.r_hole).Face()
        hole.faces.name="hole"
        hole.edges.maxh=gp.r_head/20

        circ = Circle((0, gp.l_center), gp.r_head).Face()
        circ.edges.maxh=gp.r_head/20
        circ.faces.name="circ"
        circ.faces.maxh=gp.r_head/5
        circ.edges.name="contact_head"
        
        head = circ - hole
        pendulum = head + bar - hole

        pendulum = pendulum.Rotate(Axis((0.0, 0, 0), (0, 0, 1)), 180)
        pendulum.name = "pendulum"

        # Wall
        wall_pos_x = -gp.r_head - gp.wall_len_x
        wall_pos_y = -gp.l_center - gp.wall_len_y/2
        wall = MoveTo(wall_pos_x, wall_pos_y).Rectangle(gp.wall_len_x, gp.wall_len_y).Face()
        wall.faces.maxh = gp.r_head/5
        wall.edges.Max(X).name = "contact_wall"
        wall.edges.Max(X).maxh = gp.r_head/20
        wall.edges.Max(Y).name = "fix"
        wall.edges.Min(Y).name = "fix"
        wall.edges.Min(X).name = "fix"
        wall.name = "wall"

        self._geo = Compound([pendulum, wall])
    
    def initialize(self):
        self._initialize_fe_spaces()
        self._initialize_grid_functions()
        self._set_initial_conditions()
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
        
        # Scalar H1 space for stress
        self._S = H1(self._mesh, order=3)
        
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
        
        self._gf_vm_p = GridFunction(self._S) # Von Mises - pendulum
        self._gf_vm_w = GridFunction(self._S) # Von Mises - wall              
        
        # Time series storage
        self._gf_u_history = GridFunction(self._V, multidim=0)
        self._gf_v_history = GridFunction(self._V, multidim=0)
        self._gf_stress_history = GridFunction(H1(self._mesh, order=3), multidim=0)
    
    def _set_initial_conditions(self):
        icp = self.init_params
        theta = np.deg2rad(icp.angular_position_deg)   # initial angular position
        omega = icp.angular_velocity                   # initial angular velocity
        alpha = icp.angular_acceleration               # initial angular acceleration
        
        c, s = np.cos(theta), np.sin(theta)
        
        # Rotation center (could be made configurable)
        cx = cy = 0.0
        
        # reference coordinates relative to rotation center
        X_rel = CF((x - cx, y - cy))
        
        # rotated radius r0 = R(theta) * (X - P)
        r0 = CF((c * X_rel[0] - s * X_rel[1],
                 s * X_rel[0] + c * X_rel[1]))
        
        # displacement for initial position
        u0 = CF((r0[0] - X_rel[0],
                 r0[1] - X_rel[1]))
        
        # Initial velocity: v0 = omega x r0
        v0 = CF((-omega * r0[1],
                  omega * r0[0]))
        
        # Initial acceleration: a0 = alpha x r0 - omega^2 * r0
        a0 = CF(( -alpha * r0[1],
               alpha * r0[0] ))
        
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
        pass
    
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
            cf = (cur_pos_master - cur_pos_slave) * n_S
        
        elif gap_type == "incremental":
            increment_master = X_M + u - u_old
            increment_slave = X_S + u.Other() - u_old.Other()
            cf = (increment_master - increment_slave) * n_S
        
        penalty_energy = kn * cf * cf
        self._contact.AddEnergy(IfPos(cf, penalty_energy, 0), deformed = True)
    
    def _setup_bilinear_form(self):
        # Bilinear form
        self._bfa = BilinearForm(self._fes)
        
        # Strain energy wall (always linear elastic)
        self._bfa += Variation(self.linear_elastic(self.eps(self._u), self.mu_w, self.lam_w)*dx("wall")).Compile()
        
        # Strain energy pendulum (material law configurable)
        self._bfa += Variation(self._material_law(self._deformation_tensor(self._u), self.mu_p, self.lam_p)*dx("pendulum")).Compile()
        
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
        
    def simulate(self):
        
        scene = Draw(self._gf_u.components[0],
                     self._mesh,
                     deformation=self._gf_u.components[0])
        
        t = self.sim_params.t_start
        self.tend = self.sim_params.t_end
        i = 0
        
        with TaskManager():
            while t < self.tend:
                t += self.tau
                
                # Time step update
                self._gf_uold.vec[:] = self._gf_u.vec
                self._gf_vold.vec[:] = self._gf_v.vec
                self._gf_aold.vec[:] = self._gf_a.vec

                # A) Update contact with the current displacement
                self._contact.Update(self._gf_u.components[0], self._bfa, 5, 0.01)
                
                # B) Solve nonlinear system with Newton               
                NewtonMinimization(a=self._bfa, u=self._gf_u, printing=False, inverse="sparsecholesky")

                # C) Update kinematic variables (velocity, acceleration)
                self._gf_v.vec[:] = 2/self.tau * (self._gf_u.vec-self._gf_uold.vec) - self._gf_vold.vec
                self._gf_a.vec[:] = 2/self.tau * (self._gf_v.vec-self._gf_vold.vec) - self._gf_aold.vec
                
                # G) Store results in time series
                self._gf_u_history.AddMultiDimComponent(self._gf_u.components[0].vec)
                self._gf_v_history.AddMultiDimComponent(self._gf_v.components[0].vec)
                
                if i % 50 == 0:
                    print(f"t: {t:.4f} / {self.tend:.4f}")
                i += 1

                scene.Redraw()
                
    def visualize(self, mesh=True, u=True, v=True, a=True):
        if mesh:
            # Mesh Geometry
            tw_geometry = widgets.Text(value="Mesh Geometry")
            display(tw_geometry)
            Draw(self._mesh, "mesh")
        if u:
            # Displacement
            tw_displacement = widgets.Text(value="Angular Displacement", fontsize=16, fontweight='bold')
            display(tw_displacement)
            Draw(self._gf_u.components[0], deformation=True)
        if v:
            # Velocity
            tw_velocity = widgets.Text(value="Angular Velocity")
            display(tw_velocity)
            Draw(self._gf_v.components[0], deformation=self._gf_u.components[0], vectors=True)
        if a:
            # Acceleration
            tw_acceleration = widgets.Text(value="Tangential Angular Acceleration")
            display(tw_acceleration)
            Draw(self._gf_a.components[0], deformation=self._gf_u.components[0], vectors=True)
        
    def animate_u(self):
        settings = {"Multidim": {
                    "speed" : self.anim_params.speed
                }};
        
        tw_u = widgets.Text(value="Displacement Animation")
        display(tw_u)

        Draw(self._gf_u_history,
             self._mesh,
             interpolate_multidim=True,
             deformation=self._gf_u_history,
             animate=True,
             settings = settings);
        
    def animate_stress(self):
        settings = {"Multidim": {
                    "speed" : self.anim_params.speed
                }};
        
        tw_stress = widgets.Text(value="Stress History Animation")
        display(tw_stress)
        
        # Animate stress history and deformation history in one scene
        Draw(self._gf_stress_history,
             self._mesh,
             interpolate_multidim=True,
             deformation=self._gf_u_history,
             animate=True,
             settings = settings);
     
    # Hyperelastic material model: Neo-Hookean   
    def C(self, u):
        F = Id(u.dim) + Grad(u)
        return F.trans * F
        
    def neo_hooke (self, C, mu, lam):
        return 0.5*mu*(Trace(C-Id(self._u.dim)) + 2*mu/lam*Det(C)**(-lam/2/mu)-1)
    
    def sigma_neo_hooke(self, u, lam, mu):
        d = u.dim
        F = Id(d) + Grad(u)
        J = Det(F)
        C = F.trans * F
        
        # Psi = mu/2*(I1 -d) - mu*ln(J) + lam/2*ln(J)^2
        I1 = Trace(C)
        Psi = mu/2 * (I1 - d) - mu * log(J) + lam/2 *log(J)**2
        
        # Second Piola-Kirchhoff stress
        C_var = C.MakeVariable()
        Psi_var = mu/2 * (Trace(C_var) - d) - mu * log(Det(F)) + lam/2 * log(Det(F))**2
        S = Psi_var.Diff(C_var)
        
        # Cauchy stress
        sigma = 1.0 / J * F * S * F.trans
        return sigma
    
    def von_mises_2d(self, sig):
        sxx, syy, sxy = sig[0,0], sig[1,1], sig[0,1]
        return sqrt(sxx*sxx - sxx*syy + syy*syy + 3.0*sxy*sxy)

    # Linear elastic material model
    def eps(self, u):
        return Sym(Grad(u))
    
    def linear_elastic(self, eps, mu, lam):
        return 0.5*lam*Trace(eps)**2 + mu*InnerProduct(eps, eps)
    
    def sigma_linear(self, eps, u, lam, mu):
        return lam*Trace(eps)*Id(u.dim) + 2*mu*eps