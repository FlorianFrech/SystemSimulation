# Non-Functional User Requirements

The non-functional user requirements describe quality attributes and constraints of the overall heterogeneous hybrid system simulation workflow. In contrast to the functional user requirements, they do not specify which services the workflow shall provide, but how these services shall behave with respect to usability, robustness, portability, and performance. The requirements listed here are limited to the aspects that are relevant for the design and evaluation of the framework. Project-internal concerns such as licensing, development practices, or citation rules are treated separately and are therefore not included as user requirements.

## Usability and Diagnostics

The workflow shall be usable for engineering experimentation and research-oriented prototyping. Users shall receive sufficient feedback to understand modeling errors, configuration problems, and simulation behavior.

| ID | Requirement | Priority | Rationale |
|----|-------------|----------|-----------|
| NFR_01 | The workflow should provide clear error messages and logs. | Should | Clear diagnostics reduce debugging effort and help users identify configuration and simulation problems quickly. |
| NFR_02 | The workflow should provide documentation and examples that help users build and simulate models. | Should | Documentation and examples reduce the learning effort and support reproducible use of the workflow. |
| NFR_03 | The workflow should provide clear and interpretable visual outputs for system structure and simulation results. | Should | Visual outputs improve transparency and help users inspect model structure and simulation behavior efficiently. |

## Robustness and Correctness

Since heterogeneous co-simulation involves multiple tools, interfaces, and numerical assumptions, the workflow shall detect invalid configurations early and avoid inconsistent simulations whenever possible.

| ID | Requirement | Priority | Rationale |
|----|-------------|----------|-----------|
| NFR_04 | The workflow shall detect faulty configurations and prevent inconsistent simulations. | Shall | Early validation reduces invalid results and avoids wasted simulation effort. |

## Performance and Resource Usage

The workflow is intended for research and prototyping on standard engineering workstations. It shall therefore remain practical for small to medium-sized systems with respect to runtime and memory usage.

| ID | Requirement | Priority | Rationale |
|----|-------------|----------|-----------|
| NFR_05 | The workflow shall provide acceptable simulation performance for small to medium-sized systems. | Shall | Practical runtime is required for iterative modeling, testing, and comparison of configurations. |
| NFR_06 | The workflow shall remain within typical desktop or notebook memory limits for moderate use cases. | Shall | Memory usage must remain practical on standard engineering hardware. |

## Portability

The workflow shall be executable in standard Python-based development environments without requiring specialized hardware or heavily customized platforms.

| ID | Requirement | Priority | Rationale |
|----|-------------|----------|-----------|
| NFR_07 | The workflow shall operate in standard developer environments. | Shall | Portability increases usability and reduces environment-specific barriers to adoption. |
