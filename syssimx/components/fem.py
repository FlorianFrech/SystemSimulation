from __future__ import annotations

from abc import abstractmethod
from pathlib import Path
from typing import Any

from ..core.base import CoSimComponent


class FEMComponent(CoSimComponent):
    """
    Minimal abstract base for FEM co-simulation components.

    - No direct dependency on a specific FEM library (ngsolve/netgen, etc.).
    - Subclasses implement backend specifics (mesh, FE spaces, solvers, visualization).
    """

    def __init__(self, name: str, label: str | None = None, group: str | None = None):
        super().__init__(name, label, group)
        # Geometry and Mesh
        self.geometry: Any | None = None
        self.mesh: Any | None = None

        # Spaces and Grid functions
        self.spaces: dict[str, Any] | None = {}
        self.gfs: dict[str, Any] | None = {}
        self.gfs_history: dict[str, Any] | None = {}

        # Bilinear and Linear Form
        self.bfa: Any | None = None
        self.lf: Any | None = None

        # Solver
        self.solver: Any | None = None

        # Visualization
        self.scene: Any | None = None

    # ---- Abstract hooks for FEM-specific setup ----
    @abstractmethod
    def _initialize_component(self, t0: float) -> None:
        """Setup mesh, FE spaces, solver, material laws, initial conditions."""
        ...

    @abstractmethod
    def _do_step_internal(self, t: float, dt: float) -> None:
        """Advance FEM solver from t to t+dt."""
        ...

    # ---- Optional file I/O hooks (raise NotImplementedError by default) ----
    def load_mesh_from_file(self, path: Path) -> None:
        """Optional: load mesh from file (GMSH, VTK, XDMF, etc.)."""
        raise NotImplementedError(f"{self.name}: load_mesh_from_file not implemented")

    def export_results(self, path: Path, format: str = "vtk") -> None:
        """Optional: export time series to file."""
        raise NotImplementedError(f"{self.name}: export_results not implemented")

    def visualize_state(self) -> None:
        """Optional: library-specific visualization (NGSolve Draw, matplotlib, etc.)."""
        raise NotImplementedError(f"{self.name}: visualize_state not implemented")
