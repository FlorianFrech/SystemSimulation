"""syssimx - A Python framework for heterogeneous system co-simulation.

syssimx provides a unified interface for coupling heterogeneous simulation
models including:

- **FMU Components**: Functional Mock-up Units (FMI 2.0 Co-Simulation)
- **FEM Components**: Finite Element Method solvers (NGSolve)
- **OpenSim Components**: Musculoskeletal biomechanics models

Key Features:
    - Graph-based execution engine with automatic dependency analysis
    - Algebraic loop detection and iterative solving (IJCSA algorithm)
    - Hybrid co-simulation with event detection and superdense time
    - Multiple master algorithms: Jacobi, Gauss-Seidel, Hybrid

Example:
    >>> from syssimx import System, Connection
    >>> from syssimx.components import FMUComponent
    >>>
    >>> # Create system and add components
    >>> system = System(name="MySystem")
    >>> pendulum = FMUComponent("Pendulum", fmu_path="Pendulum.fmu")
    >>> system.add_component(pendulum)
    >>>
    >>> # Initialize and run
    >>> system.initialize(t0=0.0)
    >>> system.run(t0=0.0, tf=10.0, dt=0.01)

See Also:
    - Documentation: https://syssimx.readthedocs.io
    - Repository: https://github.com/FlorianFrech/SystemSimulation
"""

from syssimx.__version__ import __version__
from syssimx.core.base import CoSimComponent
from syssimx.system import Connection, System

__all__ = [
    "CoSimComponent",
    "System",
    "Connection",
    "__version__",
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
