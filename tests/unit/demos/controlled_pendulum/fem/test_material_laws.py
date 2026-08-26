"""Unit tests for the SVK and Neo-Hookean material laws used by FEMPendulum.

These tests evaluate ``cauchy_stress`` and ``von_mises`` against closed-form
expectations for hand-picked deformation gradients. They do not require the
FEMPendulum component or contact — only a small unit-square mesh and a
prescribed displacement field.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.fem

ngsolve = pytest.importorskip("ngsolve")
netgen_occ = pytest.importorskip("netgen.occ")

import numpy as np  # noqa: E402
from netgen.occ import OCCGeometry, Rectangle  # noqa: E402
from ngsolve import CF, GridFunction, Integrate, Mesh, Norm, VectorH1, x, y  # noqa: E402

from syssimx_examples.controlled_pendulum.components.fem.material_laws import (  # noqa: E402
    NeoHookeanMaterial,
    SVKMaterial,
)

E_MOD = 70e9
NU = 0.3
MATERIALS = [NeoHookeanMaterial, SVKMaterial]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _unit_square_mesh(maxh: float = 0.5) -> Mesh:
    geo = OCCGeometry(Rectangle(1, 1).Face(), dim=2)
    return Mesh(geo.GenerateMesh(maxh=maxh))


def _displacement(mesh: Mesh, u_cf, order: int = 2) -> GridFunction:
    V = VectorH1(mesh, order=order)
    gf = GridFunction(V)
    gf.Set(u_cf)
    return gf


def _mean(expr, mesh: Mesh) -> float:
    return Integrate(expr, mesh) / Integrate(1, mesh)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("Material", MATERIALS)
def test_zero_displacement_zero_stress(Material):
    """At u = 0: F = I, so σ = 0 and σ_vM = 0."""
    mesh = _unit_square_mesh()
    mat = Material(E_MOD, NU)
    u = _displacement(mesh, CF((0.0, 0.0)))

    frobenius = _mean(Norm(mat.cauchy_stress(u)), mesh)
    von_mises = _mean(mat.von_mises(u), mesh)

    assert abs(frobenius) < 1e-3
    assert abs(von_mises) < 1e-3


@pytest.mark.parametrize("Material", MATERIALS)
def test_rigid_rotation_zero_stress(Material):
    """Frame indifference: a rigid rotation of the body must produce no stress."""
    mesh = _unit_square_mesh()
    mat = Material(E_MOD, NU)

    theta = 0.3
    c, s = np.cos(theta), np.sin(theta)
    u_cf = CF((c * x - s * y - x, s * x + c * y - y))
    u = _displacement(mesh, u_cf)

    von_mises = _mean(mat.von_mises(u), mesh)
    # Small numerical noise from FE interpolation at order 2; tolerate 1e-3 · E
    assert abs(von_mises) < 1e-3 * E_MOD


@pytest.mark.parametrize("Material", MATERIALS)
def test_uniaxial_small_strain_matches_linear_elasticity(Material):
    """Plane-stress uniaxial tension at small ε: σ_xx → E·ε, σ_yy → 0."""
    mesh = _unit_square_mesh()
    mat = Material(E_MOD, NU)

    eps = 1e-5
    u_cf = CF((eps * x, -NU * eps * y))
    u = _displacement(mesh, u_cf)

    sigma = mat.cauchy_stress(u)
    sxx = _mean(sigma[0, 0], mesh)
    syy = _mean(sigma[1, 1], mesh)

    expected = E_MOD * eps
    assert abs(sxx - expected) / expected < 1e-2
    assert abs(syy) / expected < 1e-2


@pytest.mark.parametrize("Material", MATERIALS)
def test_equibiaxial_von_mises_plane_stress(Material):
    """Equibiaxial tension (σ_xx = σ_yy = σ, σ_xy = 0): plane-stress σ_vM = |σ|."""
    mesh = _unit_square_mesh()
    mat = Material(E_MOD, NU)

    eps = 1e-5
    u_cf = CF((eps * x, eps * y))
    u = _displacement(mesh, u_cf)

    sigma = mat.cauchy_stress(u)
    sxx = _mean(sigma[0, 0], mesh)
    syy = _mean(sigma[1, 1], mesh)
    svm = _mean(mat.von_mises(u), mesh)

    assert abs(sxx - syy) / abs(sxx) < 1e-3
    # σ_vM = √(sxx² + syy² − sxx·syy) = |sxx| when sxx = syy
    assert abs(svm - abs(sxx)) / abs(sxx) < 1e-2


def test_svk_and_neohookean_agree_at_small_strain():
    """Both models must reduce to linear elasticity at small strain."""
    mesh = _unit_square_mesh()
    svk = SVKMaterial(E_MOD, NU)
    nh = NeoHookeanMaterial(E_MOD, NU)

    eps = 1e-6
    u_cf = CF((eps * x, -NU * eps * y))
    u = _displacement(mesh, u_cf)

    sxx_svk = _mean(svk.cauchy_stress(u)[0, 0], mesh)
    sxx_nh = _mean(nh.cauchy_stress(u)[0, 0], mesh)

    assert abs(sxx_svk - sxx_nh) / abs(sxx_svk) < 1e-3
