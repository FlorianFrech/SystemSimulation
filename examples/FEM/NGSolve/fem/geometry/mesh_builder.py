from ..config.config import MeshParameters
from netgen.occ import OCCGeometry
from ngsolve import Mesh

class PendulumMesh:
    def __init__(self, geo, params: MeshParameters):
        self.geo = geo
        self.mesh_params = params
        self._build()

    def _build(self):
        mp = self.mesh_params
        self._mesh = Mesh(OCCGeometry(self.geo, dim=2).GenerateMesh(maxh=mp.max_element_size))
        if mp.curved_elements:
            self._mesh.Curve(mp.mesh_order)
        
        for _ in range(mp.refinement_levels):
            self._mesh.Refine()