# Writing Guideline – Modeling Approaches Section (Chapter 2.4)

## Purpose

This section introduces the modeling paradigms whose subsystem models
are integrated in the case study. It does not teach tools, derive
numerical methods, or justify tool selection (that is Chapter 3).

### What the reader should understand after this section

- What type of equations each paradigm produces.
- What state, input, and output vectors look like at the interface
  level.
- Why the equation structures differ enough to require separate
  solvers.
- Why no single paradigm covers all aspects of the target system.

### What this section must not do

- Repeat the motivation from Chapter 1 (why heterogeneous simulation
  is needed).
- Repeat the tool selection from Chapter 3 (why Modelica / OpenSim /
  NGSolve were chosen).
- Derive numerical methods (weak forms, shape functions, index
  reduction, time integration schemes).
- Describe API-level or code-level implementation details (belongs to
  Chapter 5).
- Describe specific solver or integrator choices (see below).
- Describe specific material laws, contact formulations, or model
  configurations (belongs to Chapter 6).

---

## Solver and model-specific detail: where it belongs

The framework enforces a clean separation:

- The **model** (inside the simulation unit) owns the solver, the
  material law, the contact formulation, and all internal numerics.
- The **wrapper** (the component) owns the `set`/`get`/`step`
  mapping to the backend API.
- The **framework** (the system) owns the orchestration.

The thesis chapter structure must mirror this separation:

| Content                                      | Chapter   | Reason                                |
|----------------------------------------------|-----------|---------------------------------------|
| Paradigm characterization (equation type,    | **Ch. 2** | Minimum theory for understanding      |
| abstraction level, typical interface)        |           | the framework and the case study      |
| Wrapper realization (`set`/`get`/`step`      | **Ch. 5** | Framework implementation              |
| mapping to backend API)                      |           |                                       |
| Specific solver choices (CVODE, Newmark,     | **Ch. 6** | Model-specific decisions affecting    |
| Simbody integrator)                          |           | the case study results                |
| Specific material laws, contact formulations,| **Ch. 6** | Model-specific choices for the        |
| torque application methods                   |           | pendulum case study                   |

Chapter 2 should state that each paradigm requires its own solver
(this is the whole point of co-simulation). It should NOT name
specific solvers (Newmark, CVODE, etc.).

Chapter 5 should explain how the wrapper communicates with the
backend. It should NOT explain what the backend does internally,
because the wrapper does not know — that is the black-box property.

Chapter 6 should describe the concrete pendulum model variants:
their material laws, solver choices, contact formulations, and
interface quantities. This is where the reader learns that the FEM
pendulum uses Neo-Hookean hyperelasticity with Newmark time
integration, that the Modelica FMUs use CVODE, etc.

---

## Recommended structure

    2.4 Modeling Approaches Used in This Thesis
    ├── 2.4.1 Equation-Based Modeling
    ├── 2.4.2 Musculoskeletal Multibody Modeling
    ├── 2.4.3 Continuum-Mechanical Modeling
    └── 2.4.4 Complementarity and Integration Need

---

## Standard subsection pattern

Each subsection should cover:

1. **Paradigm characterization** — what class of physical systems,
   what kind of equations (ODE, DAE, semi-discretized PDE), what
   abstraction level (lumped-parameter vs. spatially distributed).
2. **Interface abstraction** — what are the state variables, inputs,
   outputs from the perspective of a simulation unit wrapping this
   model? What structural properties (e.g. direct feedthrough,
   stiffness) are typical?
3. **Limitation that motivates complementary paradigms** — one or two
   sentences on what this paradigm cannot resolve.
4. **Boundary sentence** — forward reference to Chapter 6 for the
   concrete model and solver choices, and to Chapter 5 for the
   wrapper realization.

Name the representative tool once per subsection for concreteness
("such as Modelica", "such as OpenSim", "such as NGSolve"), but
write about the paradigm, not the tool.

---

## Content per subsection

### 2.4.1 Equation-Based Modeling

