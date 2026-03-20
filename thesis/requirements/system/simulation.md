# Derived System Requirements: Simulation

The following system requirements derive from the simulation-related user requirements.
They specify the technical capabilities that the *SysSimX* framework must provide in order to execute coupled heterogeneous system models.
The focus lies on system-level orchestration, master-algorithm selection, structural analysis, and support for hybrid events.

| U-ID | SR-ID | System Requirement | Rationale | Priority |
|------|-------|--------------------|-----------|----------|
| UR_11 | SR_11_01 | The framework shall provide a system-level macro-step simulation loop for advancing coupled heterogeneous subsystem models in time. | Coupled subsystem models must be coordinated through one common simulation process. | Shall |
| UR_11 | SR_11_02 | The framework shall build a dependency graph from the registered components and their connections. | Graph-based structural information is required for consistent co-simulation orchestration. | Shall |
| UR_11 | SR_11_03 | The framework shall determine a valid execution order from the dependency structure of the coupled system. | Execution ordering is required to respect data dependencies between subsystems. | Shall |
| UR_11 | SR_11_04 | The framework shall detect algebraic loops in the coupled system structure and provide an iterative method for their numerical treatment. | Strongly coupled interface dependencies require special numerical handling. | Shall |
| UR_11 | SR_11_05 | The framework shall support hybrid components that expose event indicators, event-triggered state changes, and event propagation. | Hybrid co-simulation requires explicit support for events at subsystem and system level. | Shall |
| UR_11 | SR_11_06 | The framework shall support event localization and rollback for hybrid co-simulation when required by the participating components. | Accurate handling of state events requires restoring component states and resolving event times. | Shall |
| UR_12 | SR_12_01 | The framework shall allow users to select the system-level co-simulation master algorithm. | Different coupled systems require different orchestration schemes. | Shall |
| UR_12 | SR_12_02 | The framework shall allow users to configure the macro step size used for system-level coordination. | Macro-step size directly affects numerical behavior and runtime of the co-simulation. | Shall |
| UR_12 | SR_12_03 | The framework shall forward tool-specific simulation settings to the corresponding subsystem wrappers before or during initialization. | External subsystem models may require backend-specific settings in addition to the system-level configuration. | Shall |
| UR_12 | SR_12_04 | The framework shall automatically activate hybrid event handling when event-capable components are present in the system. | Hybrid-specific execution support should be enabled whenever the coupled system requires it. | Shall |
