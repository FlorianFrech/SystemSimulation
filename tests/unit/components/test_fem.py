"""Unit tests for syssimx.components.fem.FEMComponent.

FEMComponent is now the concrete NGSolve transient structural-mechanics base
(Newmark integration, snapshot/restore, multidim history, reset), so these
tests require ngsolve and exercise that machinery through a minimal concrete
subclass.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.fem

ngsolve = pytest.importorskip("ngsolve")
netgen_occ = pytest.importorskip("netgen.occ")

import numpy as np  # noqa: E402
from netgen.occ import OCCGeometry, Rectangle  # noqa: E402
from ngsolve import GridFunction, Mesh, Parameter, VectorH1  # noqa: E402

from syssimx.components.fem import FEMComponent  # noqa: E402


def _unit_square_mesh(maxh: float = 0.5) -> Mesh:
    return Mesh(OCCGeometry(Rectangle(1, 1).Face(), dim=2).GenerateMesh(maxh=maxh))


class _MiniFEM(FEMComponent):
    """Minimal concrete NGSolve transient component for testing the base."""

    def __init__(self, name: str = "mini"):
        super().__init__(name=name)
        self.solved = 0

    def _initialize_component(self, t0: float) -> None:
        self._mesh = _unit_square_mesh()
        fes = VectorH1(self._mesh, order=1)
        self._init_newmark_state(fes)
        self.tau = Parameter(0.1)
        self._gf_hist = GridFunction(fes, multidim=0)
        self._register_history_field("_gf_hist", lambda: self._gf_u.vec)

    def _solve_step(self) -> None:
        self.solved += 1

    def _update_output_states(self, t=None, event_names=None) -> None:
        pass

    def get_state(self):
        return {}

    def set_state(self, state, t: float) -> None:
        pass


def _fill(gf, value: float) -> None:
    gf.vec.FV().NumPy()[:] = value


def _vec(gf) -> np.ndarray:
    return gf.vec.FV().NumPy().copy()


# ---------------------------------------------------------------------------
# Abstractness
# ---------------------------------------------------------------------------
def test_fem_component_is_abstract():
    """FEMComponent cannot be instantiated directly (abstract _solve_step etc.)."""
    with pytest.raises(TypeError):
        FEMComponent("fem")


# ---------------------------------------------------------------------------
# Newmark integration
# ---------------------------------------------------------------------------
def test_shift_newmark_state_copies_current_to_previous():
    comp = _MiniFEM()
    comp.initialize(t0=0.0)
    _fill(comp._gf_u, 3.0)
    _fill(comp._gf_v, 4.0)
    _fill(comp._gf_a, 5.0)

    comp._shift_newmark_state()

    assert np.allclose(_vec(comp._gf_uold), 3.0)
    assert np.allclose(_vec(comp._gf_vold), 4.0)
    assert np.allclose(_vec(comp._gf_aold), 5.0)


def test_advance_newmark_matches_trapezoidal_update():
    comp = _MiniFEM()
    comp.initialize(t0=0.0)
    comp.tau.Set(0.1)
    _fill(comp._gf_u, 2.0)
    _fill(comp._gf_uold, 1.0)
    _fill(comp._gf_vold, 0.5)
    _fill(comp._gf_aold, 0.25)

    comp._advance_newmark()

    tau = 0.1
    v_expected = 2 / tau * (2.0 - 1.0) - 0.5
    a_expected = 2 / tau * (v_expected - 0.5) - 0.25
    assert np.allclose(_vec(comp._gf_v), v_expected)
    assert np.allclose(_vec(comp._gf_a), a_expected)


# ---------------------------------------------------------------------------
# Snapshot / restore
# ---------------------------------------------------------------------------
def test_snapshot_restore_roundtrip():
    comp = _MiniFEM()
    comp.initialize(t0=0.0)
    comp.tau.Set(0.1)
    _fill(comp._gf_u, 1.0)
    _fill(comp._gf_v, 2.0)
    _fill(comp._gf_a, 3.0)
    _fill(comp._gf_uold, 4.0)
    _fill(comp._gf_vold, 5.0)
    _fill(comp._gf_aold, 6.0)
    comp.t = 0.3

    snap = comp.snapshot_state()
    assert snap["mode"] == "FEM"

    # Corrupt the live state.
    for gf in (comp._gf_u, comp._gf_v, comp._gf_a, comp._gf_uold, comp._gf_vold, comp._gf_aold):
        _fill(gf, 0.0)
    comp.tau.Set(0.9)
    comp.t = 99.0

    comp.restore_state(snap, t=0.3)

    assert np.allclose(_vec(comp._gf_u), 1.0)
    assert np.allclose(_vec(comp._gf_v), 2.0)
    assert np.allclose(_vec(comp._gf_a), 3.0)
    assert np.allclose(_vec(comp._gf_uold), 4.0)
    assert np.allclose(_vec(comp._gf_vold), 5.0)
    assert np.allclose(_vec(comp._gf_aold), 6.0)
    assert comp.tau.Get() == pytest.approx(0.1)
    assert comp.t == pytest.approx(0.3)


def test_restore_state_rejects_foreign_mode():
    comp = _MiniFEM()
    comp.initialize(t0=0.0)
    with pytest.raises(ValueError):
        comp.restore_state({"mode": "FMU"}, t=0.0)


# ---------------------------------------------------------------------------
# Multidim history recording + gating
# ---------------------------------------------------------------------------
def test_record_history_frame_appends_when_enabled():
    comp = _MiniFEM()
    comp.initialize(t0=0.0)
    assert len(comp._gf_hist.vecs) == 0

    comp._record_history = True
    comp._record_history_frame()
    assert len(comp._gf_hist.vecs) == 1


def test_record_history_frame_skipped_when_disabled():
    comp = _MiniFEM()
    comp.initialize(t0=0.0)

    comp._record_history = False
    comp._record_history_frame()
    assert len(comp._gf_hist.vecs) == 0


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------
def test_reset_zeros_newmark_state():
    comp = _MiniFEM()
    comp.initialize(t0=0.0)
    for gf in (comp._gf_u, comp._gf_v, comp._gf_a, comp._gf_uold, comp._gf_vold, comp._gf_aold):
        _fill(gf, 7.0)

    comp.reset()

    for gf in (comp._gf_u, comp._gf_v, comp._gf_a, comp._gf_uold, comp._gf_vold, comp._gf_aold):
        assert np.allclose(_vec(gf), 0.0)


# ---------------------------------------------------------------------------
# Optional file-I/O hooks
# ---------------------------------------------------------------------------
def test_optional_io_hooks_raise():
    comp = _MiniFEM()
    with pytest.raises(NotImplementedError):
        comp.load_mesh_from_file(Path("mesh.vtk"))
    with pytest.raises(NotImplementedError):
        comp.export_results(Path("results.vtk"))