- Lumped-parameter, multi-domain physical systems.
- Acausal formulation → compiler produces DAE or ODE.
- Typical state: generalized coordinates, velocities, algebraic
  variables.
- Interface: inputs and outputs defined by the modeler; causality
  assigned at translation time.
- Structural property: direct feedthrough depends on the output
  equation; declared in the exported model metadata.
- Limitation: no spatial resolution — cannot resolve local
  deformation, stress, or distributed contact.
- Mention: when exported via FMI, the model becomes a simulation
  unit with the interface defined in §2.3.

### 2.4.2 Musculoskeletal Multibody Modeling

- Articulated rigid-body systems with joints, constraints, and
  muscle-tendon actuators.
- Forward dynamics: ODE on generalized coordinates produced by the
  multibody formulation.
- Typical state: joint angles, joint velocities.
- Interface: external forces/torques as inputs, joint kinematics or
  muscle quantities as outputs.
- Structural property: usually no direct feedthrough from applied
  force to kinematic output within a single step.
- Limitation: rigid-body assumption — no local deformation, no
  distributed stress/strain fields.

### 2.4.3 Continuum-Mechanical Modeling

- Spatially distributed systems described by PDEs (elasticity, heat,
  contact).
- Spatial semi-discretization (FEM) produces a large ODE or DAE
  system in the nodal degrees of freedom.
- The resulting systems are typically stiff and nonlinear, requiring
  implicit time integration with iterative solvers at each step.
- Typical state: nodal displacements, velocities (and possibly
  pressures or temperatures).
- Interface: boundary conditions (forces, prescribed displacements)
  as inputs; reaction forces, displacements, or field quantities at
  selected nodes as outputs.
- Structural property: direct feedthrough from prescribed boundary
  force to reaction displacement is common in quasi-static or
  implicit time integration.
- Limitation: high computational cost — not practical for full
  system-level simulation over long time horizons without selective
  activation.
- Do NOT include: weak form derivations, shape functions, specific
  material laws (Neo-Hookean), specific time integrators (Newmark),
  contact formulations. These belong in Chapter 6 where the concrete
  FEM pendulum model is described.

### 2.4.4 Complementarity and Integration Need

Summary table:

| Paradigm              | Abstraction      | Strength                  | Gap                           |
|-----------------------|------------------|---------------------------|-------------------------------|
| Equation-based        | Lumped (1D)      | Multi-domain system-level | No spatial resolution         |
| Multibody biomech.    | Lumped (1D)      | Musculoskeletal dynamics  | No local deformation          |
| Continuum mechanics   | Field (2D/3D)    | Spatial accuracy          | High cost, narrow scope       |

Key message: no single paradigm covers all relevant aspects of the
target system. This complementarity is the reason why the framework
must support heterogeneous co-simulation with subsystem models from
different paradigms and abstraction levels.

Close with a sentence linking to §2.3 (co-simulation principles
provide the coupling mechanism) and to Chapter 4 (the framework
architecture realizes this integration).

---

## Distinction from other chapters

| Question                                    | Where answered  |
|---------------------------------------------|-----------------|
| Why is heterogeneous simulation needed?     | Chapter 1       |
| What modeling paradigms are involved?       | **Chapter 2.4** |
| Why was tool X selected over tool Y?        | Chapter 3       |
| How is each model wrapped as a component?   | Chapter 5       |
| What specific models, solvers, and material | Chapter 6       |
| laws are used in the case study?            |                 |

---

## Writing checklist

- [ ] No tool-selection argument (that is Chapter 3)
- [ ] No motivation repetition (that is Chapter 1)
- [ ] No solver or integrator details (that is Chapter 6)
- [ ] No specific material laws or contact formulations (that is Chapter 6)
- [ ] No FEM derivations, no Modelica compiler internals
- [ ] No wrapper or API details (that is Chapter 5)
- [ ] Each subsection states the equation type (ODE / DAE / semi-discretized PDE)
- [ ] Each subsection states the interface abstraction (state, input, output)
- [ ] The complementarity argument is explicit
- [ ] FMI is not repeated (already in §2.3.7)
