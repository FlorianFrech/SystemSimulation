# Chapter 2 Guideline: Theoretical Background

## Purpose

Chapter 2 provides the minimum theoretical background needed to understand the architecture, implementation, and case study of the thesis.
It should define the modeling and co-simulation concepts that are later implemented in `syssimx`.
It is not a second state-of-the-art chapter and it is not an implementation chapter.

The chapter should answer three questions:

- What mathematical concepts are needed to describe continuous, hybrid, and coupled simulation models?
- Which co-simulation concepts are required for execution ordering, algebraic-loop handling, and event interaction?
- Which modeling approaches are used later in the case study, and what is their theoretical role?

## Required Context Before Writing

Read these documents before drafting or polishing Chapter 2:

- `thesis/guideline/README.md`
- `thesis/guideline/thesis_concept.md`
- `thesis/guideline/writing_style.md`
- `thesis/guideline/glossary.md`
- `thesis/guideline/notation.md`
- `thesis/guideline/golden_rules_writing_summary.md`

Chapter 2 must follow the glossary strictly.
Use `subsystem` for the modeled part of the physical system.
Use `simulation unit` for a tool-neutral executable simulation participant.
Use `component` only when referring to the concrete `syssimx` abstraction in later chapters.

## Chapter Role

Chapter 2 should contain theory, definitions, and conceptual relations.
It should not contain code-level names, implementation routines, test results, or case-study parameter values.

Use Chapter 2 for:

- continuous-time state-space concepts
- ordinary and differential-algebraic equations
- hybrid systems, events, modes, guards, resets, and dense time
- co-simulation, communication points, macro steps, master algorithms, feedthrough, structural dependencies, and algebraic loops
- modeling approaches used in the thesis: equation-based modeling, musculoskeletal or multibody simulation, finite element modeling, and model fidelity

Do not use Chapter 2 for:

- `syssimx` class names, method names, port implementation details, or graph metadata fields
- implementation-specific algorithms such as exact bisection code paths, active-output filtering, cached maps, or event-deduplication caches
- case-study parameter values such as contact stiffness, PID gains, macro-step sizes, solver tolerances, or benchmark timings
- detailed tool-wrapper behavior for FMUs, OpenSim, NGSolve, or the `MasterPendulum`
- validation results or claims about performance

## Recommended Section Structure

The current chapter structure is appropriate and should be preserved unless the thesis structure changes globally.

### 2.0 Notation and Conventions

Function:
Define global notation used throughout the thesis.

Content:

- time variables, macro-step notation, communication points
- state, input, output, event, and mode symbols
- dense-time notation if used in later chapters
- basic graph notation if needed for structural analysis

Rules:

- Only include symbols used repeatedly in later chapters.
- Do not overload symbols with different meanings in different sections.
- Keep local symbols in the section where they are introduced.
- Align all symbols with `thesis/guideline/notation.md`.

### 2.1 Continuous-Time Modeling

Function:
Provide the mathematical basis for continuous subsystem behavior.

Content:

- state-space representation
- inputs, outputs, parameters, and time-dependent trajectories
- \ac{ODE} and \ac{DAE} concepts
- numerical integration as an approximation of continuous dynamics
- direct feedthrough as an input-output dependency at the same time instant

Rules:

- Keep the level conceptual.
- Do not explain solver internals unless the concept is needed later.
- Do not discuss concrete solver choices such as CVODE, DASSL, or Euler here.
- Use this section to prepare the reader for component dynamics, not for implementation details.

### 2.2 Hybrid System Modeling

Function:
Introduce discontinuities, mode changes, and event-based behavior.

Content:

- continuous evolution interrupted by discrete events
- event indicators, zero crossings, guards, and resets
- modes and mode-dependent dynamics
- dense or superdense time when multiple events occur at the same physical time
- rollback and event localization as conceptual requirements for hybrid co-simulation

Rules:

- Explain why ordinary continuous-time integration is insufficient for hybrid behavior.
- Define terminology that is later used by the hybrid algorithm.
- Do not describe `syssimx` event caches, dispatch groups, or exact localization implementation.

