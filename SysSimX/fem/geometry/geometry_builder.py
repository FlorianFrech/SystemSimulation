from ..config.config import GeometryParameters
from netgen.occ import MoveTo, Rectangle, Circle, Compound, Axis, X, Y, OCCGeometry

class PendulumGeometry:
    def __init__(self, params: GeometryParameters): 
        self.geom_params = params
        self._build()

    def _build(self):
        gp = self.geom_params

        bar = MoveTo(-gp.r_rod,0).Rectangle(2*gp.r_rod, gp.l_center).Face()
        bar.edges.Min(Y).name="rotation"
        bar.faces.name="bar"
        bar.faces.maxh=gp.r_rod/2

        hole = Circle((0, gp.l_center), gp.r_hole).Face()
        hole.faces.name="hole"
        hole.edges.maxh=gp.r_head/20

        circ = Circle((0, gp.l_center), gp.r_head).Face()
        circ.edges.maxh=gp.r_head/20
        circ.faces.name="circ"
        circ.faces.maxh=gp.r_head/5
        circ.edges.name="contact_head"
        
        head = circ - hole
        pendulum = head + bar - hole

        pendulum = pendulum.Rotate(Axis((0.0, 0, 0), (0, 0, 1)), 180)
        pendulum.name = "pendulum"
        geo = pendulum
        
        if gp.use_wall:
            # Wall
            wall_pos_x = -gp.r_head - gp.wall_len_x
            wall_pos_y = -gp.l_center - gp.wall_len_y/2
            wall = MoveTo(wall_pos_x, wall_pos_y).Rectangle(gp.wall_len_x, gp.wall_len_y).Face()
            wall.faces.maxh = gp.r_head/5
            wall.edges.Max(X).name = "contact_wall"
            wall.edges.Max(X).maxh = gp.r_head/20
            wall.edges.Max(Y).name = "fix"
            wall.edges.Min(Y).name = "fix"
            wall.edges.Min(X).name = "fix"
            wall.name = "wall"
            geo = Compound([pendulum, wall])
        
        self._geo = geo