"""Multi-model master pendulum package.

Exports are backend-dependent: each pendulum model needs its simulation
backend installed (ngsolve / fmpy / opensim), and ``MasterPendulum`` needs
all three. Missing backends simply remove the corresponding export instead
of making the whole package unimportable.
"""

from . import components as _components

__all__ = list(_components.__all__)

if "FEMPendulum" in __all__:
    from .components import FEMPendulum
if "FMUPendulum" in __all__:
    from .components import FMUPendulum
if "OpenSimPendulum" in __all__:
    from .components import OpenSimPendulum

# MasterPendulum orchestrates all three models, so it requires every backend.
try:
    from .orchestration.master_pendulum import MasterPendulum

    __all__.append("MasterPendulum")
except ImportError:
    pass
