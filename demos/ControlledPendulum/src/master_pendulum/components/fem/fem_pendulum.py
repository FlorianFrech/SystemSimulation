"""This module implements the FEMPendulum component using the Netgen/NGSolve finite element library.

The `FEMPendulum` class defines a finite element model of a controlled pendulum,
including optional contact with a wall and distributed torque control.

It provides methods for initializing the model, setting and getting the state, handling events, and snapshot/restore functionality for time integration. The component is designed to be used within a multi-model simulation framework, allowing it to be combined with other pendulum models (e.g., FMU, OpenSim) in a `MasterPendulum` component.
"""

import logging
from typing import Any

import numpy as np
from IPython.display import display
from ngsolve import (
    BND,
    CF,
    H1,
    BilinearForm,
    CoefficientFunction,
    Cof,
    ContactBoundary,
    Grad,
    GridFunction,
    Id,
    IfPos,
    InnerProduct,
    Integrate,
    IntegrationRule,
    MatrixValued,
    Norm,
    NumberSpace,
    Parameter,
    Variation,
    VectorH1,
    ds,
    dx,
    exp,
    specialcf,
    sqrt,
    x,
    y,
)
from ngsolve.solvers import NewtonMinimization

from syssimx.components.fem import FEMComponent
from syssimx.core.port import PortSpec, PortType
from syssimx.utilities.units import Quantity, ureg

from ...monitoring import PendulumMonitor, PendulumMonitoringState
from .material_laws import NeoHookeanMaterial, SVKMaterial
from .pendulum_config import (
    AnimationParameters,
    ContactParameters,
    GeometryParameters,
    InitialConditionParameters,
    MaterialParameters,
    MeshParameters,
    SimulationParameters,
)
from .pendulum_mesh import build_mesh
from .visualization import FEMPendulumVisualizer

