from netgen.occ import Axis, Circle, Compound, MoveTo, OCCGeometry, X, Y
from ngsolve import Mesh

from .pendulum_config import (
    GeometryParameters,
    MeshParameters,
)


def build_mesh(
    geo_params: GeometryParameters, mesh_params: MeshParameters, with_contact: bool
) -> Mesh:
    gp = geo_params
    mp = mesh_params

    bar = MoveTo(-gp.r_rod, 0).Rectangle(2 * gp.r_rod, gp.l_center).Face()
    bar.edges.Min(Y).name = "rotation"
    bar.edges.Min(Y).maxh = gp.r_rod / 10
    bar.faces.name = "bar"
    bar.faces.maxh = gp.r_rod / 2

    hole = Circle((0, gp.l_center), gp.r_hole).Face()
    hole.faces.name = "hole"
    hole.edges.maxh = gp.r_head / 20

    circ = Circle((0, gp.l_center), gp.r_head).Face()
    circ.edges.maxh = gp.r_head / 20
    circ.faces.name = "circ"
    circ.faces.maxh = gp.r_head / 5
    circ.edges.name = "contact_head"

    head = circ - hole
    pendulum = head + bar - hole

    pendulum = pendulum.Rotate(Axis((0.0, 0, 0), (0, 0, 1)), 180)
    pendulum.vertices[0].maxh = gp.r_rod / 20
    pendulum.vertices[1].maxh = gp.r_rod / 20
    pendulum.name = "pendulum"
    geo = pendulum

    if with_contact:
        # Wall
        wall_pos_x = -gp.r_head - gp.wall_len_x
        wall_pos_y = -gp.l_center - gp.wall_len_y / 2
        wall = MoveTo(wall_pos_x, wall_pos_y).Rectangle(gp.wall_len_x, gp.wall_len_y).Face()
        wall.faces.maxh = gp.r_head / 5
        wall.edges.Max(X).name = "contact_wall"
        wall.edges.Max(X).maxh = gp.r_head / 20
        wall.edges.Max(Y).name = "fix"
        wall.edges.Min(Y).name = "fix"
        wall.edges.Min(X).name = "fix"
        wall.name = "wall"
        geo = Compound([pendulum, wall])

    geo = OCCGeometry(geo, dim=2)
    mesh = Mesh(geo.GenerateMesh(maxh=mp.max_element_size))

    if mp.curved_elements:
        mesh.Curve(mp.mesh_order)

    for _ in range(mp.refinement_levels):
        mesh.Refine()

    return mesh
