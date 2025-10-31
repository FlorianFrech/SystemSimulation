# SysSimX: A Framework for System Simulation

This repository contains a framework for simulating dynamic systems using Python. It provides tools for defining system components, configuring simulations, and running experiments.

## Features
- Modular component design
- Configuration management using YAML files
- Support for various numerical integration methods
- Logging and visualization of simulation results
- Integration with external simulation tools (e.g., OpenSim, FMUs)
- Example demos for controlled pendulum systems
- Hybrid simulation capabilities combining different modeling approaches
- Easy-to-use API for setting up and running simulations
- Comprehensive documentation and examples
- Unit tests to ensure reliability and correctness

## Structure

```
SysSimX/
├── __init__.py
├── components/             # Component implementations
│   ├── fmu_comp.py         # FMU co-simulation wrapper
│   ├── fem_comp.py         # FEM component base class
│   └── opensim_comp.py     # OpenSim component wrapper
├── core/                   # Core abstractions and interfaces
│   ├── base.py             # CoSimComponent abstract base class
│   ├── port.py             # PortSpec and PortState definitions
│   └── multi_comp.py       # MultiComponent for hybrid simulations
├── system/                 # System-level orchestration
│   ├── system.py           # System class for component integration
│   ├── connection.py       # Connection dataclass
├── ui/                     # User interface components
├── utilities/              # Helper functions and tools
│   ├── units.py            # Unit handling with Pint
│   ├── update_fmus.py      # FMU generation utilities
│   └── results_opensim.py  # OpenSim result export
└── viz/                    # Visualization tools
    └── sysgraph.py         # System graph visualizer