logger = logging.getLogger(__name__)

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
        self.input_specs = INPUT_SPECS.copy()
        self.output_specs = OUTPUT_SPECS.copy()
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

        # When False, `_do_step_internal` skips appending to the multidim
        # history grid functions. The hybrid algorithm flips this off around
        # trial steps so the history reflects accepted simulation time only.
        self._record_history: bool = True

        # Monitoring: the observable state exists from construction (the step
        # loop writes to it); the widget panel is created in setup_monitoring().
        self.monitoring_state = PendulumMonitoringState()
        self.monitoring_state.mode = "FEM"
        self._monitor: PendulumMonitor | None = None

        # Visualization helper (NGSolve webgui scenes / animations).
        self._viz = FEMPendulumVisualizer(self)

        # Register the multidim history fields the base records each sub-step.
        # Resolved by attribute name so they survive reallocation in reset().
        self._register_history_field(
            "_gf_u_history", lambda: self._gf_u.components[0].vec
        )
        self._register_history_field("_gf_von_mises_history", lambda: self._gf_von_mises.vec)
        self._register_history_field(
            "_gf_cauchy_stress_history", lambda: self._gf_cauchy_stress.vec
        )

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

        model = getattr(self.mat_params, "model", "neo_hookean")

        _material_cls = {"neo_hookean": NeoHookeanMaterial, "svk": SVKMaterial}
        if model not in _material_cls:
            raise ValueError(f"Unknown material model '{model}'. Choose 'neo_hookean' or 'svk'.")

        self._material_pendulum = _material_cls[model](self.E_p, self.nu_p)
        self._material_wall     = _material_cls[model](self.E_w, self.nu_w)

        # These are the hooks used in _setup_bilinear_form — interface is identical
        self._deformation_gradient_p = self._material_pendulum.C
        self._psi_p                  = self._material_pendulum.psi
        self._cauchy_stress_p        = self._material_pendulum.cauchy_stress
        self._von_mises_p            = self._material_pendulum.von_mises

        self._deformation_gradient_w = self._material_wall.C
        self._psi_w                  = self._material_wall.psi
        # Wall stress hooks for post-processing on the wall region.
        self._cauchy_stress_w        = self._material_wall.cauchy_stress
        self._von_mises_w            = self._material_wall.von_mises

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

        # Stress spaces span pendulum and wall so that both regions carry
        # post-processed stress values. The wall is included because it
        # already participates in the simulation through its strain-energy
        # contribution to the bilinear form, and visualizing its stress
        # field makes the contact response symmetric across the interface.
        self._S_cauchy = MatrixValued(
            H1(self._mesh, order=self.mesh_params.mesh_order)
        )
        # Scalar H1 space for stress norm visualization (full mesh)
        self._V_vm = H1(self._mesh, order=self.mesh_params.mesh_order)

    def _initialize_grid_functions(self):
        """Initialize grid functions for state variables and stress."""
        # Newmark state (u, v, a and previous-step buffers) is owned by the base.
        self._init_newmark_state(self._fes)

        self._gf_cauchy_stress = GridFunction(self._S_cauchy)  # Stress
        self._gf_von_mises = GridFunction(self._V_vm)  # Stress norm (scalar)

        # Time series storage
        self._gf_u_history = GridFunction(self._V, multidim=0)
        self._gf_v_history = GridFunction(self._V, multidim=0)
        self._gf_cauchy_stress_history = GridFunction(self._S_cauchy, multidim=0)
        self._gf_von_mises_history = GridFunction(self._V_vm, multidim=0)

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
        self.tau_step = Parameter(self.sim_params.tau)
        vel_new = (
            2 / self.tau_step * (self._u - self._gf_uold.components[0]) - self._gf_vold.components[0]
        )
        acc_new = (
            2 / self.tau_step * (vel_new - self._gf_vold.components[0]) - self._gf_aold.components[0]
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
            self.tau_step.Set(dt)

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
    def _extra_snapshot(self) -> dict[str, Any]:
        """Add the contact-gap state to the base Newmark snapshot."""
        return {
            "gap": self.gap if self._with_contact else None,
            "gap_prev": self.gap_prev if self._with_contact else None,
        }

    def _restore_extra(self, snapshot: dict[str, Any]) -> None:
        """Restore the contact-gap state captured by ``_extra_snapshot``."""
        if self._with_contact:
            self.gap = snapshot.get("gap", float("inf"))
            self.gap_prev = snapshot.get("gap_prev", float("inf"))

    def _handle_events_internal(self, event_names, t):
        if "wall_hit" not in event_names:
            return

        if not self.in_trial:
            logger.info("[%s] Event 'wall_hit' at t=%.6fs.", self.name, t)

        # Invert velocity field (keep displacement and old states unchanged)
        if not self._with_contact:
            self._gf_v.vec.data = -1.0 * self._gf_v.vec
            self._gf_vold.vec.data = -1.0 * self._gf_vold.vec

            # Recompute acceleration from inverted velocity (Newmark update)
            tau = self.tau_step.Get()
            acc_new = 2 / tau * (self._gf_v.vec - self._gf_vold.vec) - self._gf_aold.vec
            self._gf_a.vec.data = acc_new

            # Update outputs
            self._update_output_states(t, event_names=event_names)
            self._record_outputs(t)

    # ----------------------------------------------------------------------------
    # Time stepping hooks (the micro-step loop lives in FEMComponent)
    # ----------------------------------------------------------------------------
    def _effective_substep(self, dt):
        """Nominal internal sub-step: the macro step, capped at sim_params.tau."""
        if dt < 1e-4:
            return dt
        elif dt < self.sim_params.tau:
            return dt
        return self.sim_params.tau

    def _pre_solve(self, t_current, effective_dt):
        """Update the contact set and reduce the sub-step near contact."""
        if not self._with_contact:
            return
        self._contact.Update(self._gf_u.components[0], self._bfa, intorder=10, maxdist=0.5)
        self.gap_prev = self._get_contact_gap_distance()
        self._t_prev = t_current
        if not self.in_trial:
            self.monitoring_state.gap = self.gap_prev

        # Reduce time step if the pendulum is close to contact.
        if effective_dt <= 1e-4:
            self.tau_step.Set(effective_dt)
        elif self.gap_prev < 0.001:
            self.tau_step.Set(1e-4)
        elif self.gap_prev < 0.005:
            self.tau_step.Set(5e-4)
        elif self.gap_prev < 0.01:
            self.tau_step.Set(1e-3)
        else:
            self.tau_step.Set(self.sim_params.tau)

    def _solve_step(self):
        """Solve the nonlinear elasticity system for the current sub-step."""
        NewtonMinimization(
            a=self._bfa,
            u=self._gf_u,
            printing=False,
            inverse="sparsecholesky",
            maxerr=self.sim_params.max_err,
            maxit=self.sim_params.max_it,
        )

    def _post_solve(self, t_current):
        """Detect the wall-contact event and recompute the stress fields."""
        # Check for wall contact event (gap crossing zero).
        if self._with_contact:
            self.gap = self._get_contact_gap_distance()
            if self.gap_prev > 0.0 and self.gap <= 0.0:
                # Report internal event with precise timing from the micro-steps.
                self.report_internal_event(
                    event_name="wall_hit",
                    t_before=self._t_prev,
                    t_after=t_current,
                    indicator_before=self.gap_prev,
                    indicator_after=self.gap,
                )

        # Compute stress on both materials. The piecewise CoefficientFunction
        # picks the pendulum or wall material law in the corresponding region.
        u_cur = self._gf_u.components[0]
        cauchy_per_mat = []
        vm_per_mat = []
        for mat in self._mesh.GetMaterials():
            if mat == "pendulum":
                cauchy_per_mat.append(self._cauchy_stress_p(u_cur))
                vm_per_mat.append(self._von_mises_p(u_cur))
            elif mat == "wall":
                cauchy_per_mat.append(self._cauchy_stress_w(u_cur))
                vm_per_mat.append(self._von_mises_w(u_cur))
            else:
                cauchy_per_mat.append(CF(((0, 0), (0, 0))))
                vm_per_mat.append(CF(0.0))
        self._gf_cauchy_stress.Interpolate(CF(cauchy_per_mat))
        self._gf_von_mises.Set(CF(vm_per_mat))

    def _after_substep(self, t_current):
        """Update the live monitoring state and redraw the scene."""
        self.monitoring_state.time = t_current
        self.monitoring_state.dt = self.tau_step.Get()
        if self.anim_params.animate:
            self._viz.redraw()
        self.update_monitoring()
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
        self, t: float | None = None, event_names: list[str] | None = None
    ):
        """
        Convert rigid-body proxy to output ports (called by base-class).
        """
        q_state, omega_state, alpha_state = self._rigid_proxy()
        self.outputs["theta"].set(q_state * ureg("rad"), t=t)
        self.outputs["omega"].set(omega_state * ureg("rad/s"), t=t)
        self.outputs["alpha"].set(alpha_state * ureg("rad/s^2"), t=t)
        self._apply_event_ports(t, event_names)

    # ----------------------------------------------------------------------------
    # Reset method
    # ----------------------------------------------------------------------------
    def reset(self):
        # The base zeros the Newmark state (u, v, a and previous-step buffers).
        if self._monitor is not None:
            self._monitor.close()
        has_runtime_fields = all(
            getattr(self, field_name, None) is not None
            for field_name in (
                "_gf_u",
                "_gf_cauchy_stress",
                "_gf_von_mises",
                "_V",
                "_S_cauchy",
                "_V_vm",
            )
        )
        super().reset()
        if has_runtime_fields:
            # Reset stress fields and reallocate the time-series history only
            # after the corresponding finite-element spaces have existed.
            self._gf_cauchy_stress.vec[:] = 0
            self._gf_von_mises.vec[:] = 0
            self._gf_u_history = GridFunction(self._V, multidim=0)
            self._gf_v_history = GridFunction(self._V, multidim=0)
            self._gf_cauchy_stress_history = GridFunction(self._S_cauchy, multidim=0)
            self._gf_von_mises_history = GridFunction(self._V_vm, multidim=0)
        self.monitoring_state = PendulumMonitoringState()
        self.monitoring_state.mode = "FEM"
        self._monitor = None

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
                    except Exception:
                        # Gap CF is undefined at points without a contact
                        # counterpart; skip those integration points.
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

        return KE, PE, self.strain_energy()

    def strain_energy(self) -> float:
        """Return the elastic strain energy stored in the deformed pendulum.

        The integral reads the current displacement field only, so it is safe
        to call inside a speculative advance or a state-transfer transaction.
        """
        return float(
            Integrate(
                self._psi_p(self._deformation_gradient_p(self._gf_u.components[0]), self._u),
                self._mesh,
                definedon=self._mesh.Materials("pendulum"),
            )
        )

    # ----------------------------------------------------------------------------
    # Visualization methods (delegated to FEMPendulumVisualizer)
    # ----------------------------------------------------------------------------
    def initialize_scene(self):
        """Initialize the live stress visualization scene."""
        return self._viz.initialize_scene()

    def update_scene(self, q: float | Quantity, t: float):
        """Update the live scene with a new pendulum angle ``q`` at time ``t``."""
        self._viz.update_scene(q, t)

    def visualize_state(self, draw_u: bool = True, draw_v: bool = True, draw_a: bool = True):
        """Draw the current displacement, velocity, and/or acceleration fields."""
        self._viz.visualize_state(draw_u=draw_u, draw_v=draw_v, draw_a=draw_a)

    def animate_displacement(self, settings: dict | None = None):
        """Animate the recorded displacement history."""
        self._viz.animate_displacement(settings)

    def animate_stress(self, settings: dict | None = None):
        """Animate the recorded von Mises stress history with deformation."""
        self._viz.animate_stress(settings)

    # ----------------------------------------------------------------------------
    # Monitoring interface methods (delegated to the shared PendulumMonitor)
    # ----------------------------------------------------------------------------
    def setup_monitoring(self) -> None:
        """Create the shared monitoring panel bound to ``monitoring_state``."""
        self._monitor = PendulumMonitor(
            self.input_specs,
            self.output_specs,
            t_end=self.sim_params.t_end,
            tau=self.sim_params.tau,
            mode="FEM",
            with_contact=self._with_contact,
            state=self.monitoring_state,
        )

    def update_monitoring(self):
        """Mirror current port values into the observable monitoring state."""
        if self._monitor is not None:
            self._monitor.sync_from_ports(self.inputs, self.outputs)

    def display_monitoring(self):
        """Display the monitoring panel and the stress-visualization header."""
        if self._monitor is None:
            self.setup_monitoring()
        self._monitor.display()
        display(self._monitor.scene_header)
