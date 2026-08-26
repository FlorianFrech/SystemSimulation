"""Structural / contract tests for the hyperelastic material hierarchy.

These complement ``test_material_laws.py`` (which checks the physics) by
verifying the refactored class structure: the shared
:class:`HyperelasticMaterial` base is abstract, the concrete laws derive from
it, the plane-stress Lamé parameters are computed in one place, and the shared
derived quantities (``PK1`` from ``PK2``) behave consistently.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.fem

ngsolve = pytest.importorskip("ngsolve")
netgen_occ = pytest.importorskip("netgen.occ")

from netgen.occ import OCCGeometry, Rectangle  # noqa: E402
from ngsolve import (  # noqa: E402
    CF,
    GridFunction,
    Grad,
    Id,
    Integrate,
    Mesh,
    Norm,
    VectorH1,
    x,
    y,
)

from syssimx_examples.controlled_pendulum.components.fem.material_laws import (  # noqa: E402
    HyperelasticMaterial,
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
# Class hierarchy
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("Material", MATERIALS)
def test_concrete_materials_are_hyperelastic(Material):
    """Both concrete laws derive from the shared base."""
    mat = Material(E_MOD, NU)
    assert isinstance(mat, HyperelasticMaterial)


def test_base_class_is_abstract():
    """HyperelasticMaterial cannot be instantiated directly."""
    with pytest.raises(TypeError):
        HyperelasticMaterial(E_MOD, NU)


def test_subclass_missing_pk2_is_abstract():
    """A subclass that omits PK2 stays abstract and cannot be instantiated."""

    class IncompleteMaterial(HyperelasticMaterial):
        def psi(self, C, u):  # provides psi but not PK2
            return 0.0

    with pytest.raises(TypeError):
        IncompleteMaterial(E_MOD, NU)


# ---------------------------------------------------------------------------
# Shared parameter computation
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("Material", MATERIALS)
def test_lame_parameters_plane_stress(Material):
    """mu and the plane-stress lambda are computed once in the base."""
    mat = Material(E_MOD, NU)
    assert mat.mu == pytest.approx(E_MOD / (2 * (1 + NU)))
    assert mat.lmbda == pytest.approx(E_MOD * NU / (1 - NU * NU))


# ---------------------------------------------------------------------------
# Shared derived stresses
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("Material", MATERIALS)
def test_pk2_zero_at_zero_displacement(Material):
    """At u = 0 the second Piola-Kirchhoff stress vanishes for both laws."""
    mesh = _unit_square_mesh()
    mat = Material(E_MOD, NU)
    u = _displacement(mesh, CF((0.0, 0.0)))
    assert abs(_mean(Norm(mat.PK2(u)), mesh)) < 1e-3


@pytest.mark.parametrize("Material", MATERIALS)
def test_pk1_equals_F_times_pk2(Material):
    """The shared PK1 must satisfy P = F·S for a non-trivial deformation."""
    mesh = _unit_square_mesh()
    mat = Material(E_MOD, NU)

    eps = 1e-4
    u = _displacement(mesh, CF((eps * x, -NU * eps * y)))

    F = Id(2) + Grad(u)
    residual = _mean(Norm(mat.PK1(u) - F * mat.PK2(u)), mesh)
    scale = _mean(Norm(mat.PK2(u)), mesh) + 1.0
    assert residual / scale < 1e-9
