"""Export a miniature 2D FEM pendulum mesh for the defense presentation.

Rebuilds the case-study pendulum geometry from ``pendulum_mesh.py`` with a
coarser element sizing so the mesh stays legible at slide-icon size, and
writes a tight-bbox vector PDF (plus a PNG preview) to
``thesis/figures/defense/``.

Run from anywhere inside the repo:

    python demos/ControlledPendulum/notebooks/master_pendulum/fem/fem_mesh_mini_slide.py
"""

from collections import defaultdict
from pathlib import Path
import sys

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.tri as mtri
from matplotlib.colors import ListedColormap

from netgen.occ import Axis, Circle, Compound, MoveTo, OCCGeometry, X, Y
from ngsolve import BND, VOL, Mesh

_repo = Path(__file__).resolve()
while _repo != _repo.parent and not (_repo / "pyproject.toml").exists():
    _repo = _repo.parent
if str(_repo) not in sys.path:
    sys.path.insert(0, str(_repo))

from syssimx_examples.controlled_pendulum.components.fem.pendulum_config import (
    GeometryParameters,
)

FIG_DIR = _repo / "thesis" / "figures" / "defense"
FIG_DIR.mkdir(parents=True, exist_ok=True)

# Coarsening factor relative to the case-study mesh (1.0 = case-study sizing).
COARSE = 2.5


def build_mini_mesh(gp: GeometryParameters, coarse: float) -> Mesh:
    """Same geometry and boundary names as ``pendulum_mesh.build_mesh``,
    with all local element sizes scaled by ``coarse``."""
    bar = MoveTo(-gp.r_rod, 0).Rectangle(2 * gp.r_rod, gp.l_center).Face()
    bar.edges.Min(Y).name = "rotation"
    bar.edges.Min(Y).maxh = coarse * gp.r_rod / 10
    bar.faces.name = "bar"
    bar.faces.maxh = coarse * gp.r_rod / 2

    hole = Circle((0, gp.l_center), gp.r_hole).Face()
    hole.faces.name = "hole"
    hole.edges.maxh = coarse * gp.r_head / 20

    circ = Circle((0, gp.l_center), gp.r_head).Face()
    circ.edges.maxh = coarse * gp.r_head / 20
    circ.faces.name = "circ"
    circ.faces.maxh = coarse * gp.r_head / 5
    circ.edges.name = "contact_head"

    head = circ - hole
    pendulum = head + bar - hole

    pendulum = pendulum.Rotate(Axis((0.0, 0, 0), (0, 0, 1)), 180)
    pendulum.name = "pendulum"

    wall_pos_x = -gp.r_head - gp.wall_len_x
    wall_pos_y = -gp.l_center - gp.wall_len_y / 2
    wall = MoveTo(wall_pos_x, wall_pos_y).Rectangle(gp.wall_len_x, gp.wall_len_y).Face()
    wall.faces.maxh = coarse * gp.r_head / 5
    wall.edges.Max(X).name = "contact_wall"
    wall.edges.Max(X).maxh = coarse * gp.r_head / 20
    wall.edges.Max(Y).name = "fix"
    wall.edges.Min(Y).name = "fix"
    wall.edges.Min(X).name = "fix"
    wall.name = "wall"

    geo = OCCGeometry(Compound([pendulum, wall]), dim=2)
    mesh = Mesh(geo.GenerateMesh(maxh=coarse * 0.03))
    mesh.Curve(2)
    return mesh


def extract_mesh(mesh: Mesh):
    points, point_index = [], {}
    triangles, materials = [], []

    def vid(vertex):
        key = tuple(np.round(mesh[vertex].point[:2], 14))
        if key not in point_index:
            point_index[key] = len(points)
            points.append(key)
        return point_index[key]

    for element in mesh.Elements(VOL):
        ids = [vid(v) for v in element.vertices]
        if len(ids) == 3:
            triangles.append(ids)
            materials.append(element.mat)

    boundaries = defaultdict(list)
    for element in mesh.Elements(BND):
        ids = [vid(v) for v in element.vertices]
        if len(ids) == 2:
            boundaries[element.mat].append(tuple(ids))

    return (
        np.asarray(points, dtype=float),
        np.asarray(triangles, dtype=int),
        materials,
        dict(boundaries),
    )


# Colors match the thesis mesh figure (fem_mesh_boundaries).
MATERIAL_COLORS = {"pendulum": "#DCEBF3", "wall": "#EFE3D1"}
BOUNDARY_COLORS = {
    "rotation": "#0072B2",
    "contact_head": "#D55E00",
    "contact_wall": "#CC79A7",
    "fix": "0.20",
}


def plot_mini(coords, triangles, materials, boundaries, gp: GeometryParameters):
    # ~2.9 cm x ~6.8 cm on the slide; scale with \includegraphics as needed.
    fig, ax = plt.subplots(figsize=(1.15, 2.7))
    ax.set_aspect("equal")
    ax.set_axis_off()

    for material, color in MATERIAL_COLORS.items():
        mask = np.array([mat == material for mat in materials])
        ax.tripcolor(
            coords[:, 0], coords[:, 1], triangles[mask],
            facecolors=np.ones(mask.sum()),
            cmap=ListedColormap([color]),
            edgecolors="none", alpha=0.85, zorder=0,
        )

    triangulation = mtri.Triangulation(coords[:, 0], coords[:, 1], triangles)
    ax.triplot(triangulation, color="0.40", linewidth=0.35, alpha=0.9, zorder=1)

    for name, color in BOUNDARY_COLORS.items():
        for segment in boundaries.get(name, []):
            xy = coords[list(segment)]
            ax.plot(
                xy[:, 0], xy[:, 1],
                color=color, linewidth=1.4,
                solid_capstyle="round", zorder=4,
            )

    # # Ground hatching above the pivot, echoing the schematic on the slide.
    # hatch_half_span = 3.0 * gp.r_rod
    # hatch_len = 1.6 * gp.r_rod
    # for x0 in np.linspace(-hatch_half_span, hatch_half_span, 9):
    #     ax.plot(
    #         [x0, x0 + 0.7 * hatch_len], [0.0, hatch_len],
    #         color="0.20", linewidth=0.7, zorder=3,
    #     )
    # ax.plot(
    #     [-hatch_half_span, hatch_half_span], [0.0, 0.0],
    #     color="0.20", linewidth=0.9, zorder=3,
    # )

    # pad = 0.012
    # ax.set_xlim(coords[:, 0].min() - pad, coords[:, 0].max() + pad)
    # ax.set_ylim(coords[:, 1].min() - pad, hatch_len + pad)
    return fig


def main():
    gp = GeometryParameters()
    mesh = build_mini_mesh(gp, COARSE)
    coords, triangles, materials, boundaries = extract_mesh(mesh)
    print(f"mesh: {len(triangles)} triangles, boundaries: {sorted(boundaries)}")

    fig = plot_mini(coords, triangles, materials, boundaries, gp)
    for suffix in ("pdf", "png"):
        out = FIG_DIR / f"fem_pendulum_mesh_mini.{suffix}"
        fig.savefig(out, dpi=600, bbox_inches="tight", pad_inches=0.01, transparent=True)
        print(f"wrote {out.relative_to(_repo)}")


if __name__ == "__main__":
    main()
