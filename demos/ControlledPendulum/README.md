# Controlled Pendulum Demo

This demo showcases the simulation of a controlled pendulum system using various modeling approaches, including Finite Element Method (FEM), OpenSim, and Functional Mock-up Units (FMU). The goal is to demonstrate how different components can be integrated into a single simulation framework to analyze the dynamics of a pendulum under control inputs.

## Directory Structure
```
demos/ControlledPendulum/
├── notebooks/
│   └── master_pendulum/
│       ├── test_master_pendulum_combined.ipynb
├── src/
│   └── master_pendulum/
│       └── orchestration/
│           └── master_pendulum.py
```

## Notebooks 
- `test_master_pendulum_combined.ipynb`: This notebook contains tests for the combined master pendulum system, integrating different modeling approaches and verifying their interactions.

## Source Code
- `master_pendulum.py`: This script orchestrates the master pendulum system, integrating components such as FEM pendulum, OpenSim pendulum, and FMU pendulum into a cohesive simulation framework.