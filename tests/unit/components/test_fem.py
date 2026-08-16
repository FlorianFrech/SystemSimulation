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
        self.tau_step = Parameter(0.1)
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


class _SteppingFEM(_MiniFEM):
    """Minimal FEM with controllable nominal and adaptive sub-steps."""

    def __init__(
        self,
        nominal_dt: float | None = None,
        adaptive_dt: float | None = None,
    ):
        super().__init__()
        self.nominal_dt = nominal_dt
        self.adaptive_dt = adaptive_dt
        self.accepted_steps: list[float] = []

    def _effective_substep(self, dt: float) -> float:
        return dt if self.nominal_dt is None else self.nominal_dt

    def _pre_solve(self, t_current: float, effective_dt: float) -> None:
        if self.adaptive_dt is not None:
            self.tau_step.Set(self.adaptive_dt)

    def _solve_step(self) -> None:
        self.accepted_steps.append(self.tau_step.Get())
        super()._solve_step()


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
    comp.tau_step.Set(0.1)
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
# Time-step validation
# ---------------------------------------------------------------------------
def test_do_step_requires_initialization():
    comp = _MiniFEM()

    with pytest.raises(RuntimeError, match="must be initialized before stepping"):
        comp.do_step(t=0.0, dt=0.1)


@pytest.mark.parametrize("t", [float("inf"), float("-inf"), float("nan")])
def test_do_step_rejects_nonfinite_start_time(t):
    comp = _MiniFEM()
    comp.initialize(t0=0.0)

    with pytest.raises(ValueError, match="start time t must be finite"):
        comp.do_step(t=t, dt=0.1)


@pytest.mark.parametrize("dt", [-0.1, float("inf"), float("-inf"), float("nan")])
def test_do_step_rejects_invalid_macro_step(dt):
    comp = _MiniFEM()
    comp.initialize(t0=0.0)

    with pytest.raises(ValueError, match="dt must be finite and non-negative"):
        comp.do_step(t=0.0, dt=dt)


def test_zero_step_is_initialization_noop():
    comp = _MiniFEM()
    comp.initialize(t0=0.0)

    comp.do_step(t=0.0, dt=0.0)

    assert comp.solved == 0
    assert comp.t == pytest.approx(0.0)


@pytest.mark.parametrize("nominal_dt", [0.0, -0.1, float("inf"), float("nan")])
def test_do_step_rejects_invalid_effective_substep(nominal_dt):
    comp = _SteppingFEM(nominal_dt=nominal_dt)
    comp.initialize(t0=0.0)

    with pytest.raises(ValueError, match="Effective FEM sub-step"):
        comp.do_step(t=0.0, dt=0.1)

    assert comp.solved == 0


@pytest.mark.parametrize("adaptive_dt", [0.0, -0.1, float("inf"), float("nan")])
def test_do_step_rejects_invalid_adaptive_substep(adaptive_dt):
    comp = _SteppingFEM(nominal_dt=0.1, adaptive_dt=adaptive_dt)
    comp.initialize(t0=0.0)

    with pytest.raises(ValueError, match="Adaptive FEM sub-step"):
        comp.do_step(t=0.0, dt=0.1)

    assert comp.solved == 0


def test_adaptive_substep_is_bounded_by_nominal_and_remaining_time():
    comp = _SteppingFEM(nominal_dt=0.1, adaptive_dt=0.2)
    comp.initialize(t0=0.0)

    comp.do_step(t=0.0, dt=0.25)

    assert comp.accepted_steps == pytest.approx([0.1, 0.1, 0.05])
    assert comp.solved == 3
    assert comp.t == pytest.approx(0.25)


def test_substep_loop_does_not_take_a_vanishing_residual_step():
    """Regression: a macro step split into many equal sub-steps must not end
    with a floating-point residue sub-step.

    ``_advance_newmark`` computes ``v = 2/tau (u - u_old)``. A residue of order
    1e-18 gives an amplifier of order 1e17, which turns round-off into
    unbounded velocities and diverges the nonlinear solve. Reproduces the
    controlled-pendulum contact ratio: a 1e-4 s adaptive sub-step inside a
    1e-2 s macro step.
    """
    comp = _SteppingFEM(nominal_dt=2e-3, adaptive_dt=1e-4)
    comp.initialize(t0=0.0)

    comp.do_step(t=0.0, dt=1e-2)

    assert len(comp.accepted_steps) == 100
    assert min(comp.accepted_steps) == pytest.approx(1e-4)
    assert comp.t == 1e-2


def test_substep_loop_still_covers_the_full_macro_step():
    """The residue tolerance must not drop real work: sub-steps still sum to dt."""
    comp = _SteppingFEM(nominal_dt=3e-4, adaptive_dt=3e-4)
    comp.initialize(t0=0.0)

    comp.do_step(t=0.0, dt=1e-3)

    assert sum(comp.accepted_steps) == pytest.approx(1e-3, rel=1e-9)
    assert comp.t == pytest.approx(1e-3)


def test_do_step_rejects_unrepresentable_time_advance():
    comp = _MiniFEM()
    comp.initialize(t0=1.0)

    with pytest.raises(ValueError, match="does not produce a finite time advance"):
        comp.do_step(t=1.0, dt=1e-20)

    assert comp.solved == 0


# ---------------------------------------------------------------------------
# Snapshot / restore
# ---------------------------------------------------------------------------
def test_snapshot_restore_roundtrip():
    comp = _MiniFEM()
    comp.initialize(t0=0.0)
    comp.tau_step.Set(0.1)
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
    comp.tau_step.Set(0.9)
    comp.t = 99.0

    comp.restore_state(snap, t=0.3)

    assert np.allclose(_vec(comp._gf_u), 1.0)
    assert np.allclose(_vec(comp._gf_v), 2.0)
    assert np.allclose(_vec(comp._gf_a), 3.0)
    assert np.allclose(_vec(comp._gf_uold), 4.0)
    assert np.allclose(_vec(comp._gf_vold), 5.0)
    assert np.allclose(_vec(comp._gf_aold), 6.0)
    assert comp.tau_step.Get() == pytest.approx(0.1)
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
