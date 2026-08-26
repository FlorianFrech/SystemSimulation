"""Pendulum model components for the ControlledPendulum case study.

Each model wraps a different simulation backend with different install
requirements (ngsolve for FEM, fmpy for FMU, opensim for OpenSim). Imports
are guarded per backend — mirroring ``syssimx.components`` — so this package
stays importable with any subset of backends installed and only exports the
models whose backend is available.
"""

__all__ = []

# FEM pendulum (requires ngsolve)
try:
    from .fem.fem_pendulum import FEMPendulum

    __all__.append("FEMPendulum")
except ImportError:
    pass

# FMU pendulum (requires fmpy at simulation time; import itself is guarded
# inside syssimx.components.fmu)
try:
    from .fmu.fmu_pendulum import FMUPendulum

    __all__.append("FMUPendulum")
except ImportError:
    pass

# OpenSim pendulum (requires opensim, conda-only)
try:
    from .opensim.opensim_pendulum import OpenSimPendulum

    __all__.append("OpenSimPendulum")
except ImportError:
    pass
