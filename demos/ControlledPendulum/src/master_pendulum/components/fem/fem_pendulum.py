"""This module implements the FEMPendulum component using the Netgen/NGSolve finite element library.

The `FEMPendulum` class defines a finite element model of a controlled pendulum,
including optional contact with a wall and distributed torque control.

It provides methods for initializing the model, setting and getting the state, handling events, and snapshot/restore functionality for time integration. The component is designed to be used within a multi-model simulation framework, allowing it to be combined with other pendulum models (e.g., FMU, OpenSim) in a `MasterPendulum` component.
"""

from typing import Any

import ipywidgets as widgets
import numpy as np
from IPython.display import display
from ipywidgets import HTML, HBox, Layout, VBox
from netgen.occ import *
from ngsolve import *
from ngsolve.solvers import NewtonMinimization
from ngsolve.webgui import Draw

from .material_laws import NeoHookeanMaterial
from .pendulum_config import *
from .pendulum_mesh import build_mesh
from syssimx.components.fem import FEMComponent
from syssimx.core.port import PortSpec, PortType
from syssimx.utilities.units import Quantity, ureg

# ----------------------------------------------------------------------------
# Port specifications
# ----------------------------------------------------------------------------
INPUT_SPECS = {
    "tau": PortSpec("tau", PortType.REAL, direction="in", unit="N.m"),
    "omega_invert": PortSpec("omega_invert", PortType.EVENT, direction="in"),
}

OUTPUT_SPECS = {
    "theta": PortSpec("theta", PortType.REAL, direction="out", unit="rad"),
    "omega": PortSpec("omega", PortType.REAL, direction="out", unit="rad/s"),
    "alpha": PortSpec("alpha", PortType.REAL, direction="out", unit="rad/s^2"),
}


