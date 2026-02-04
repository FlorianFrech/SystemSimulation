# SysSimX: A Framework for System Simulation

This repository contains a framework for simulating dynamic systems using Python. It provides tools for defining system components, configuring simulations, and running experiments.

## Main Functionality

1. A graph-based execution engine that exploits FMI 2.0 model structure to derive execution orders, detect algebraic loops, and build SCC-based generations fo
parallel co-simulation.

2. Adaptations of Jacobi, Gauss-Seidel and interface-Jacobian co-simulation under FMI 2.0 co-simulation constraints (no rollback, step-mode APIs).

3. A multi-representation master model concept (FEM, OpenSim, equation-based) with parameter and state synchronization to validate heterogeneous integration.

4. A Python framework (SysSimX) with reusable component abstractions for FMUs, OpenSim models, and FEM models.


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

## Licensing

- **Code and notebooks (primary):** MPL-2.0 (`LICENSE`)
- **Documentation and media:** CC BY 4.0 (`LICENSES/CC-BY-4.0.txt`)
- **Third-party files:** See `THIRD_PARTY_LICENSES.MD` (notably `examples/opensim/*` contains Apache-2.0
  material with license headers)
