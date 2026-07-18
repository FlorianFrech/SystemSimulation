"""ControlledPendulum case-study source package.

Re-exports the pendulum models available with the currently installed
backends (see ``master_pendulum`` for the per-backend guarding).
"""

from . import master_pendulum as _master_pendulum

__all__ = list(_master_pendulum.__all__)

if "MasterPendulum" in __all__:
    from .master_pendulum import MasterPendulum
if "FEMPendulum" in __all__:
    from .master_pendulum import FEMPendulum
if "FMUPendulum" in __all__:
    from .master_pendulum import FMUPendulum
if "OpenSimPendulum" in __all__:
    from .master_pendulum import OpenSimPendulum
