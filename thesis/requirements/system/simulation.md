# Derived System Requirements: Simulation

The following system requirements derive from the simulation-related user requirements.
They specify the technical capabilities that the *SysSimX* framework must provide in order to execute coupled heterogeneous system models.
The focus lies on system-level orchestration, hybrid event handling, and pluggable co-simulation algorithms.

| ID | Requirement | Priority |
|----|-------------|----------|
| **UR_10** | **The overall workflow shall support the co-simulation of coupled system models with continuous, discrete, and hybrid behavior, including the detection and handling of discrete events across subsystems.** | **Shall** |
| SR_10_01 | The framework shall provide a system-level macro-step simulation loop for advancing coupled subsystem models in time. | Shall |
| SR_10_02 | The framework shall build a dependency graph from the registered components and their connections. | Shall |
| SR_10_03 | The framework shall determine a valid execution order from the dependency structure of the coupled system. | Shall |
| SR_10_04 | The framework shall support system-level detection, localization, and propagation of discrete events across coupled subsystem models. | Shall |
| **UR_11** | **The overall workflow shall support pluggable co-simulation master algorithms, including iterative treatment of algebraic loops in strongly coupled subsystem configurations.** | **Shall** |
| SR_11_01 | The framework shall provide a pluggable algorithm interface that is independent of the system model. | Shall |
| SR_11_02 | The framework shall detect algebraic loops in the coupled system structure as strongly connected components. | Shall |
| SR_11_03 | The framework shall provide an iterative method for the numerical treatment of algebraic loops. | Shall |
