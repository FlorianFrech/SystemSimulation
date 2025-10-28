from __future__ import annotations
from abc import abstractmethod
from typing import Dict, Any, Optional, Tuple, List, Union
from dataclasses import dataclass, field
from pathlib import Path
import numpy as np

from ngsolve import *
from ngsolve.webgui import Draw, WebGLScene
from netgen.occ import *
from ngsolve.solvers import NewtonMinimization

import ipywidgets as widgets
from ipywidgets import Layout, HBox, VBox, HTML
from IPython.display import display, Markdown

from ..core.base import CoSimComponent
from ..core.port import PortSpec, PortType

class FEMComponent(CoSimComponent):
    """
    Base class for Finite Element Method (FEM) co-simulation components.
    """
    config: Optional[Any] = None  # Placeholder for FEM configuration dataclass

    def __init__(self, 
                 name: str, 
                 label: Optional[str] = None, 
                 group: Optional[str] = None):
        super().__init__(name, label, group)
        
        self.geometry: Optional[netgen.occ.Geometry] = None
        self.mesh: Optional[Mesh] = None

        self.spaces: Optional[Dict[str, Any]] = {}
        self.gfs: Optional[Dict[str, Any]] = {}
        self.gfs_history: Optional[Dict[str, Any]] = {}

        self.bfa: Optional[BilinearForm] = None
        self.lf: Optional[LinearForm] = None
        self.solver: Optional[Any] = None

        self.scene: Optional[WebGLScene] = None
    
    def initialize(self):
        pass

    def do_step(self, t, dt):
        pass

    def set_state(self, state):
        pass
    
    def get_state(self):
        pass

    def reset(self):
        pass
