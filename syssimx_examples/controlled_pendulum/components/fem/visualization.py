"""NGSolve webgui visualization for the FEM pendulum.

Keeps the presentation concern (live stress scene, field plots, recorded
animations) out of the model class. The visualizer holds a back-reference to a
``FEMPendulum`` and renders its grid functions on demand, so it always reflects
the component's current state without duplicating it.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from ngsolve.webgui import Draw

_DEFAULT_ANIM_SETTINGS = {"Multidim": {"speed": 15}}


class FEMPendulumVisualizer:
    """Renders the grid functions of a :class:`FEMPendulum`.

    Args:
        pendulum: The FEM pendulum whose fields are visualized.
    """

    def __init__(self, pendulum: Any):
        self._p = pendulum
        self.scene = None

    # ------------------------------------------------------------------
    # Live stress scene
    # ------------------------------------------------------------------
    def initialize_scene(self):
        """Create the live von Mises stress scene and return it."""
        p = self._p
        self.scene = Draw(
            p._gf_von_mises,
            p._mesh,
            "von_mises_stress",
            deformation=p._gf_u.components[0],
            show=True,
        )
        return self.scene

    def redraw(self) -> None:
        """Redraw the live scene if it has been initialized."""
        if self.scene is not None:
            self.scene.Redraw()

    def update_scene(self, q, t: float) -> None:
        """Set the pendulum angle to ``q`` at time ``t`` and redraw."""
        if self.scene is not None:
            self._p.set_state({"theta": {"value": q}}, t)
            self.scene.Redraw()

    # ------------------------------------------------------------------
    # Instantaneous field plots
    # ------------------------------------------------------------------
    def visualize_state(
        self, draw_u: bool = True, draw_v: bool = True, draw_a: bool = True
    ) -> None:
        """Draw the displacement, velocity, and/or acceleration fields."""
        p = self._p
        if draw_u:
            Draw(p._gf_u.components[0], deformation=True)
        if draw_v:
            Draw(p._gf_v.components[0], deformation=p._gf_u.components[0], vectors=True)
        if draw_a:
            Draw(p._gf_a.components[0], deformation=p._gf_u.components[0], vectors=True)

    # ------------------------------------------------------------------
    # Recorded-history animations
    # ------------------------------------------------------------------
    def animate_displacement(self, settings: dict | None = None) -> None:
        """Animate the recorded displacement history.

        Requires that ``anim_params.animate`` was True during simulation so the
        history grid functions were populated.
        """
        p = self._p
        settings = settings or _DEFAULT_ANIM_SETTINGS
        if not hasattr(p, "_gf_u_history") or len(p._gf_u_history.vecs) == 0:
            raise RuntimeError(
                f"{p.name}: No displacement history recorded. "
                "Run with anim_params.animate=True to collect history."
            )
        Draw(
            p._gf_u_history,
            p._mesh,
            deformation=p._gf_u_history,
            animate=True,
            settings=settings,
        )

    def animate_stress(self, settings: dict | None = None) -> None:
        """Animate the recorded von Mises stress history with deformation.

        Requires that ``anim_params.animate`` was True during simulation so the
        history grid functions were populated.
        """
        p = self._p
        settings = settings or _DEFAULT_ANIM_SETTINGS
        if not hasattr(p, "_gf_von_mises_history") or len(p._gf_von_mises_history.vecs) == 0:
            raise RuntimeError(
                f"{p.name}: No stress history recorded. "
                "Run with anim_params.animate=True to collect history."
            )
        Draw(
            p._gf_von_mises_history,
            p._mesh,
            interpolation_multidim=True,
            deformation=p._gf_u_history,
            animate=True,
            autoscale=False,
            min=0,
            max=np.max([v.FV().NumPy().max() for v in p._gf_von_mises_history.vecs]),
            settings=settings,
        )
