"""Component implementations for different simulation backends."""

__all__ = []

# FMU Component (requires fmpy)
try:
    from .fmu import FMUComponent

    __all__.append("FMUComponent")
except ImportError:
    pass

# FEM Component (requires ngsolve)
try:
    from .fem import FEMComponent

    __all__.append("FEMComponent")
except ImportError:
    pass

# OpenSim Component (requires opensim)
try:
    from .opensim import OpenSimComponent

    __all__.append("OpenSimComponent")
except ImportError:
    pass