### 2.3 Co-Simulation Principles

Function:
Explain how multiple simulation units are coupled and orchestrated.

Content:

- simulation units and communication points
- macro steps and input approximation between communication points
- master algorithms and execution order
- Jacobi and Gauss-Seidel coupling at a conceptual level
- direct feedthrough and instantaneous dependencies
- structural dependency graphs and strongly connected components
- algebraic loops and coupled initialization
- conceptual role of FMI and FMUs in co-simulation

Rules:

- Use `simulation unit` for tool-neutral participants.
- Use `master algorithm`, not `orchestrator`, unless referring to the general orchestration role.
- Keep graph theory at the level needed for Chapter 5 structural analysis.
- Do not include implementation-specific graph fields such as `_dag`, `_input_sources`, or `execution_idx`.
- Do not describe the exact IJCSA implementation. State the principle of solving coupled input-output dependencies.

### 2.4 Modeling Approaches Used in This Thesis

Function:
Provide the theoretical background for the model classes later used in the controlled pendulum case study.

Content:

- equation-based modeling and Modelica-style declarative models
- \ac{FMI} and \acp{FMU} as packaging and tool-interoperability concepts
- musculoskeletal or multibody modeling as rigid-body dynamics with joints and constraints
- finite element modeling as a continuum-based discretization approach
- model fidelity and reduced representations

Rules:

- Keep the section about modeling approaches, not tool integration.
- Use the pendulum only as a running example if it clarifies the concept.
- Do not reproduce the full implementation of the FMU, OpenSim, or FEM pendulum.
- Defer concrete pendulum equations, contact parameters, solver settings, and switching thresholds to Chapter 6.
- If Newmark updates are included, present them only as the time-discretization concept used for dynamic FEM analysis. Do not turn this into a full solver chapter.
- Keep simulation-unit interface discussion short. Chapter 2 may state which quantities a modeling approach typically exposes, but the concrete port contract, wrapper lifecycle, state snapshot representation, feedthrough declaration, and backend adaptation belong in Chapter 5.
- For finite element models, separate the general concept from the case-study realization. Chapter 2 explains continuum fields, weak form, discretization, and time integration. Chapter 6 explains the controlled-pendulum geometry, mesh, hinge constraint, torque boundary, penalty contact law, output projection, and stress or displacement visualizations.
- For OpenSim, keep only the conceptual consequence: OpenSim models expose selected controls, generalized coordinates, speeds, and realized quantities, but no FMI-style descriptor. The wrapper mapping belongs in Chapter 5. The concrete pendulum interface belongs in Chapter 6.
- Use `\paragraph{}` headings inside Section 2.4 only when they make a long conceptual subsection easier to scan. Do not introduce paragraph headings only to make all modeling approaches look symmetric. Section 2.4.1 may remain prose-only if the Modelica listing already structures the explanation.

## Theory-to-Chapter Boundary

Use this table to decide where content belongs.

| Content type | Belongs in |
| --- | --- |
| Mathematical definition, notation, conceptual dependency | Chapter 2 |
| User requirements and system requirements | Chapter 3 |
| Framework abstractions and design rationale | Chapter 4 |
| Class behavior, method order, data structures, implementation algorithms | Chapter 5 |
| Concrete case-study models, parameters, solver settings, and reference setup | Chapter 6 |
| Interpretation, limitations, contribution, and future work | Chapter 7 |

Examples:

| Topic | Chapter 2 version | Later chapter version |
| --- | --- | --- |
| Direct feedthrough | Same-time input-output dependency | Port perturbation or FMI model-structure extraction in Chapter 5 |
| Algebraic loop | Cycle of instantaneous dependencies | Stored loop metadata and IJCSA implementation in Chapter 5 |
| Event handling | Indicators, guards, resets, dense time | Detection, localization, dispatch, deduplication in Chapter 5 |
| FEM dynamics | Continuum discretization and time integration concept | FEM pendulum geometry, boundary conditions, contact stiffness, and output projection in Chapter 6 |
| Solver choices | General role of numerical integration | CVODE, Euler reset FMU, and FEM Newmark settings in Chapter 6 |
| Simulation-unit contract | Typical exposed quantities and why an interface is needed | Concrete wrapper behavior, ports, lifecycle, feedthrough, snapshots, and backend calls in Chapter 5 |
| FEM visualization | Concept that FEM resolves displacement, strain, stress, and contact fields | Mesh, boundary tags, deformed contact snapshots, and field plots for the case-study pendulum in Chapter 6 |

