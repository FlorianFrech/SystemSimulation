"""Model-artifact figures of the FEM pendulum (figure_style.md sections 2 and 3).

Both figures draw from the arrays ``evidence.fem_fields`` caches, never from a
live solver, so a style change costs seconds.

* ``draw_mesh`` is the reference mesh with its named boundaries.
* ``draw_stress`` has two panels. (a) is the peak-stress frame of the first
  impact the FEM resolved, zoomed on the contact. (b) is the outgoing state of
  the FEM -> rigid switch that discarded the most strain energy. The wall
  carries no field in (b), because the discarded energy is integrated over the
  pendulum only (``FEMPendulum.strain_energy``).

Geometry is drawn in the current configuration at displacement scale one. With
steel on steel the elastic deformation is invisible at that scale, and only the
rigid rotation shows, which is what the reader should see.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import matplotlib.tri as mtri
import numpy as np
from matplotlib.collections import LineCollection, PolyCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import MaxNLocator

from evidence.fem_fields import POINTS_PER_TRIANGLE, SUBTRIANGLES
from plot_setup import (
    BODY_FILLS,
    BODY_LABELS,
    BOUNDARY_LINEWIDTH,
    BOUNDARY_STYLES,
    FIELD_CMAP,
    FIELD_LEVELS,
    FIELD_MESH_STYLE,
    FULL_WIDTH,
    HALF_WIDTH,
    MESH_LINE_STYLE,
    PEAK_MARKER_STYLE,
    legend_above,
    panel_labels,
)

# Stress units, largest first. A panel takes the largest unit that keeps its
# peak at or above one, so no colour bar reads 0.000 to 0.004.
_STRESS_UNITS = ((1e6, r"\mega\pascal"), (1e3, r"\kilo\pascal"), (1.0, r"\pascal"))


def _triangulation(xy):
    """Four linear sub-triangles per element over its six sampled points."""
    n = xy.shape[0]
    local = np.asarray(SUBTRIANGLES, dtype=int)
    triangles = (POINTS_PER_TRIANGLE * np.arange(n)[:, None, None] + local).reshape(-1, 3)
    flat = xy.reshape(-1, 2)
    return mtri.Triangulation(flat[:, 0], flat[:, 1], triangles)


def _outlines(xy):
    """Element outlines through the three corners, for PolyCollection."""
    return xy[:, :3]


def _extent(xy, pad):
    flat = xy[:, :3].reshape(-1, 2)
    return (flat[:, 0].min() - pad, flat[:, 0].max() + pad,
            flat[:, 1].min() - pad, flat[:, 1].max() + pad)


def _bare_axes(ax, xy, pad):
    """Equal aspect, no ticks, no spines, limits fitted to ``xy``."""
    x0, x1, y0, y1 = _extent(xy, pad)
    ax.set_aspect("equal")
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
    ax.grid(False)
    for spine in ax.spines.values():
        spine.set_visible(False)


def _body_polys(ax, xy, materials, body, *, filled=True, **style):
    mask = materials == body
    polys = PolyCollection(
        _outlines(xy[mask]),
        facecolors=BODY_FILLS[body] if filled else "none",
        **style,
    )
    ax.add_collection(polys)
    return mask


def _boundaries(ax, xy, segments):
    """Named boundaries as line collections. Returns legend handles in style order."""
    flat = xy.reshape(-1, 2)
    handles = []
    for name, style in BOUNDARY_STYLES.items():
        pairs = segments.get(name)
        if pairs is None or len(pairs) == 0:
            continue
        ax.add_collection(LineCollection(
            flat[pairs], colors=style["color"], linestyles=style["linestyle"],
            linewidths=BOUNDARY_LINEWIDTH, capstyle="round", zorder=5,
        ))
        handles.append(Line2D([], [], color=style["color"], linestyle=style["linestyle"],
                              linewidth=BOUNDARY_LINEWIDTH, label=style["label"]))
    return handles


def _stress_unit(peak_pa):
    for scale, unit in _STRESS_UNITS:
        if peak_pa >= scale:
            return scale, unit
    return _STRESS_UNITS[-1]


def _field_panel(ax, fig, geometry, frame, *, bodies, zoom=None):
    """One von Mises panel in the current configuration. Returns the peak corner."""
    xy = geometry["points"] + frame["u"]
    materials = geometry["materials"]
    values = frame["von_mises"]

    field_mask = np.isin(materials, bodies)
    for body in sorted(set(materials) - set(bodies)):
        _body_polys(ax, xy, materials, body, **MESH_LINE_STYLE, zorder=1)

    shown_xy = xy[field_mask]
    shown = values[field_mask]
    peak_pa = float(shown.max())
    scale, unit = _stress_unit(peak_pa)
    levels = np.linspace(0.0, peak_pa / scale, FIELD_LEVELS + 1)
    filled = ax.tricontourf(_triangulation(shown_xy), shown.ravel() / scale,
                            levels=levels, cmap=FIELD_CMAP, zorder=2)
    ax.add_collection(PolyCollection(_outlines(shown_xy), facecolors="none", zorder=3,
                                     **FIELD_MESH_STYLE))

    peak_xy = shown_xy.reshape(-1, 2)[int(np.argmax(shown.ravel()))]
    ax.scatter(*peak_xy, **PEAK_MARKER_STYLE)

    _bare_axes(ax, xy, pad=0.004)
    if zoom is not None:
        half_w, half_h = zoom
        ax.set_xlim(peak_xy[0] - half_w, peak_xy[0] + half_w)
        ax.set_ylim(peak_xy[1] - half_h, peak_xy[1] + half_h)

    bar = fig.colorbar(filled, ax=ax, shrink=0.72, pad=0.03, aspect=22)
    bar.set_label(rf"$\sigma_\mathrm{{vM}}$ in \si{{{unit}}}")
    bar.locator = MaxNLocator(nbins=5)
    bar.update_ticks()
    bar.outline.set_linewidth(0.6)
    return peak_xy


def draw_mesh(geometry):
    """Reference mesh, both bodies, and the four named boundaries."""
    xy = geometry["points"]
    materials = geometry["materials"]

    fig, ax = plt.subplots(figsize=(HALF_WIDTH, 1.45 * HALF_WIDTH))
    handles = []
    for body in ("pendulum", "wall"):
        _body_polys(ax, xy, materials, body, **MESH_LINE_STYLE, zorder=1)
        handles.append(Patch(facecolor=BODY_FILLS[body], edgecolor=MESH_LINE_STYLE["edgecolor"],
                             linewidth=0.6, label=BODY_LABELS[body]))
    handles += _boundaries(ax, xy, geometry["segments"])
    _bare_axes(ax, xy, pad=0.006)
    legend_above(ax, handles=handles, ncol=2, columnspacing=1.0, handlelength=1.8)
    fig.tight_layout()
    return fig


def draw_stress(geometry, frames, zoom):
    """(a) peak of the first impact, zoomed. (b) outgoing state of the handover.

    Panel widths follow each panel's own aspect, so both drawings reach the
    same height and neither leaves a margin the other has to absorb.
    """
    x0, x1, y0, y1 = _extent(geometry["points"] + frames["handover"]["u"], pad=0.004)
    aspect_a = zoom[0] / zoom[1]
    aspect_b = (x1 - x0) / (y1 - y0)
    fig, axes = plt.subplots(1, 2, figsize=(FULL_WIDTH, 0.56 * FULL_WIDTH),
                             layout="constrained",
                             gridspec_kw={"width_ratios": [aspect_a, aspect_b]})
    _field_panel(axes[0], fig, geometry, frames["impact"],
                 bodies=("pendulum", "wall"), zoom=zoom)
    _field_panel(axes[1], fig, geometry, frames["handover"], bodies=("pendulum",))
    panel_labels(axes, y=0.99)
    return fig
