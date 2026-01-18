"""SysSimX - A Python framework for heterogeneous system co-simulation."""

from syssimx.core.base import CoSimComponent
from syssimx.system import Connection, System

__all__ = [
    "CoSimComponent",
    "System",
    "Connection",
]

# Optional imports - only available if dependencies are installed
try:
    from syssimx.components import FMUComponent
    __all__.append("FMUComponent")
except ImportError:
    FMUComponent = None  # fmpy not installed

try:
    from syssimx.components import FEMComponent
    __all__.append("FEMComponent")
except ImportError:
    FEMComponent = None  # ngsolve not installed

try:
    from syssimx.components import OpenSimComponent
    __all__.append("OpenSimComponent")
except ImportError:
    OpenSimComponent = None  # opensim not installed

__version__ = "0.1.0"