### Simulation-Unit Contract Boundary

Chapter 2 should not contain a separate contract discussion for every modeling approach if that discussion starts to read like wrapper documentation.
Use at most one short bridge paragraph per approach.
That paragraph may state the typical interface consequence of the modeling approach:

- equation-based models expose variables according to causality and variability declarations,
- FMUs package such variables in a standardized model description,
- musculoskeletal models require a model-specific selection of controls, generalized coordinates, speeds, and realized outputs,
- finite element models expose selected boundary quantities or projected scalar outputs rather than the full field state.

For the OpenSim subsection, the Chapter 2 bridge paragraph should stop at this level:

```latex
A musculoskeletal model does not define a standardized co-simulation descriptor comparable to an \ac{FMI} model description.
The exchanged quantities must therefore be selected for the concrete model.
Typical inputs are actuator controls, prescribed generalized forces, or external loads.
Typical outputs are generalized coordinates, speeds, accelerations, body kinematics, contact quantities, or muscle-related quantities.
```

The following OpenSim content belongs outside Chapter 2:

- Chapter 5: how `OpenSimComponent` maps selected quantities to ports, initializes the OpenSim `Model`, `State`, and `Manager`, stages realization, reads outputs, and declares or handles direct feedthrough.
- Chapter 6: the concrete pendulum torque input, \(\theta\), \(\omega\), \(\alpha\), synchronized mass, center-of-mass length, pivot inertia, absence of muscle dynamics, and role as intermediate-fidelity model.

Move the following content to Chapter 5:

- how a wrapper creates ports,
- how it initializes the backend,
- how it reads and writes values,
- how it detects or declares direct feedthrough,
- how rollback snapshots are represented,
- how the backend state is restored.

Move the following content to Chapter 6:

- the concrete pendulum inputs and outputs,
- parameter synchronization between model variants,
- FEM boundary names and geometry,
- FEM contact parameters and internal time stepping,
- qualitative mesh, displacement, stress, or contact visualizations.

## Solver Detail Boundary

Solver theory must stay proportional to the thesis contribution.
The thesis contributes a co-simulation framework, not a new numerical integration method.

Allowed in Chapter 2:

- explaining that continuous dynamics require numerical integration
- distinguishing \acp{ODE}, \acp{DAE}, and \acp{PDE}
- presenting a short Newmark update if required to understand dynamic FEM modeling
- stating that implicit and explicit schemes differ in stability and cost at a high level

Not appropriate for Chapter 2:

- detailed derivations of CVODE, DASSL, Euler, or Newton solver internals
- solver-specific tolerances or configuration parameters
- performance claims about solver choices
- tool-specific solver behavior of exported FMUs

Concrete solver choices belong in Chapter 6.
For this thesis, Chapter 6 should state that most FMUs use CVODE by default, while the PID reset FMU uses Euler because the reset input must be applied reliably during event handling.

## Figures and Tables

Use figures and tables only when they reduce explanation effort.

Appropriate figures:

- conceptual continuous-time model with inputs, states, and outputs
- hybrid trajectory with event indicator and reset
- co-simulation communication grid
- dependency graph and algebraic-loop concept
- comparison of modeling approaches at a conceptual level

Avoid:

- implementation sequence diagrams
- class diagrams
- code-level data-flow diagrams
- case-study result plots
- tool screenshots

Caption rule:
Every figure caption must state what concept the figure supports.
Do not use captions as a second full explanation of the section.

### Structural-Analysis Figure (Section 2.3.3)

Role:
Show the conceptual three-step pipeline from a coupled scenario to a generation-based execution order.
The figure must remain solution-neutral and must not depend on `syssimx` field names, port boxes, or implementation-style coloring.

