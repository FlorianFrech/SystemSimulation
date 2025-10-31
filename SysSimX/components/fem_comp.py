from __future__ import annotations
from abc import abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path

from ..core.base import CoSimComponent
from ..core.port import PortSpec, PortType

class FEMComponent(CoSimComponent):
    """
    Minimal abstract base for FEM co-simulation components.

    - No direct dependency on a specific FEM library (ngsolve/netgen, etc.).
    - Subclasses implement backend specifics (mesh, FE spaces, solvers, visualization).
    """

    def __init__(self, name: str, label: Optional[str] = None, group: Optional[str] = None):
        super().__init__(name, label, group)    
        # Geometry and Mesh
        self.geometry: Optional[Any] = None
        self.mesh: Optional[Any] = None

        # Spaces and Grid functions
        self.spaces: Optional[Dict[str, Any]] = {}
        self.gfs: Optional[Dict[str, Any]] = {}
        self.gfs_history: Optional[Dict[str, Any]] = {}

        # Bilinear and Linear Form
        self.bfa: Optional[Any] = None
        self.lf: Optional[Any] = None

        # Solver
        self.solver: Optional[Any] = None

        # Visualization
        self.scene: Optional[Any] = None

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