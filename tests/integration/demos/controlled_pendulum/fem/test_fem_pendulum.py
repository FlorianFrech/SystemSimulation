"""End-to-end integration tests for the FEMPendulum component.

These tests run the full FEM simulation and are therefore slow — marked with
both ``fem`` and ``slow`` so they can be excluded from default CI runs via
``pytest -m "not slow"``.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.fem, pytest.mark.slow]

ngsolve = pytest.importorskip("ngsolve")

import numpy as np  # noqa: E402

from demos.ControlledPendulum.src.master_pendulum.components.fem import pendulum_config as cfg  # noqa: E402
from demos.ControlledPendulum.src.master_pendulum.components.fem.fem_pendulum import (  # noqa: E402
    FEMPendulum,
)


def _build_pendulum(
    *,
    with_contact: bool,
    use_gravity: bool,
    theta0_deg: float,
    omega0: float = 0.0,
    tau: float = 0.002,
    t_end: float = 0.6,
    model: str = "svk",
) -> FEMPendulum:
    pend = FEMPendulum(name="FEM_Pendulum")

    mesh_params = cfg.MeshParameters()
    mesh_params.max_element_size = 0.1 / 4

    mat_params = cfg.MaterialParameters()
    mat_params.model = model
    mat_params.E_pendulum = 2.1e11
    mat_params.nu_pendulum = 0.3
    mat_params.rho_pendulum = 7800

    init_params = cfg.InitialConditionParameters()
    init_params.angular_position_deg = theta0_deg
    init_params.angular_velocity = omega0
    init_params.drive_torque = 0.0

    sim_params = cfg.SimulationParameters()
    sim_params.tau = tau
    sim_params.t_end = t_end
    sim_params.with_contact = with_contact
    sim_params.use_gravity = use_gravity

    anim_params = cfg.AnimationParameters()
    anim_params.animate = False

    pend.set_parameters(
        mat_params=mat_params,
        init_params=init_params,
        sim_params=sim_params,
        anim_params=anim_params,
        mesh_params=mesh_params,
    )
    pend.initialize(0.0)
    return pend


def _run(pend: FEMPendulum, t_end: float, dt: float) -> None:
    t = 0.0
    while t < t_end - 1e-12:
        pend.do_step(t, dt)
        t += dt


def test_impact_peak_omega_matches_rigid_body_theory():
    """Swinging from θ₀=20° with contact, peak |ω| at impact must match
    ω_max = √(2·m·g·L·(1−cos θ₀) / I) from energy conservation."""
    theta0_deg = 20.0
    pend = _build_pendulum(
        with_contact=True,
        use_gravity=True,
        theta0_deg=theta0_deg,
        tau=0.002,
        t_end=0.6,
    )
    _run(pend, t_end=0.6, dt=0.01)

    history = pend.get_history()
    omega_vals = np.asarray(history["omega"]["values"])

    theta0 = np.deg2rad(theta0_deg)
    L = pend._equivalent_length
    m = pend.mass
    I = pend.inertia
    omega_max = np.sqrt(2 * m * 9.81 * L * (1 - np.cos(theta0)) / I)

    peak = np.max(np.abs(omega_vals))
    assert peak == pytest.approx(omega_max, rel=0.1), (
        f"Peak |ω|={peak:.3f} rad/s; theory predicts {omega_max:.3f} rad/s"
    )


def test_rigid_rotation_initial_condition_has_small_stress():
    """Setting θ₀=20° with no gravity and no contact should not excite
    significant deformation — only a rigid rotation of the reference field.

    At t=0 the FEM solver has not yet run; we just check that the stress
    evaluated from the prescribed initial displacement is small relative to E.
    """
    pend = _build_pendulum(
        with_contact=False,
        use_gravity=False,
        theta0_deg=20.0,
        tau=0.002,
        t_end=0.0,
    )
    u_cur = pend._gf_u.components[0]
    vm_peak = max(
        pend._von_mises_p(u_cur)(pend._mesh(px, py))
        for px, py in [(0.05, -0.1), (0.0, -0.2), (-0.05, -0.1)]
    )
    assert vm_peak < 1e-3 * pend.mat_params.E_pendulum