Required panels:

- Panel (a) **Dependency graph.** Four labelled nodes (A, B, C, D) with directed arrows. Mark nodes with direct feedthrough on the node itself (distinct color or double border, not red) **and** classify edges as instantaneous (solid) or delayed (dashed). The node encoding shows the cause (feedthrough property of the receiving unit); the edge encoding shows the effect (instantaneous versus delayed dependency). Include a three-entry legend.
- Panel (b) **Zero-delay graph.** Only the instantaneous edges are retained. The SCC formed by B and C is highlighted as an algebraic loop block.
- Panel (c) **Condensed graph.** The algebraic loop is collapsed to a single block. Topological generations are labelled (Gen 0, Gen 1, Gen 2).

What the figure must not show:

- port-level boxes or per-port direct-feedthrough arrows (these belong to the implementation level)
- `\texttt{graph}`, `\texttt{\_dag}`, `\texttt{execution\_order}` or any other metadata field name
- delayed-producer relocation (this is a `syssimx` scheduling choice and belongs in Chapter 5)
- ghosted edges or filter annotations

Caption must state that the figure illustrates the conceptual pipeline, and must not enumerate panels as a method list.
The same scenario (A, B, C, D) is reused in the implementation chapter for the worked example. Chapter 2 is therefore the visual anchor; the implementation figure refines it.

## Equation Rules

Equations should be included only if they are reused later.

Rules:

- Define every symbol close to its first use.
- Use notation consistently with `notation.md`.
- Label equations only if they are referenced later.
- Avoid derivations that do not support later implementation or case-study interpretation.
- Keep the derivation depth below what would be expected in a numerical-methods thesis.

## Acronyms and Terminology

Use acronym macros for terms listed in `thesis/other/acronyms.tex`.

Likely Chapter 2 acronyms:

- `\ac{ODE}`
- `\ac{DAE}`
- `\ac{PDE}`
- `\ac{FMI}`
- `\ac{FMU}` and `\acp{FMU}`
- `\ac{FEM}`
- `\ac{SCC}`
- `\ac{IJCSA}` if the term is introduced conceptually

Introduce \ac{FMI} before \ac{FMU}.
The first explanation should make clear that an \ac{FMU} is the packaged simulation unit defined by the \ac{FMI} standard.

## Writing Style

Chapter 2 should be precise and compact.
Use direct statements and avoid defensive phrasing.

Preferred:

- "A co-simulation master algorithm advances several simulation units through communication points."
- "Direct feedthrough creates an instantaneous dependency from an input to an output."
- "A strongly connected component of the dependency graph represents an algebraic loop."

Avoid:

- "This is not an implementation detail, but rather a theoretical concept."
- "It can be observed that the model can be described as..."
- "The methodology facilitates a robust coupling of heterogeneous models."
- "The framework is not intended to replace tools. Instead, it..."

Do not introduce `syssimx` as the subject of Chapter 2.
If a forward reference is necessary, keep it short:

- "Chapter 5 implements this dependency analysis for the `syssimx` system graph."

## Cross-References

Use forward references sparingly.
The main references should point from later chapters back to Chapter 2, not the other way around.

Good forward references:

- "The implementation of this concept is described in Section~..."
- "The controlled pendulum case study uses this modeling distinction in Chapter~..."

Avoid:

- repeating implementation details before they are introduced
- previewing every later result
- turning Chapter 2 into a roadmap for the whole thesis

## Revision Checklist

Before considering Chapter 2 polished, check:

- Each section has a clear theoretical role.
- No implementation method names appear unless used only as a later reference.
- `simulation unit`, `component`, `system`, and `System` are used according to the glossary.
- FMI is introduced before FMU.
- Concrete solver settings are deferred to Chapter 6.
- FEM details are limited to concepts; pendulum-specific boundary conditions stay in Chapter 6 unless needed as a short example.
- Equations are necessary, defined, and reused later.
- Figures are conceptual and not implementation-level.
- The chapter does not duplicate the state-of-the-art review from Chapter 1.
- The chapter does not pre-empt the architecture in Chapter 4 or implementation in Chapter 5.
