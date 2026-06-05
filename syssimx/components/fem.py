"""NGSolve transient structural-mechanics co-simulation wrapper.

``FEMComponent`` is the concrete FEM backend for SysSimX. It wraps an NGSolve
finite-element model that is advanced in time with a constant-average-acceleration
(trapezoidal) Newmark scheme and exposes it through the ``CoSimComponent``
interface. The class owns the parts that are common to any transient structural
NGSolve model:

* the Newmark state grid functions ``(u, v, a)`` and their previous-step
  buffers ``(u_old, v_old, a_old)`` and the velocity/acceleration update,
* snapshot / restore of that state for hybrid event localization and rollback,
* multidim grid-function history recording (gated by ``_record_history``),
* ``reset`` of the Newmark state,
* a micro-stepped ``do_step`` loop built from overridable hooks.

A concrete model (e.g. the controlled FEM pendulum) subclasses this and supplies
the mesh, finite-element spaces, the variational form, and the physics-specific
hooks. The base is deliberately backend-specific (NGSolve) and problem-specific
(transient structural dynamics); a non-transient NGSolve model can override the
step hooks to opt out of the Newmark update.

Requires the ``ngsolve`` optional dependency (``pip install syssimx[fem]``).
"""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ngsolve import GridFunction, TaskManager

from ..core.base import CoSimComponent