# ----------------------------------------------------------------------------
# Pendulum FEM component
# ----------------------------------------------------------------------------
class FEMPendulum(FEMComponent):
    """
    Finite Element Model of a controlled pendulum using Netgen/NGSolve.
    Implements a 2D pendulum with optional contact and torque control.
    Args:
        name (str): Name of the component.
        group (str): Group name for organizing components.
    """

    def __init__(self, name: str, group: str = "Plant"):
        super().__init__(name, group=group)

        # Define input and output specifications
        self.input_specs = INPUT_SPECS
        self.output_specs = OUTPUT_SPECS
        self._initialize_ports_from_specs()

        # Pendulum configuration parameters
        self.geom_params = GeometryParameters()
        self.mat_params = MaterialParameters()
        self.mesh_params = MeshParameters()
        self.init_params = InitialConditionParameters()
        self.contact_params = ContactParameters()
        self.sim_params = SimulationParameters()
        self.anim_params = AnimationParameters()

        self.parameters = {
            "geom_params": self.geom_params,
            "mat_params": self.mat_params,
            "mesh_params": self.mesh_params,
            "init_params": self.init_params,
            "contact_params": self.contact_params,
            "sim_params": self.sim_params,
            "anim_params": self.anim_params,
        }
        self._equivalent_length = 0.0

    # ----------------------------------------------------------------------------
    # Setup Configuration Parameters before initialization
    # ----------------------------------------------------------------------------
    def set_parameters(
        self,
        geom_params: GeometryParameters | None = None,
        mat_params: MaterialParameters | None = None,
        mesh_params: MeshParameters | None = None,
        init_params: InitialConditionParameters | None = None,
        contact_params: ContactParameters | None = None,
        sim_params: SimulationParameters | None = None,
        anim_params: AnimationParameters | None = None,
        **parameters: Any,
    ) -> None:
        """
        Set component parameters BEFORE initialize().
        Override to handle complex parameter objects.
        Args:
            geom_params (GeometryParameters): Geometry parameters.
            mat_params (MaterialParameters): Material parameters.
            mesh_params (MeshParameters): Mesh parameters.
            init_params (InitialConditionParameters): Initial condition parameters.
            contact_params (ContactParameters): Contact parameters.
            sim_params (SimulationParameters): Simulation parameters.
            anim_params (AnimationParameters): Animation parameters.
        """
        self.geom_params = geom_params if geom_params else self.geom_params
        self.mat_params = mat_params if mat_params else self.mat_params
        self.mesh_params = mesh_params if mesh_params else self.mesh_params
        self.init_params = init_params if init_params else self.init_params
        self.contact_params = contact_params if contact_params else self.contact_params
        self.sim_params = sim_params if sim_params else self.sim_params
        self.anim_params = anim_params if anim_params else self.anim_params
        super().set_parameters(**parameters)

    # ----------------------------------------------------------------------------
    # Initialization method
    # ----------------------------------------------------------------------------
    def _initialize_component(self, t0: float):
        """
        Netgen/NGSolve pendulum specific initialization (called by base-class).
        1. Setup material laws
        2. Create mesh and compute mass/inertia
        3. Initialize FE spaces and grid functions
        4. Setup contact if enabled
        5. Setup torque control system
        6. Setup bilinear form
        7. Set initial state
        Args:
            t0 (float): Start time of the simulation.
        """
        self._with_contact = self.sim_params.with_contact
        self._use_gravity = self.sim_params.use_gravity
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

        state = {
            "theta": {"value": np.deg2rad(self.init_params.angular_position_deg)},
            "omega": {"value": self.init_params.angular_velocity},
            "tau": {"value": self.init_params.drive_torque},
        }
        self.set_state(state=state, t=t0)

        if self._with_contact:
            self.gap = self._get_contact_gap_distance()
            self.gap_prev = self.gap

        self.setup_monitoring()

    # ----------------------------------------------------------------------------
    # Initialization helper methods
    # ----------------------------------------------------------------------------
    def _setup_material_law(self):
        self.E_p, self.E_w = self.mat_params.E_pendulum, self.mat_params.E_wall
        self.nu_p, self.nu_w = self.mat_params.nu_pendulum, self.mat_params.nu_wall
        self.rho_p, self.rho_w = self.mat_params.rho_pendulum, self.mat_params.rho_wall

        self._material_pendulum = NeoHookeanMaterial(self.E_p, self.nu_p)
        self._deformation_gradient_p = self._material_pendulum.C
        self._psi_p = self._material_pendulum.psi
        self._PK2_neo_hookean_p = self._material_pendulum.PK2_neo_hookean

        self._material_wall = NeoHookeanMaterial(self.E_w, self.nu_w)
        self._deformation_gradient_w = self._material_wall.C
        self._psi_w = self._material_wall.psi
        self._PK2_neo_hookean_w = self._material_wall.PK2_neo_hookean

    def _create_mesh(self):
        self._mesh = build_mesh(self.geom_params, self.mesh_params, self._with_contact)

    def _compute_mass(self):
        """Compute mass by integrating density over the undeformed area of the pendulum."""
        area = Integrate(1, self._mesh, definedon=self._mesh.Materials("pendulum"))
        self.mass = area * self.mat_params.thickness * self.rho_p

    def _compute_inertia(self):
        """Compute moment of inertia about the pivot by integrating r² over the area, where r is distance from pivot."""
        # Compute center of mass (rho cancels since it's a constant scalar)
        area = self.mass / (self.mat_params.thickness * self.rho_p)
        cx = Integrate(x, self._mesh, definedon=self._mesh.Materials("pendulum")) / area
        cy = Integrate(y, self._mesh, definedon=self._mesh.Materials("pendulum")) / area

        # Compute effective length from pivot to CoM
        self._equivalent_length = np.sqrt(cx**2 + cy**2)

        # Store for torque calculation
        self._X_rel = CF((x - 0, y - 0))  # Relative to pivot at (0,0)

        # Moment of inertia about pivot: I = rho * t * ∫ r² dA
        J_area = Integrate(
            self._X_rel[0] ** 2 + self._X_rel[1] ** 2,
            self._mesh,
            definedon=self._mesh.Materials("pendulum"),
        )
        self.inertia = self.rho_p * self.mat_params.thickness * J_area

    def _gravity_torque_fem(self):
        """Compute gravitational torque by integrating moment arm × gravity force."""
        g = 9.81
        rhoA_p = self.rho_p * self.mat_params.thickness

        # CRITICAL: Use deformed positions (X + u), not reference positions X
        u = self._gf_u.components[0]
        x_deformed = x + u[0]  # Current x-position after rotation

        # Torque = ∫ x_deformed * (ρAg) dA
        # (assuming gravity points in +y direction, torque = arm_x * force_y)
        torque_fem = Integrate(
            rhoA_p * g * x_deformed, self._mesh, definedon=self._mesh.Materials("pendulum")
        )
        return torque_fem

    def _gravity_torque_rigid(self, theta: float):
        """Compute gravitational torque using rigid-body approximation: τ = m * g * L * sin(θ)."""
        if not self._use_gravity:
            return 0.0
        return self.mass * 9.81 * self._equivalent_length * np.sin(theta)

    def _initialize_fe_spaces(self):
        """Initialize finite element spaces for displacement, Lagrange multipliers, and stress."""
        # Create H1 vector space for 3D quantities (displacement, velocity, acceleration)
        self._V = VectorH1(self._mesh, order=self.mesh_params.mesh_order, dirichlet="fix")

        # Create NumberSpace for Lagrange multipliers (rotation constraint)
        self._Q = NumberSpace(self._mesh, definedon=self._mesh.Boundaries("rotation"))

        # Mixed FE space
        self._fes = self._V * self._Q**2
        (self._u, self._q), (self._v, self._p) = self._fes.TnT()

        # Scalar H1 space for stress in pendulum
        self._S = MatrixValued(
            H1(
                self._mesh,
                order=self.mesh_params.mesh_order,
                definedon=self._mesh.Materials("pendulum"),
            )
        )
        # Scalar H1 space for stress norm visualization
        self._S_norm = H1(
            self._mesh,
            order=self.mesh_params.mesh_order,
            definedon=self._mesh.Materials("pendulum"),
        )

    def _initialize_grid_functions(self):
        """Initialize grid functions for state variables and stress."""
        self._gf_u = GridFunction(self._fes)  # Current state
        self._gf_v = GridFunction(self._fes)  # Velocity
        self._gf_a = GridFunction(self._fes)  # Acceleration

        self._gf_uold = GridFunction(self._fes)  # Previous displacement
        self._gf_vold = GridFunction(self._fes)  # Previous velocity
        self._gf_aold = GridFunction(self._fes)  # Previous acceleration

        self._gf_sigma = GridFunction(self._S)  # Stress
        self._gf_sigma_norm = GridFunction(self._S_norm)  # Stress norm (scalar)

        # Time series storage
        self._gf_u_history = GridFunction(self._V, multidim=0)
        self._gf_v_history = GridFunction(self._V, multidim=0)
        self._gf_stress_history = GridFunction(self._S, multidim=0)
        self._gf_sigma_norm_history = GridFunction(self._S_norm, multidim=0)

    def _initialize_contact(self):
        """
        Initialize contact boundary conditions using penalty method and incremental gap function.
        """
        kn = self.contact_params.kn

        master = self._mesh.Boundaries("contact_wall")
        slave = self._mesh.Boundaries("contact_head")
        self._contact = ContactBoundary(master, slave)

        u = self._u
        u_old = self._gf_uold.components[0]

        X_M = CoefficientFunction((x, y))
        X_S = X_M.Other()
        n_S = -specialcf.normal(2).Other()

        increment_master = X_M + u - u_old
        increment_slave = X_S + u.Other() - u_old.Other()
        self._cf = (increment_master - increment_slave) * n_S

        penalty_energy = kn * self._cf * self._cf
        self._contact.AddEnergy(IfPos(self._cf, penalty_energy, 0), deformed=True)

    def _initialize_torque_control(self):
        """
        Initialize torque control system using distributed traction on rotation boundary.
        """
        # --- Geometric quantities ---
        N_ref = specialcf.normal(2)  # outward unit normal in reference configuration (on 'rotation')
        r_ref = self._X_rel  # position vector from pivot to boundary points (reference)

        # Deformation gradient restricted to the boundary.
        # NOTE: In NGSolve, `.Trace()` here means "restrict to the boundary", not the matrix trace.
        F = Id(2) + Grad(self._u).Trace()

        # Cofactor (adjugate) matrix: cof(F) = det(F) * F^{-T}.
        # Used for the surface Piola transform: n * J_s = cof(F) * N.
        cofF = Cof(F)

        # Current surface normal (unnormalized): n * J_s
        nJ_s = cofF * N_ref
        J_s = Norm(nJ_s)
        n_cur = nJ_s / IfPos(J_s, J_s, 1)

        # Cross product for torque calculation: r × n (2D cross product gives scalar)
        self._torque_moment_arm = -(r_ref[0] * N_ref[1] - r_ref[1] * N_ref[0])

        self._torque_drive_parameter = Parameter(0.0)

        distribution = self.sim_params.torque_traction_distribution

        rotation_edge_length = Integrate(1, self._mesh, definedon=self._mesh.Boundaries("rotation"))

        if distribution == "linear":
            # Linear weight (robustly enforced to be zero-mean -> pure torque, no net force)
            hinge_radius = max(1e-12, float(self.geom_params.r_rod))
            weight_raw = x / hinge_radius
            weight_mean = (
                Integrate(weight_raw, self._mesh, definedon=self._mesh.Boundaries("rotation"))
                / rotation_edge_length
            )
            self._weight = weight_raw - weight_mean

        elif distribution in ("bipolar", "dipole", "antisymmetric"):
            # Create localized weight function near the rotation axis
            hinge_radius = self.geom_params.r_rod
            smoothing_width = max(1e-9, 0.5 * hinge_radius)
            core_weight = exp(-(x * x) / (smoothing_width * smoothing_width))

            # Split the weight into positive and negative regions using smooth Heaviside
            heaviside_smoothing = 0.1 * smoothing_width
            smooth_heaviside = 0.5 * (
                1 + x / sqrt(x * x + heaviside_smoothing * heaviside_smoothing)
            )

            weight_positive_side = core_weight * smooth_heaviside  # Right side weight
            weight_negative_side = core_weight * (1.0 - smooth_heaviside)  # Left side weight

            # --- Zero-mean bipolar distribution ---
            # Ensure the weight distribution has zero net force (pure torque)
            weight_difference = weight_positive_side - weight_negative_side

            # Remove mean to ensure ∫ w dA = 0 (no net force)
            weight_mean = (
                Integrate(
                    weight_difference, self._mesh, definedon=self._mesh.Boundaries("rotation")
                )
                / rotation_edge_length
            )
            self._weight = weight_difference - weight_mean
        else:
            raise ValueError(
                f"Unknown torque traction distribution: {distribution!r}. "
                "Expected 'linear' or 'bipolar' (aka 'dipole')."
            )

        # Traction amplitude scaled by zero-mean weight distribution
        self._traction_amplitude = self._torque_drive_parameter * self._weight

        # Applied traction in current configuration (includes surface jacobian)
        self._applied_traction = self._traction_amplitude * n_cur * J_s

        # --- Effective moment arm calculation ---
        # Compute the effective lever arm for torque-to-parameter conversion
        self._effective_moment_arm = Integrate(
            self._weight * self._torque_moment_arm,
            self._mesh,
            definedon=self._mesh.Boundaries("rotation"),
        )

    def _setup_bilinear_form(self):
        # Bilinear form
        self._bfa = BilinearForm(self._fes)

        # Strain energy wall
        if self._with_contact:
            self._bfa += Variation(
                self._psi_w(self._deformation_gradient_w(self._u), self._u) * dx("wall")
            ).Compile()

        # Strain energy pendulum
        self._bfa += Variation(
            self._psi_p(self._deformation_gradient_p(self._u), self._u) * dx("pendulum")
        ).Compile()

        # Rotation constraint
        self._bfa += (InnerProduct(self._u, self._p) + InnerProduct(self._v, self._q)) * ds(
            "rotation"
        )

        # Apply distributed traction for torque generation
        self._bfa += InnerProduct(self._applied_traction, self._v) * ds("rotation")

        # inertia
        self.tau = Parameter(self.sim_params.tau)
        vel_new = (
            2 / self.tau * (self._u - self._gf_uold.components[0]) - self._gf_vold.components[0]
        )
        acc_new = (
            2 / self.tau * (vel_new - self._gf_vold.components[0]) - self._gf_aold.components[0]
        )

        #  gravity force
        rhoA_p = self.rho_p * self.mat_params.thickness
        rhoA_w = self.rho_w * self.mat_params.thickness

        if self._with_contact:
            self._bfa += rhoA_w * InnerProduct(acc_new, self._v) * dx("wall")
        self._bfa += rhoA_p * InnerProduct(acc_new, self._v) * dx("pendulum")

        g = -9.81
        if self._use_gravity:
            if self._with_contact:
                self._bfa += -rhoA_w * g * InnerProduct(CF((0, 1)), self._v) * dx("wall")
            self._bfa += -rhoA_p * g * InnerProduct(CF((0, 1)), self._v) * dx("pendulum")

    # ----------------------------------------------------------------------------
    # State methods for setting and getting simulation state
    # ----------------------------------------------------------------------------
    def _apply_rigid_state_to_fields(self, state: dict[str, Any], target: str) -> None:
        # target: "current" or "old"
        theta = state.get("theta", {}).get("value", 0.0)
        omega = state.get("omega", {}).get("value", 0.0)
        alpha = state.get("alpha", {}).get("value", None)

        c, s = np.cos(theta), np.sin(theta)
        r0 = CF((c * self._X_rel[0] - s * self._X_rel[1], s * self._X_rel[0] + c * self._X_rel[1]))
        u0 = CF((r0[0] - self._X_rel[0], r0[1] - self._X_rel[1]))
        v0 = CF((-omega * r0[1], omega * r0[0]))

        if alpha is None:
            torque_drive = self._get_applied_drive_torque() if "tau" in state else 0.0
            torque_gravity = self._gravity_torque_rigid(theta)
            alpha = (torque_drive - torque_gravity) / self.inertia

        a0 = CF((-alpha * r0[1], alpha * r0[0]))

        if target == "current":
            self._gf_u.components[0].Set(u0, definedon=self._mesh.Materials("pendulum"))
            self._gf_v.components[0].Set(v0, definedon=self._mesh.Materials("pendulum"))
            self._gf_a.components[0].Set(a0, definedon=self._mesh.Materials("pendulum"))
        else:
            self._gf_uold.components[0].Set(u0, definedon=self._mesh.Materials("pendulum"))
            self._gf_vold.components[0].Set(v0, definedon=self._mesh.Materials("pendulum"))
            self._gf_aold.components[0].Set(a0, definedon=self._mesh.Materials("pendulum"))

    def set_state_with_history(
        self,
        current_state: dict[str, Any],
        previous_state: dict[str, Any] | None,
        dt: float | None,
        t: float,
    ) -> None:
        self.set_state(current_state, t)

        if previous_state is not None:
            self._apply_rigid_state_to_fields(previous_state, target="old")
        else:
            # fallback: old == current
            self._gf_uold.vec[:] = self._gf_u.vec
            self._gf_vold.vec[:] = self._gf_v.vec
            self._gf_aold.vec[:] = self._gf_a.vec

        if dt is not None:
            self.tau.Set(dt)

    def set_state(self, state: dict[str, Any], t: float):
        """
        Reset and initialize the FEM pendulum state from a reference rigid-body state.
        """
        self.t = t

        if "theta" in state:
            theta = state["theta"]["value"]
            if hasattr(theta, "magnitude"):
                theta = theta.magnitude
            c, s = np.cos(theta), np.sin(theta)
            # rotated radius r0 = R(theta) * (X - P)
            r0 = CF(
                (c * self._X_rel[0] - s * self._X_rel[1], s * self._X_rel[0] + c * self._X_rel[1])
            )
            # displacement for initial position
            u0 = CF((r0[0] - self._X_rel[0], r0[1] - self._X_rel[1]))
            # Update displacement grid function
            self._gf_u.components[0].Set(u0, definedon=self._mesh.Materials("pendulum"))
            self._gf_uold.vec[:] = self._gf_u.vec

            # Update gap if contact is enabled
            if self._with_contact:
                self.gap_prev = state.get("gap_prev", float("inf"))
                self.gap = self._get_contact_gap_distance()

            if "omega" in state:
                omega = state["omega"]["value"]
                # Initial velocity: v0 = omega x r0
                v0 = CF((-omega * r0[1], omega * r0[0]))

                # Update velocity grid function
                self._gf_v.components[0].Set(v0, definedon=self._mesh.Materials("pendulum"))

                # Initialize previous velocity for Newmark
                self._gf_vold.vec[:] = self._gf_v.vec

                # Initialize accelartion from dynamics
                torque_drive = self._get_applied_drive_torque() if "tau" in state else 0.0
                torque_gravity = self._gravity_torque_rigid(theta)
                alpha_init = (torque_drive - torque_gravity) / self.inertia

                # Convert scalar angular acceleration to acceleration field
                a0 = CF((-alpha_init * r0[1], alpha_init * r0[0]))
                self._gf_a.components[0].Set(a0, definedon=self._mesh.Materials("pendulum"))
                self._gf_aold.vec[:] = self._gf_a.vec

        if "tau" in state:
            torque = state["tau"]["value"]
            self.set_drive_torque(torque)

    def get_state(self):
        state = {}
        q_state, omega_state, alpha_state = self._rigid_proxy()
        torque_state = self._get_applied_drive_torque()
        state["theta"] = {"value": q_state, "unit": "rad"}
        state["omega"] = {"value": omega_state, "unit": "rad/s"}
        state["alpha"] = {"value": alpha_state, "unit": "rad/s**2"}
        state["tau"] = {"value": torque_state, "unit": "N*m"}
        if self._with_contact:
            state["gap"] = {"value": self.gap, "unit": "m"}
            state["gap_prev"] = {"value": self.gap_prev, "unit": "m"}
        return state

    # ----------------------------------------------------------------------------
    # Hybrid methods for snapshot/restore and event handling
    # ----------------------------------------------------------------------------
    def snapshot_state(self):
        """
        Capture complete Newmark time integration state.
        Must include current AND previous time step data.
        """
        return {
            # Mode Identifier
            "mode": "FEM",
            # Current state
            "u": self._gf_u.vec.FV().NumPy().copy(),
            "v": self._gf_v.vec.FV().NumPy().copy(),
            "a": self._gf_a.vec.FV().NumPy().copy(),
            # Previous time step  for Newmark
            "u_old": self._gf_uold.vec.FV().NumPy().copy(),
            "v_old": self._gf_vold.vec.FV().NumPy().copy(),
            "a_old": self._gf_aold.vec.FV().NumPy().copy(),
            # Time step size (may vary during contact)
            "tau": self.tau.Get(),
            # Contact gap info
            "gap": self.gap if self._with_contact else None,
            "gap_prev": self.gap_prev if self._with_contact else None,
            # Time
            "t": self.t,
        }

    def restore_state(self, snapshot: dict[str, Any], t: float):
        """
        Restore complete Newmark state from snapshot.
        Critical: Must restore BOTH current and old states.
        """
        # Check mode
        if snapshot.get("mode", "") != "FEM":
            raise ValueError(
                f"[{self.name}] Incompatible snapshot mode, got '{snapshot.get('mode', '')}'."
            )

        self.internal_event_hints.clear()

        # Restore time
        self.t = t

        # Restore current state
        self._gf_u.vec.FV().NumPy()[:] = snapshot["u"]
        self._gf_v.vec.FV().NumPy()[:] = snapshot["v"]
        self._gf_a.vec.FV().NumPy()[:] = snapshot["a"]

        # Restore previous time step (THIS IS CRITICAL!)
        self._gf_uold.vec.FV().NumPy()[:] = snapshot["u_old"]
        self._gf_vold.vec.FV().NumPy()[:] = snapshot["v_old"]
        self._gf_aold.vec.FV().NumPy()[:] = snapshot["a_old"]

        # Update contact gap info
        if self._with_contact:
            self.gap = snapshot.get("gap", float("inf"))
            self.gap_prev = snapshot.get("gap_prev", float("inf"))

        # Restore time step size
        self.tau.Set(snapshot["tau"])

        # Update outputs and record
        self._update_output_states(t)
        self._record_outputs(t)

    def _handle_events_internal(self, event_names, t):
        if "wall_hit" not in event_names:
            return

        print(f"[{self.name}] Event 'wall_hit' at t={t:.4f}s.")

        # Invert velocity field (keep displacement and old states unchanged)
        if not self._with_contact:
            self._gf_v.vec.data = -1.0 * self._gf_v.vec
            self._gf_vold.vec.data = -1.0 * self._gf_vold.vec

            # Recompute acceleration from inverted velocity (Newmark update)
            tau = self.tau.Get()
            acc_new = 2 / tau * (self._gf_v.vec - self._gf_vold.vec) - self._gf_aold.vec
            self._gf_a.vec.data = acc_new

            # Update outputs
            self._update_output_states(t, event_names=event_names)
            self._record_outputs(t)

    # ----------------------------------------------------------------------------
    # Time stepping method
    # ----------------------------------------------------------------------------
    def do_step(self, t, dt):
        """Override base-class method to implement micro-stepping with internal event hints.

        Outputs are updated and recorded within each micro-step to ensure accurate recording.
        """
        self._do_step_internal(t, dt)

    def _do_step_internal(self, t, dt):
        """
        Advance FEM pendulum simulation from t to t+dt (called by base-class).

        Reports internal event hints when wall contact is detected during
        micro-stepping, enabling precise event localization by the master algorithm.
        """
        # Clear any stale internal event hints from previous steps
        self.internal_event_hints.clear()

        if dt < 1e-4:
            effective_dt = dt
        elif dt < self.sim_params.tau:
            effective_dt = dt
        else:
            effective_dt = self.sim_params.tau

        t_current = t
        t_end = t + dt

        with TaskManager():
            while t_current < t_end - 1e-12:
                tau = min(effective_dt, t_end - t_current)
                self.tau.Set(tau)

                # Time step update
                self._gf_uold.vec[:] = self._gf_u.vec
                self._gf_vold.vec[:] = self._gf_v.vec
                self._gf_aold.vec[:] = self._gf_a.vec

                # Update contact with the current displacement
                if self._with_contact:
                    # Update contact conditions
                    self._contact.Update(
                        self._gf_u.components[0], self._bfa, intorder=10, maxdist=0.5
                    )
                    self.gap_prev = self._get_contact_gap_distance()
                    t_prev = t_current
                    self.widgets["gap"].value = self.gap_prev

                    # Reduce time step if pendulum is close to contact
                    if effective_dt <= 1e-4:
                        self.tau.Set(effective_dt)
                    elif self.gap_prev < 0.001:
                        self.tau.Set(1e-4)
                    elif self.gap_prev < 0.005:
                        self.tau.Set(5e-4)
                    elif self.gap_prev < 0.01:
                        self.tau.Set(1e-3)
                    else:
                        self.tau.Set(self.sim_params.tau)

                # Update time settings
                tau = self.tau.Get()
                t_current += tau
                self.widgets["time"].value = t_current
                self.widgets["dt"].value = tau

                # Solve nonlinear system with Newton
                NewtonMinimization(
                    a=self._bfa,
                    u=self._gf_u,
                    printing=False,
                    inverse="sparsecholesky",
                    maxerr=self.sim_params.max_err,
                    maxit=self.sim_params.max_it,
                )

                # Update kinematic variables (velocity, acceleration)
                self._gf_v.vec[:] = (
                    2 / tau * (self._gf_u.vec - self._gf_uold.vec) - self._gf_vold.vec
                )
                self._gf_a.vec[:] = (
                    2 / tau * (self._gf_v.vec - self._gf_vold.vec) - self._gf_aold.vec
                )

                # Check for wall contact event (gap crossing zero)
                if self._with_contact:
                    self.gap = self._get_contact_gap_distance()

                    # Detect zero-crossing: gap went from positive to non-positive
                    if self.gap_prev > 0.0 and self.gap <= 0.0:
                        # Report internal event with precise timing from micro-steps
                        self.report_internal_event(
                            event_name="wall_hit",
                            t_before=t_prev,
                            t_after=t_current,
                            indicator_before=self.gap_prev,
                            indicator_after=self.gap,
                        )

                # Compute stress
                self._gf_sigma.Interpolate(self._PK2_neo_hookean_p(self._gf_u.components[0]))
                self._gf_sigma_norm.Set(Norm(self._gf_sigma))

                # Add current state to time series history for visualization
                self._gf_u_history.AddMultiDimComponent(self._gf_u.components[0].vec)
                self._gf_sigma_norm_history.AddMultiDimComponent(self._gf_sigma_norm.vec)

                if self.anim_params.animate:
                    self.scene.Redraw()
                self._update_output_states(t_current)

                self._record_outputs(t_current)
                self.update_monitoring()
        self.t = t_current
        
    # ----------------------------------------------------------------------------
    # Input/output methods
    # ----------------------------------------------------------------------------
    def set_inputs(self, signals: dict[str, Any], t: float | None = None) -> None:
        for name, value in signals.items():
            if name in self.inputs:
                self.inputs[name].set(value, t=t)
                if name == "tau":
                    self.set_drive_torque(value)
        
        # Update acting torque
        drive_torque = self._get_applied_drive_torque()
        gravity_torque = self._gravity_torque_fem()
        total_torque = drive_torque - gravity_torque
        alpha = total_torque / self.inertia
        self.outputs["alpha"].set(alpha, t=t)


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

    def get_outputs(self) -> dict[str, Any]:
        return {
            name: out_port.get()
            for name, out_port in self.outputs.items()
            if out_port.get() is not None
        }

    def _update_output_states(
        self, t: float | None = None, event_names: list[str] | None = []
    ):
        """
        Convert rigid-body proxy to output ports (called by base-class).
        """
        q_state, omega_state, alpha_state = self._rigid_proxy()
        q_state = q_state * ureg("rad")
        omega_state = omega_state * ureg("rad/s")
        alpha_state = alpha_state * ureg("rad/s^2")
        self.outputs["theta"].set(q_state, t=t)
        self.outputs["omega"].set(omega_state, t=t)
        self.outputs["alpha"].set(alpha_state, t=t)

        if event_names:
            for event_name in event_names:
                if event_name in self.output_specs.keys():
                    self.outputs[event_name].set(True, t=t)
        else:
            for out_port in self.outputs.values():
                if out_port.spec.type == PortType.EVENT:
                    out_port.set(False, t=t)

    # ----------------------------------------------------------------------------
    # Reset method
    # ----------------------------------------------------------------------------
    def reset(self):
        # Reset all grid functions and time series
        super().reset()
        self._gf_u.vec[:] = 0
        self._gf_v.vec[:] = 0
        self._gf_a.vec[:] = 0
        self._gf_uold.vec[:] = 0
        self._gf_vold.vec[:] = 0
        self._gf_aold.vec[:] = 0
        self._gf_sigma.vec[:] = 0
        self._gf_sigma_norm.vec[:] = 0
        self._gf_u_history = GridFunction(self._V, multidim=0)
        self._gf_v_history = GridFunction(self._V, multidim=0)
        self._gf_stress_history = GridFunction(self._S, multidim=0)
        self._gf_sigma_norm_history = GridFunction(self._S_norm, multidim=0)

    # ----------------------------------------------------------------------------
    # Helpers for diagnostics and visualization
    # ----------------------------------------------------------------------------
    def _get_contact_gap_distance(self):
        """
        Compute the minimum gap distance at the contact interface.
        Returns:
            float: Minimum gap distance
        """
        self._contact.Update(self._gf_u.components[0], self._bfa, intorder=10, maxdist=0.5)
        gap_vec_master = self._contact.gap
        n_master = self._contact.normal
        gap_n_master = InnerProduct(gap_vec_master, n_master)
        gap_values = []
        for el in self._mesh.Elements(BND):
            if el.mat == "contact_wall":
                trafo = self._mesh.GetTrafo(el)
                ir = IntegrationRule(el.type, order=3 * self.mesh_params.mesh_order)
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
        """
        Compute rigid-body proxy quantities: angular position, velocity, acceleration.
        Returns:
            tuple: (theta, omega, alpha)
                - theta (float): Angular position in radians
                - omega (float): Angular velocity in rad/s
                - alpha (float): Angular acceleration in rad/s^2
        """
        r = self._X_rel
        rhoA = self.rho_p * self.mat_params.thickness
        u = self._gf_u.components[0]

        denom = Integrate(
            rhoA * InnerProduct(r, r), self._mesh, definedon=self._mesh.Materials("pendulum")
        )

        s_num = Integrate(
            rhoA * (r[0] * u[1] - r[1] * u[0]),
            self._mesh,
            definedon=self._mesh.Materials("pendulum"),
        )
        c_num = Integrate(
            rhoA * InnerProduct(r, r + u), self._mesh, definedon=self._mesh.Materials("pendulum")
        )

        s = s_num / denom  # ~ sin(theta)
        c = c_num / denom  # ~ cos(theta)

        theta = np.arctan2(s, c)

        # Angular velocity
        c, s = np.cos(theta), np.sin(theta)
        # rotated radius r = R(theta) * (X - P)
        r = CF((c * r[0] - s * r[1], s * r[0] + c * r[1]))

        v = self._gf_v.components[0]

        num_omega_x = Integrate(
            rhoA * v[0] * (-r[1]), self._mesh, definedon=self._mesh.Materials("pendulum")
        )
        num_omega_y = Integrate(
            rhoA * v[1] * (r[0]), self._mesh, definedon=self._mesh.Materials("pendulum")
        )
        num_v = num_omega_x + num_omega_y
        omega = num_v / denom

        # Angular acceleration - NOW ALWAYS USE GRID FUNCTION
        a = self._gf_a.components[0]
        num_alpha_x = Integrate(
            rhoA * a[0] * (-r[1]), self._mesh, definedon=self._mesh.Materials("pendulum")
        )
        num_alpha_y = Integrate(
            rhoA * a[1] * (r[0]), self._mesh, definedon=self._mesh.Materials("pendulum")
        )
        num_a = num_alpha_x + num_alpha_y
        alpha = num_a / denom

        return theta, omega, alpha

    def _get_applied_drive_torque(self, return_force=False):
        """
        Compute the actual applied torque from the distributed traction.

        Args:
            return_force (bool): If True, also return force components

        Returns:
            float or tuple: Applied torque in N·m, optionally with (Fx, Fy, Mz)
        """
        # Calculate actual applied torque by integrating moment contributions
        effective_traction = self._traction_amplitude * self._torque_moment_arm
        applied_drive_torque = Integrate(
            effective_traction, self._mesh, definedon=self._mesh.Boundaries("rotation")
        )
        if return_force:
            # Calculate net force components (should be near zero for pure torque)
            force_x = Integrate(
                self._applied_traction[0], self._mesh, definedon=self._mesh.Boundaries("rotation")
            )
            force_y = Integrate(
                self._applied_traction[1], self._mesh, definedon=self._mesh.Boundaries("rotation")
            )
            return force_x, force_y, applied_drive_torque
        else:
            return applied_drive_torque

    def calculate_energy(self):
        # Kinetic energy
        rhoA = self.rho_p * self.mat_params.thickness
        KE = 0.5 * Integrate(
            rhoA * InnerProduct(self._gf_v.components[0], self._gf_v.components[0]),
            self._mesh,
            definedon=self._mesh.Materials("pendulum"),
        )

        # Potential energy
        g = 9.81
        PE = Integrate(
            rhoA * g * self._gf_u.components[0][1],
            self._mesh,
            definedon=self._mesh.Materials("pendulum"),
        )

        # Strain energy
        SE = Integrate(
            self._psi_p(self._deformation_gradient_p(self._gf_u.components[0]), self._u),
            self._mesh,
            definedon=self._mesh.Materials("pendulum"),
        )

        return KE, PE, SE

    # ----------------------------------------------------------------------------
    # Visualization methods
    # ----------------------------------------------------------------------------
    def initialize_scene(self):
        """
        Initialize the stress visualization scene.
        """
        self.scene = Draw(
            Norm(self._gf_sigma),
            self._mesh,
            "displacement",
            deformation=self._gf_u.components[0],
            show=True,
        )

    def update_scene(self, q: float | Quantity, t: float):
        """
        Update the visualization scene with new state.

        Args:
            q (Union[float, Quantity]): The new state value.
            t (float): The current time.
        """
        if self.scene:
            self.set_state({"theta": {"value": q}}, t)
            self.scene.Redraw()

    def visualize_state(self, draw_u: bool = True, draw_v: bool = True, draw_a: bool = True):
        """
        Visualizes the current state of the FEM pendulum (displacement, velocity, and acceleration field.)

        Args:
            draw_u (bool, optional): Whether to draw the displacement field. Defaults to True.
            draw_v (bool, optional): Whether to draw the velocity field. Defaults to True.
            draw_a (bool, optional): Whether to draw the acceleration field. Defaults to True.
        """
        # Displacement
        if draw_u:
            Draw(self._gf_u.components[0], deformation=True)

        # Velocity
        if draw_v:
            Draw(self._gf_v.components[0], deformation=self._gf_u.components[0], vectors=True)

        # Acceleration
        if draw_a:
            Draw(self._gf_a.components[0], deformation=self._gf_u.components[0], vectors=True)

    def animate_displacement(self, settings: dict | None = None):
        """
        Animate displacement history.

        Requires that `anim_params.animate` was True during simulation so
        histories were recorded.
        """
        if settings is None:
            settings = {"Multidim": {"speed": 15}}
        if not hasattr(self, "_gf_u_history") or len(self._gf_u_history.vecs) == 0:
            raise RuntimeError(
                f"{self.name}: No displacement history recorded. "
                "Run with anim_params.animate=True to collect history."
            )
        Draw(
            self._gf_u_history,
            self._mesh,
            deformation=self._gf_u_history,
            animate=True,
            settings=settings,
        )
    
    
    def animate_stress(self, settings: dict | None = None):
        """
        Animate stress norm history with deformation.

        Requires that `anim_params.animate` was True during simulation so
        histories were recorded.
        """
        if settings is None:
            settings = {"Multidim": {"speed": 15}}
        if not hasattr(self, "_gf_sigma_norm_history") or len(self._gf_sigma_norm_history.vecs) == 0:
            raise RuntimeError(
                f"{self.name}: No stress history recorded. "
                "Run with anim_params.animate=True to collect history."
            )
        Draw(
            self._gf_sigma_norm_history,
            self._mesh,
            interpolation_multidim=True,
            deformation=self._gf_u_history,
            animate=True,
            autoscale=False,
            min=0,
            max=np.max([v.FV().NumPy().max() for v in self._gf_sigma_norm_history.vecs]),
            settings=settings,
        )

    # ----------------------------------------------------------------------------
    # Monitoring interface methods
    # ----------------------------------------------------------------------------
    def _initialize_widgets(self):
        self.widgets = {}
        # Input and output monitoring widgets
        for name, spec in self.input_specs.items():
            if spec.type == PortType.REAL:
                self.widgets[name] = widgets.FloatText(
                    value=0.0, description=f"{name} ({spec.unit}):", step=0.01, disabled=True
                )
        for name, spec in self.output_specs.items():
            if spec.type == PortType.REAL:
                self.widgets[name] = widgets.FloatText(
                    value=0.0, description=f"{name} ({spec.unit}):", step=0.01, disabled=True
                )
        # Additional simulation monitoring widgets
        self.widgets["time"] = widgets.FloatText(
            value=0, description=f"Time: t / {self.sim_params.t_end} s", step=0.001, disabled=True
        )

        self.widgets["dt"] = widgets.FloatText(
            value=self.sim_params.tau, description="Time Step: dt in s", step=0.0001, disabled=True
        )

        self.widgets["mode"] = widgets.Text(
            value="FEM", description="Simulation Mode:", disabled=True
        )
        if self._with_contact:
            self.widgets["gap"] = widgets.FloatText(
                value=0.0, description="Min. Gap in m", step=0.0001, disabled=True
            )
        self._format_widgets()

    def _format_widgets(self):
        for w in self.widgets.values():
            w.layout.width = "300px"
            w.layout.margin = "5px"
            w.style.description_width = "150px"

            w.readout_format = ".5g"

            # Professional color scheme
            w.style.font_family = (
                "Inter"  # , -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
            )
            w.style.font_size = "13px"
            w.style.font_weight = "500"

            # Modern input field styling
            w.style.background = "white"
            w.style.border = "1px solid #e0e0e0"
            w.style.border_radius = "4px"
            w.style.padding = "8px 12px"

            # Text styling
            w.style.color = "#424242"
            w.style.description_color = "#757575"

    def setup_monitoring(self) -> None:
        """Setup monitoring interface with grouped widgets."""
        self._initialize_widgets()

        # Create styled headers
        main_header = HTML(
            "<h3 style='color:#1565c0; font-family:Inter, sans-serif; margin:15px 0 20px 0; "
            "text-align:center; font-weight:600; border-bottom:2px solid #1565c0; padding-bottom:10px;'>"
            "Pendulum Monitoring</h3>"
        )

        # Group headers with modern styling
        header_style = (
            "color:#424242; font-family:Inter, sans-serif; font-size:14px; "
            "font-weight:600; margin:15px 0 8px 0; padding:8px 12px; "
            "background:linear-gradient(to right, #f5f5f5, #ffffff); "
            "border-left:4px solid #1565c0; border-radius:4px;"
        )

        input_header = HTML(f"<div style='{header_style} text-align:center;'>Input Signals</div>")
        output_header = HTML(f"<div style='{header_style} text-align:center;'>Output Signals</div>")
        simulation_header = HTML(
            f"<div style='{header_style} text-align:center;'>Simulation Status</div>"
        )

        # Group widgets
        input_widgets = [
            self.widgets[name] for name in self.input_specs.keys() if name in self.widgets
        ]
        output_widgets = [
            self.widgets[name] for name in self.output_specs.keys() if name in self.widgets
        ]
        simulation_widgets = [self.widgets["time"], self.widgets["dt"], self.widgets["mode"]]
        if self._with_contact:
            simulation_widgets.append(self.widgets["gap"])

        # Create widget groups with padding
        input_box = VBox([input_header] + input_widgets, layout=Layout(margin="0 0 20px 10px"))
        output_box = VBox([output_header] + output_widgets, layout=Layout(margin="0 0 20px 10px"))
        simulation_box = VBox(
            [simulation_header] + simulation_widgets, layout=Layout(margin="0 0 20px 10px")
        )

        # Widget Box
        widget_box = HBox(
            [simulation_box, input_box, output_box], layout=Layout(justify_content="space-between")
        )

        # Create main container with sections
        self.monitoring_display = VBox(
            [
                main_header,
                widget_box,
            ],
            layout=Layout(
                padding="20px",
                border="1px solid #e0e0e0",
                border_radius="8px",
                background="#fafafa",
                width="fit-content",
                margin="0 auto",
                height="auto",
                box_shadow="0 4px 8px rgba(0, 0, 0, 0.1)",
            ),
        )

        # Stress visualization header
        self.scene_header = HTML(
            "<h3 style='color:#1565c0; font-family:Inter, sans-serif; margin:15px 0 20px 0; "
            "text-align:center; font-weight:600; border-bottom:2px solid #1565c0; padding-bottom:10px;'>"
            "Stress Visualization (N/m²)</h3>"
        )

    def update_monitoring(self):
        """Update monitoring widgets with current values."""
        for name, spec in self.output_specs.items():
            if name in self.widgets:
                value = self.outputs[name].get()
                if value is not None:
                    if hasattr(value, "magnitude"):
                        # Format to 5 significant figures
                        self.widgets[name].value = float(f"{value.magnitude:.5g}")
                    else:
                        self.widgets[name].value = float(f"{value:.5g}")
        for name, spec in self.input_specs.items():
            if name in self.widgets:
                value = self.inputs[name].get()
                if value is not None:
                    if hasattr(value, "magnitude"):
                        self.widgets[name].value = float(f"{value.magnitude:.5g}")
                    else:
                        self.widgets[name].value = float(f"{value:.5g}")

    def display_monitoring(self):
        """Display the monitoring interface."""
        display(self.monitoring_display)
        display(self.scene_header)
