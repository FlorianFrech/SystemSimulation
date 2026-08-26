"""FE patch tests for the plane-stress constitutive law.

Unlike ``test_material_laws.py`` (which prescribes a displacement field and
checks the stress algebraically), these tests solve a tiny BVP and verify that
the recovered stress matches the imposed homogeneous-deformation analytical
expectation. This catches inconsistencies between the strain energy used in
``BilinearForm`` and the stress used for post-processing.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.fem

ngsolve = pytest.importorskip("ngsolve")
netgen_occ = pytest.importorskip("netgen.occ")

from netgen.occ import OCCGeometry, Rectangle  # noqa: E402
from ngsolve import (  # noqa: E402
    CF,
    BilinearForm,
    GridFunction,
    Integrate,
    Mesh,
    Variation,
    VectorH1,
    dx,
    x,
)
from ngsolve.solvers import NewtonMinimization  # noqa: E402

from syssimx_examples.controlled_pendulum.components.fem.material_laws import (  # noqa: E402
    NeoHookeanMaterial,
    SVKMaterial,
)

E_MOD = 70e9
NU = 0.3
MATERIALS = [NeoHookeanMaterial, SVKMaterial]


def _make_patch_mesh(maxh: float = 0.3) -> Mesh:
    rect = Rectangle(1, 1).Face()
    # Tag left/right edges for the u_x Dirichlet data and the bottom edge for
    # the u_y constraint that removes the vertical rigid-translation mode.
    for edge in rect.edges:
        p = edge.center
        if abs(p.x) < 1e-6:
            edge.name = "left"
        elif abs(p.x - 1.0) < 1e-6:
            edge.name = "right"
        elif abs(p.y) < 1e-6:
            edge.name = "bottom"
    geo = OCCGeometry(rect, dim=2)
    return Mesh(geo.GenerateMesh(maxh=maxh))


@pytest.mark.parametrize("Material", MATERIALS)
def test_uniaxial_tension_patch(Material):
    """Stretch a 1×1 square along x and recover σ_xx ≈ E·ε.

    Left edge: u_x = 0. Right edge: u_x = ε. Bottom edge: u_y = 0 — the exact
    uniaxial field u = (εx, -νεy) satisfies this, so the constraint only pins
    the vertical rigid-translation null space (without it the strain energy is
    translation-invariant in y, the tangent is singular, and Newton may
    diverge depending on round-off).
    The resulting field is uniaxial tension with lateral contraction determined
    by minimization of the strain energy — for plane stress this gives
    σ_yy ≈ 0 and σ_xx ≈ E·ε at small strain.
    """
    mesh = _make_patch_mesh()
    mat = Material(E_MOD, NU)

    eps = 1e-5

    fes = VectorH1(mesh, order=2, dirichletx="left|right", dirichlety="bottom")
    u = GridFunction(fes)
    # Prescribe x-displacement on Dirichlet boundaries; u_y = 0 on the bottom.
    u.components[0].Set(CF(0.0), definedon=mesh.Boundaries("left"))
    u.components[0].Set(CF(eps), definedon=mesh.Boundaries("right"))
    # Quick-and-dirty: use linear interpolation as initial guess in x.
    u.Set(CF((eps * x, 0.0)))

    trial = fes.TrialFunction()
    bfa = BilinearForm(fes)
    bfa += Variation(mat.psi(mat.C(trial), trial) * dx).Compile()

    NewtonMinimization(a=bfa, u=u, printing=False, maxerr=1e-10, maxit=30)

    sigma = mat.cauchy_stress(u)
    area = Integrate(1, mesh)
    sxx = Integrate(sigma[0, 0], mesh) / area
    syy = Integrate(sigma[1, 1], mesh) / area

    expected = E_MOD * eps
    # Patch tests on small meshes converge geometrically; 5% is plenty
    assert abs(sxx - expected) / expected < 5e-2
    assert abs(syy) / expected < 5e-2