class FEMComponent(CoSimComponent):
    """Concrete NGSolve transient structural-mechanics component.

    Subclasses implement :meth:`_initialize_component` (build mesh, spaces,
    forms, initial state) and :meth:`_solve_step` (the nonlinear solve of one
    sub-step), and may override the optional step hooks below.
    """

    def __init__(self, name: str, label: str | None = None, group: str | None = None):
        super().__init__(name, label, group)

        # Geometry / mesh / finite-element space (populated by the subclass).
        self.geometry: Any = None
        self._mesh: Any = None
        self._fes: Any = None

        # Newmark state grid functions (allocated by _init_newmark_state).
        self._gf_u: Any = None
        self._gf_v: Any = None
        self._gf_a: Any = None
        self._gf_uold: Any = None
        self._gf_vold: Any = None
        self._gf_aold: Any = None

        # Communication / sub-step size parameter (an ngsolve Parameter created
        # by the subclass, typically while assembling the variational form).
        self.tau: Any = None

        # Registered multidim history fields: (history_attr_name, source_vec_fn).
        self._history_fields: list[tuple[str, Callable[[], Any]]] = []

        # Time of the most recent accepted sub-step start (used by hooks that
        # report internal events with [t_before, t_after] intervals).
        self._t_prev: float = 0.0

    # ------------------------------------------------------------------
    # Newmark state management
    # ------------------------------------------------------------------
    def _init_newmark_state(self, fes: Any) -> None:
        """Allocate the six Newmark state grid functions over ``fes``."""
        self._fes = fes
        self._gf_u = GridFunction(fes)  # current displacement
        self._gf_v = GridFunction(fes)  # current velocity
        self._gf_a = GridFunction(fes)  # current acceleration
        self._gf_uold = GridFunction(fes)  # previous displacement
        self._gf_vold = GridFunction(fes)  # previous velocity
        self._gf_aold = GridFunction(fes)  # previous acceleration

    def _shift_newmark_state(self) -> None:
        """Copy the current state into the previous-step buffers."""
        self._gf_uold.vec[:] = self._gf_u.vec
        self._gf_vold.vec[:] = self._gf_v.vec
        self._gf_aold.vec[:] = self._gf_a.vec

    def _advance_newmark(self) -> None:
        """Update velocity and acceleration from the freshly solved displacement.

        Constant-average-acceleration (trapezoidal) Newmark update:
            v = 2/τ (u - u_old) - v_old
            a = 2/τ (v - v_old) - a_old
        """
        tau = self.tau.Get()
        self._gf_v.vec[:] = 2 / tau * (self._gf_u.vec - self._gf_uold.vec) - self._gf_vold.vec
        self._gf_a.vec[:] = 2 / tau * (self._gf_v.vec - self._gf_vold.vec) - self._gf_aold.vec

    # ------------------------------------------------------------------
    # Multidim history recording
    # ------------------------------------------------------------------
    def _register_history_field(self, history_attr: str, source_vec_fn: Callable[[], Any]) -> None:
        """Register a history grid function to receive a frame each sub-step.

        Args:
            history_attr: Name of the ``GridFunction(..., multidim=0)`` attribute
                on this component that accumulates frames. Resolved by name at
                record time so it survives reallocation in ``reset``.
            source_vec_fn: Callable returning the source vector to append.
        """
        self._history_fields.append((history_attr, source_vec_fn))

    def _record_history_frame(self) -> None:
        """Append one frame to every registered history field.

        Skipped when ``_record_history`` is False (e.g. during hybrid trial
        steps) so the history reflects accepted simulation time only.
        """
        if not self._record_history:
            return
        for history_attr, source_vec_fn in self._history_fields:
            getattr(self, history_attr).AddMultiDimComponent(source_vec_fn())

    # ------------------------------------------------------------------
    # Snapshot / restore for hybrid event localization
    # ------------------------------------------------------------------
    def snapshot_state(self) -> dict[str, Any]:
        """Capture the complete Newmark state (current and previous step)."""
        snapshot = {
            "mode": "FEM",
            "u": self._gf_u.vec.FV().NumPy().copy(),
            "v": self._gf_v.vec.FV().NumPy().copy(),
            "a": self._gf_a.vec.FV().NumPy().copy(),
            "u_old": self._gf_uold.vec.FV().NumPy().copy(),
            "v_old": self._gf_vold.vec.FV().NumPy().copy(),
            "a_old": self._gf_aold.vec.FV().NumPy().copy(),
            "tau": self.tau.Get(),
            "t": self.t,
        }
        snapshot.update(self._extra_snapshot())
        return snapshot

    def restore_state(self, snapshot: dict[str, Any], t: float) -> None:
        """Restore the complete Newmark state from a snapshot."""
        if snapshot.get("mode", "") != "FEM":
            raise ValueError(
                f"[{self.name}] Incompatible snapshot mode, got '{snapshot.get('mode', '')}'."
            )

        self.internal_event_hints.clear()
        self.t = t

        # Current state
        self._gf_u.vec.FV().NumPy()[:] = snapshot["u"]
        self._gf_v.vec.FV().NumPy()[:] = snapshot["v"]
        self._gf_a.vec.FV().NumPy()[:] = snapshot["a"]

        # Previous time step (required to continue the Newmark recursion)
        self._gf_uold.vec.FV().NumPy()[:] = snapshot["u_old"]
        self._gf_vold.vec.FV().NumPy()[:] = snapshot["v_old"]
        self._gf_aold.vec.FV().NumPy()[:] = snapshot["a_old"]

        self.tau.Set(snapshot["tau"])
        self._restore_extra(snapshot)

        self._update_output_states(t)
        self._record_outputs(t)

    def _extra_snapshot(self) -> dict[str, Any]:
        """Subclass hook: extra fields to add to the snapshot (e.g. contact gap)."""
        return {}

    def _restore_extra(self, snapshot: dict[str, Any]) -> None:
        """Subclass hook: restore extra fields captured by ``_extra_snapshot``."""

    # ------------------------------------------------------------------
    # Time stepping (micro-stepped Newmark loop built from hooks)
    # ------------------------------------------------------------------
    def do_step(self, t: float, dt: float) -> None:
        """Advance from ``t`` to ``t + dt`` via internal micro-stepping.

        Overrides the single-shot ``CoSimComponent.do_step``: outputs and
        history are updated within each accepted sub-step so that recorded
        results and internal event hints are sub-step accurate.
        """
        self._do_step_internal(t, dt)

    def _do_step_internal(self, t: float, dt: float) -> None:
        self.internal_event_hints.clear()

        effective_dt = self._effective_substep(dt)
        t_current = t
        t_end = t + dt

        with TaskManager():
            while t_current < t_end - 1e-12:
                tau = min(effective_dt, t_end - t_current)
                self.tau.Set(tau)

                # Advance the Newmark history: previous <- current
                self._shift_newmark_state()

                # Hook: contact update / adaptive sub-step selection. May call
                # self.tau.Set(...) to reduce the sub-step.
                self._pre_solve(t_current, effective_dt)

                # Commit the (possibly reduced) sub-step.
                t_current += self.tau.Get()

                # Hook: nonlinear solve of the variational form.
                self._solve_step()

                # Newmark velocity/acceleration update from the new displacement.
                self._advance_newmark()

                # Hook: post-solve diagnostics (event detection, stress, ...).
                self._post_solve(t_current)

                # Visualization history (gated by _record_history).
                self._record_history_frame()

                # Outputs and recorded port history.
                self._update_output_states(t_current)
                if self._record_history:
                    self._record_outputs(t_current)

                # Hook: live visualization / monitoring update.
                self._after_substep(t_current)

        self.t = t_current

    # ---- Step hooks (overridable; sensible defaults) ----
    def _effective_substep(self, dt: float) -> float:
        """Return the nominal internal sub-step for a macro step ``dt``."""
        return dt

    def _pre_solve(self, t_current: float, effective_dt: float) -> None:
        """Hook before the nonlinear solve (e.g. contact update, adaptive τ)."""

    @abstractmethod
    def _solve_step(self) -> None:
        """Solve the nonlinear variational form for the current sub-step."""

    def _post_solve(self, t_current: float) -> None:
        """Hook after the Newmark update (e.g. event detection, stress fields)."""

    def _after_substep(self, t_current: float) -> None:
        """Hook after outputs are recorded (e.g. redraw, monitoring update)."""

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------
    def reset(self) -> None:
        """Zero the Newmark state grid functions."""
        super().reset()
        for gf in (
            self._gf_u,
            self._gf_v,
            self._gf_a,
            self._gf_uold,
            self._gf_vold,
            self._gf_aold,
        ):
            if gf is not None:
                gf.vec[:] = 0

    # ------------------------------------------------------------------
    # Optional file-I/O hooks (raise by default)
    # ------------------------------------------------------------------
    def load_mesh_from_file(self, path: Path) -> None:
        """Optional: load a mesh from file (GMSH, VTK, XDMF, ...)."""
        raise NotImplementedError(f"{self.name}: load_mesh_from_file not implemented")

    def export_results(self, path: Path, format: str = "vtk") -> None:
        """Optional: export the time series to file."""
        raise NotImplementedError(f"{self.name}: export_results not implemented")
