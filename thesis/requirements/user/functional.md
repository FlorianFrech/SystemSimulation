# Functional User Requirements

The functional user requirements describe the capabilities that a user expects from the overall heterogeneous hybrid system simulation workflow. They are formulated in a tool-agnostic way and focus on user needs rather than on concrete implementation details. For clarity, the requirements are grouped into four categories: modeling, heterogeneity, simulation, and interaction.

## Modeling

The modeling requirements describe how users shall be able to represent subsystems and assemble them into complete system models. The focus lies on modularity, explicit physical interfaces, and support for the main classes of models that are relevant for this thesis.

| ID | Requirement | Priority | Rationale |
|----|-------------|----------|-----------|
| UR_01 | The overall workflow shall support component-based modeling of subsystems from different physical domains. | Shall | Complex mechatronic and cyber-physical systems are built from interacting subsystems from mechanics, electronics, control, and related domains. |
| UR_02 | The overall workflow shall support explicit units for physical quantities at model interfaces and parameters. | Shall | Unit information improves clarity, enables consistency checks, and reduces modeling errors at subsystem interfaces. |
| UR_03 | The overall workflow shall support hierarchical composition of atomic components and virtual subsystems. | Shall | Hierarchical composition reflects system structure, improves reuse, and keeps large models manageable. |
| UR_04 | The overall workflow shall support equation-based modeling of subsystem behavior. | Shall | Equation-based modeling is required to represent multi-domain physical subsystems in a compact and physically meaningful form. |
| UR_05 | The overall workflow shall support musculoskeletal modeling of biomechanical subsystems. | Shall | The target application domain includes biomechanical systems whose dynamics cannot be represented adequately by general-purpose lumped models alone. |
| UR_06 | The overall workflow shall support continuum-mechanical modeling with spatial discretization for deformable subsystems. | Shall | Some subsystems require distributed models to capture deformation, stress, contact, and boundary effects. |
| UR_07 | The overall workflow shall support subsystem models with continuous-time, discrete-time, and hybrid behavior. | Shall | Realistic mechatronic systems combine physical dynamics with sampled controllers, switching logic, and event-driven behavior. |
| UR_08 | The overall workflow shall support reuse and parameterization of components and subsystems across different system configurations. | Shall | Reuse reduces modeling effort and enables structured comparison of alternative model variants and parameter sets. |

## Heterogeneity

The heterogeneity requirements describe the need to combine subsystem models that originate from different modeling paradigms and execution environments. These requirements define the interoperability scope of the workflow.

| ID | Requirement | Priority | Rationale |
|----|-------------|----------|-----------|
| UR_09 | The overall workflow shall support the integration of subsystem models developed in different modeling environments. | Shall | Heterogeneous systems are commonly modeled with domain-specific tools, which makes interoperability a core requirement. |
| UR_10 | The overall workflow shall support the combined use of equation-based, musculoskeletal, and continuum-mechanical subsystem models within one simulation setup. | Shall | The target systems require several specialized model classes that must interact consistently within one coupled workflow. |

## Simulation

The simulation requirements describe the capabilities that users need in order to execute the coupled system model. They cover hybrid system behavior, master-level coordination, and the configuration of simulation settings that affect the overall workflow.

| ID | Requirement | Priority | Rationale |
|----|-------------|----------|-----------|
| UR_11 | The overall workflow shall enable the numerical simulation of heterogeneous hybrid systems with continuous and discrete behavior. | Shall | Accurate system analysis requires a workflow that can handle both continuous evolution and event-driven changes across coupled subsystems. |
| UR_12 | The overall workflow shall allow users to select the co-simulation master algorithm, configure the macro step size, and provide tool-specific simulation settings where required. | Shall | Different coupled systems require different coordination schemes and simulation settings to balance robustness, accuracy, and runtime. |

## Interaction

The interaction requirements describe how users shall inspect the model structure, monitor simulations, and work with the resulting data. They focus on features that improve transparency, comparison, and practical usability of the workflow.

| ID | Requirement | Priority | Rationale |
|----|-------------|----------|-----------|
| UR_13 | The overall workflow should provide a visual representation of the system model and its hierarchical structure. | Should | Visual inspection helps users understand dependencies, interfaces, and subsystem composition. |
| UR_14 | The overall workflow should allow users to observe simulation progress through textual and graphical feedback. | Should | Runtime feedback supports debugging, monitoring, and early detection of numerical or modeling problems. |
| UR_15 | The overall workflow should allow users to compare simulation results across model variants and configurations. | Should | Comparative analysis is required to assess modeling choices, parameter settings, and system behavior under different assumptions. |
| UR_16 | The overall workflow should support result export and post-processing for further analysis and documentation. | Should | Simulation results are often processed further for reporting, validation, and external evaluation workflows. |
