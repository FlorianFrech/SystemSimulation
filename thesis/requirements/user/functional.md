# Functional User Requirements

The functional user requirements describe the capabilities that a user expects from the overall heterogeneous hybrid system simulation workflow. They are formulated in a tool-agnostic way and focus on user needs rather than on concrete implementation details. For clarity, the requirements are grouped into four categories: general system modeling, heterogeneous integration, simulation, and interaction.

## General System Modeling

The general system modeling requirements describe how users shall be able to represent subsystems and assemble them into complete system models. These requirements cover modularity, explicit physical interfaces, system assembly, and support for hybrid dynamic behavior. They are not specific to any particular modeling or simulation backend.

| ID | Requirement | Priority |
|----|-------------|----------|
| UR_01 | The overall workflow shall support component-based modeling, where each subsystem is represented as an independent, reusable, and parameterizable component with explicit input and output interfaces. | Shall |
| UR_02 | The overall workflow shall support explicit physical units for interface variables and component parameters, including automatic unit validation and conversion. | Shall |
| UR_03 | The overall workflow shall support the assembly of complete system models by connecting components. | Shall |
| UR_04 | The overall workflow shall support components with continuous-time, discrete-time, and hybrid behavior. | Shall |

## Heterogeneous Integration

The heterogeneous integration requirements describe the need to integrate subsystem models from different modeling and simulation backends into one coupled workflow. No single existing tool covers all required modeling approaches, which motivates the need for a common integration framework that is independent of any particular backend. This category also includes runtime model switching, which relies on the common component abstraction to transfer state between models from different backends.

| ID | Requirement | Priority |
|----|-------------|----------|
| UR_05 | The overall workflow shall support the integration of equation-based subsystem models into the component-based workflow. | Shall |
| UR_06 | The overall workflow shall support the integration of musculoskeletal subsystem models into the component-based workflow. | Shall |
| UR_07 | The overall workflow shall support the integration of finite element models into the component-based workflow. | Shall |
| UR_08 | The overall workflow shall support the simultaneous use of subsystem models from different modeling and simulation backends within one coupled system model. | Shall |
| UR_09 | The overall workflow shall support runtime switching between alternative model representations of the same subsystem. | Shall |

## Simulation

The simulation requirements describe the capabilities needed to execute the coupled system model as a numerical co-simulation. They cover system-level orchestration, hybrid event handling across subsystem boundaries, and the selection of co-simulation master algorithms for different coupling scenarios.

| ID | Requirement | Priority |
|----|-------------|----------|
| UR_10 | The overall workflow shall support the co-simulation of coupled system models with continuous, discrete, and hybrid behavior, including the detection and handling of discrete events across subsystems. | Shall |
| UR_11 | The overall workflow shall support pluggable co-simulation master algorithms, including iterative treatment of algebraic loops in strongly coupled subsystem configurations.	 | Shall |

## Interaction

The interaction requirements describe how users shall inspect the system structure and access simulation results. They focus on transparency and practical usability of the workflow.

| ID | Requirement | Priority |
|----|-------------|----------|
| UR_12 | The overall workflow should provide a visual representation of the system model and its dependency structure. | Should |
| UR_13 | The overall workflow should support the export of simulation histories for further analysis and documentation. | Should |
