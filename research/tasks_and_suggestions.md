# Chapter 2 Theory Chapter – Tasks, Suggestions, and Structural Recommendations

## Purpose of this document

This document summarizes the recommendations, tasks, and structural decisions for improving **Chapter 2 – Theoretical Background** of the master's thesis.

The goal of Chapter 2 is:

- to introduce the **fundamental theory and concepts** required to understand the **SysSimX** framework,
- to prepare the reader for the implementation and design chapters,
- to remain **compact, precise, and relevant**,
- to avoid repeating the context and motivation already introduced in Chapter 1,
- to avoid detailed algorithmic and implementation-specific explanations that belong later in the thesis.

Detailed technical explanations of:

- dependency graph construction,
- strongly connected components,
- algebraic loop detection,
- IJCSA-based algebraic loop solution,
- event-time localization via bisection,
- and implementation-specific hybrid orchestration

should be placed in **Chapter 5**, close to the implementation.

---

# 1. Core design principle for Chapter 2

## Recommended role of Chapter 2

Chapter 2 should provide the **minimum complete theoretical basis** needed for the reader to:

- understand the framework architecture,
- understand the component abstractions,
- understand co-simulation and hybrid simulation terminology,
- follow the implementation and case study later without conceptual gaps.

## What Chapter 2 should not do

Chapter 2 should **not**:

- repeat the full motivation from Chapter 1,
- become a detailed algorithm chapter,
- include implementation-specific procedural detail,
- become a second state-of-the-art chapter,
- explain theory that is never used later.

---

# 2. Decision on the hybrid example

## Recommendation

Use the **pendulum with ideal elastic wall contact** as the running example for the hybrid system section.

This is a strong choice because it:

- stays consistent with the pendulum already used elsewhere in the thesis,
- avoids introducing a second unrelated toy system,
- connects naturally to the later case study,
- illustrates hybrid behavior in a physically intuitive way.

## What the example should demonstrate

The pendulum-wall example can illustrate:

- **state events**,
- **zero-crossing based event detection**,
- **event localization**,
- **reset maps**,
- **pre-event and post-event state values**,
- **restart of continuous simulation after an event**.

## Important physical clarification

Do **not** describe the impact as a discontinuity in position.

For ideal elastic impact at the wall:

- the **angle / position remains continuous**,
- the **velocity jumps discontinuously**,
- the position trajectory has a **kink**,
- the velocity trajectory has a **jump**.

A suitable reset relation is:

```math
\theta^{+} = \theta^{-} = \theta_{\mathrm{wall}}, \qquad
\omega^{+} = -e\,\omega^{-}
```

For ideal elastic impact:

```math
e = 1
```

## Suitable event indicator

A clean event indicator is:

```math
\gamma(\theta) = \theta - \theta_{\mathrm{wall}}
```

The event is triggered when the trajectory reaches the wall in the admissible crossing direction.

## How to use the example in the thesis

### In Chapter 2

Use it only as a **conceptual hybrid example**.

Focus on:

- event condition,
- zero-crossing,
- reset,
- continuation after event.

Do **not** yet explain:

- rollback,
- bisection implementation,
- master algorithm details,
- FMI limitations,
- PID reset strategies,
- implementation workarounds.

### In Chapter 5 / 6

Return to the controlled pendulum with:

- hybrid co-simulation algorithm,
- event localization,
- rollback,
- wall contact handling,
- controller interaction,
- PID anti-windup or reset behavior.

---

# 3. Recommended notation strategy

## Main recommendation

Use a **hybrid notation strategy**:

- a **global notation and conventions subsection** at the beginning of Chapter 2,
- plus **local notation extensions** inside each subsection.

This is better than only using local notation, and also better than trying to define everything globally in advance.

---

## 3.1 Global notation subsection at the beginning of Chapter 2

Create a short subsection such as:

```text
2.0 Notation and Conventions
```

This subsection should define only the symbols that recur across several sections.

## Suggested globally defined symbols

- \( t \): physical time
- \( x(t) \): continuous state vector
- \( z(t) \): algebraic variable vector
- \( q(t) \): discrete state / mode / logic state
- \( u(t) \): input vector
- \( y(t) \): output vector
- \( T_k \): communication points in co-simulation
- \( H \): macro step size
- \( \Delta t_{i,r} \): local step size of subsystem \( i \) and mirco steo \( r \)
- \( (t,\nu) \): superdense time
- \( (\cdot)^- \), \( (\cdot)^+ \): pre-event and post-event values
- subsystem index \( i \)

## Benefits of a global notation section

- creates consistency across all theory sections,
- reduces redefinition,
- lowers cognitive load for the reader,
- improves transitions to later chapters.

---

## 3.2 Local notation extensions inside subsections

Inside each subsection, only define **new symbols** that are specific to that concept.

### Examples

#### In hybrid system modeling

Introduce locally:

- \( \gamma_j \): event indicator / guard function,
- \( t_e \): event time,
- \( R_j \): reset map.

#### In co-simulation section

Introduce locally:

- communication grid,
- coupling operator,
- subsystem-local stepping notation,
- execution ordering notation if needed.

#### In FMI subsection

Introduce locally:

- FMU,
- importer,
- master algorithm,
- capability flags,
- model exchange / co-simulation terminology.

## Rule

Do **not** redefine core symbols such as \(x\), \(u\), \(y\), \(z\), \(q\) if they are already introduced globally.

---

# 4. Recommended subsection writing pattern

For almost every subsection in Chapter 2, use the following structure.

## Standard subsection pattern

### 1. Short prose bridge

Start with a short paragraph that explains:

- why this concept is needed,
- where it fits into the thesis,
- what problem it helps to understand.

### 2. Notation block

Then define:

- the symbols used in this subsection,
- only the new notation that is needed here,
- or explicitly state how existing notation is extended.

### 3. Core concept explanation

Then explain the concept itself:

- one precise conceptual explanation,
- one or two central equations,
- one compact formal description.

### 4. Minimal example or figure

Then include:

- a very simple illustrative example,
- preferably related to the running pendulum example,
- or a compact conceptual diagram.

### 5. Boundary sentence

End with a sentence that clearly defers the technical detail to later chapters.

Example:

> The detailed algorithmic realization used in SysSimX is described in Chapter 5.

---

# 5. Concrete structural recommendations for Chapter 2

## Proposed Chapter 2 structure

### 2.0 Notation and Conventions
Short global symbol and terminology definition.

### 2.1 Continuous-Time System Modeling
- dynamical systems with inputs and outputs
- ODEs and DAEs
- direct feedthrough and algebraic loops

### 2.2 Hybrid System Modeling
- hybrid state representation
- events and zero-crossings
- reset and reinitialization
- time semantics in hybrid simulation

### 2.3 Co-Simulation Principles and Algorithms
- monolithic simulation vs co-simulation
- mathematical formulation of co-simulation
- execution strategies
- direct feedthrough and algebraic loops in co-simulation
- initialization of coupled systems
- hybrid co-simulation
- FMI

### 2.4 Domain-Specific Modelling Foundations
Only short, scoped foundations for:
- Modelica
- OpenSim
- NGSolve / FEM

This section should explain only what is later needed to understand:
- wrappers,
- interfaces,
- subsystem role,
- coupling assumptions.

It should **not** become a deep numerical methods chapter.

---

# 6. What to write next

## Priority order for the remaining work in Chapter 2

### Priority 1 — Add notation and conventions subsection
This creates consistency before the remaining theory text is expanded.

### Priority 2 — Complete Section 2.2 Hybrid System Modeling
Use the pendulum-wall example here.

### Priority 3 — Complete Section 2.3 Co-Simulation Principles
Focus on conceptual foundations only.

### Priority 4 — Scope and compress Section 2.4 Domain-Specific Foundations
Only include what is later used.

### Priority 5 — Review consistency across all Chapter 2 sections
Check:

- notation consistency,
- term consistency,
- figure style consistency,
- forward references to later chapters.

---

# 7. Detailed task list

## Task A — Add a notation and conventions subsection

### Deliverable
A short section at the beginning of Chapter 2 containing:

- recurring symbols,
- event notation,
- superdense time notation,
- pre-/post-event notation,
- terminology conventions.

### Checklist
- [ ] Define \(x, z, q, u, y\)
- [ ] Define \(T_k, H, h_i\)
- [ ] Define \((t,\nu)\)
- [ ] Define pre/post-event notation
- [ ] Define terminology rules for subsystem / component / FMU / master

---

## Task B — Rewrite / strengthen Hybrid System Modeling section

### Deliverable
A compact but rigorous hybrid systems section using the pendulum-wall contact example.

### Include
- hybrid state decomposition,
- event indicators,
- event times,
- reset maps,
- restart after event,
- superdense time at conceptual level.

### Avoid here
- implementation details,
- event localization algorithm details,
- rollback mechanisms,
- framework-specific API.

### Checklist
- [ ] Introduce hybrid state representation
- [ ] Define event indicator
- [ ] Introduce event time
- [ ] Define reset map
- [ ] Use pendulum-wall example
- [ ] Add one clear figure

---

## Task C — Use pendulum-wall example properly

### Deliverable
A physically correct example description and figure.

### Checklist
- [ ] Position continuous
- [ ] Velocity jump
- [ ] No claim of position jump
- [ ] Mark event time in plots
- [ ] Include wall angle in diagram
- [ ] Provide reset equation

---

## Task D — Standardize subsection style

### Deliverable
All theory subsections follow the same structure.

### Checklist
- [ ] Short prose introduction
- [ ] Notation block
- [ ] Core concept
- [ ] Minimal figure/example
- [ ] Forward reference to Chapter 5 where appropriate

---

## Task E — Keep deep implementation theory in Chapter 5

### Deliverable
A clean theory/implementation separation.

### Move or keep in Chapter 5
- dependency graph construction,
- SCC detection,
- Tarjan-based loop detection,
- IJCSA derivation and realization,
- event localization via bisection,
- rollback realization,
- algorithm pseudocode,
- hybrid master step logic.

### Checklist
- [ ] Remove algorithm detail from Chapter 2 if too deep
- [ ] Add forward references instead
- [ ] Ensure Chapter 5 picks up the terms consistently

---

## Task F — Add the right diagrams

### Deliverable
Only high-value figures that directly improve understanding.

## Recommended figures for Chapter 2

### Figure 1 — Continuous-time pendulum
Already acts as a running example.

### Figure 2 — Hybrid pendulum with wall
Show:
- pendulum,
- wall location,
- angle definition,
- event condition.

### Figure 3 — Time plots for hybrid example
Show:
- \(\theta(t)\) with kink,
- \(\omega(t)\) with jump,
- event time \(t_e\).

### Figure 4 — Communication grid in co-simulation
Show:
- macro steps,
- subsystem-local micro steps,
- communication points.

### Figure 5 — Jacobi vs Gauss-Seidel execution
Very compact schematic.

### Figure 6 — Algebraic loop at interface level
A direct feedthrough cycle in co-simulation.

### Figure 7 — Event localization inside one macro step
Simple interval view with event time inside \([T_k, T_{k+1}]\).

---

# 8. Terminology rules

To keep the chapter consistent, define a few terminology rules and then follow them strictly.

## Recommended terminology

### System
The coupled overall model.

### Subsystem
A theoretical part of the system.

### Component
A concrete framework-level simulation unit in SysSimX.

### Simulation unit
General theory term for a black-box co-simulation participant.

### FMU
A standardized FMI component artifact.

### Master algorithm
The orchestration logic of the coupled simulation.

### Event
A discrete occurrence that changes mode, state, or equations.

### Reset
The instantaneous update at event time.

### Reinitialization / restart
Continuation of continuous simulation from the post-event state.

---

# 9. Compact guidance for the co-simulation section

## What this section must achieve

The co-simulation section should explain just enough for the reader to understand:

- why subsystems are coupled through communication points,
- why inputs need approximation between communication points,
- why execution order matters,
- why direct feedthrough can create algebraic loops,
- why initialization is nontrivial,
- why hybrid co-simulation is harder than pure continuous co-simulation,
- why FMI matters.

## What it should not yet do

It should not yet derive:

- detailed graph algorithms,
- the exact IJCSA formulation used in code,
- the full event localization procedure,
- implementation-specific solver orchestration.

---

# 10. Suggested writing principle for every theory section

Use this internal rule while writing:

> Only explain a concept in Chapter 2 if it is later used, referenced, or required for understanding the framework, implementation, or case study.

This prevents the theory chapter from becoming too broad.

---

# 11. Final recommendations

## Strong recommendations

- Use the **pendulum with ideal elastic wall contact** as the hybrid theory example.
- Add a short **Notation and Conventions** subsection at the beginning of Chapter 2.
- Use a **hybrid notation strategy**: global base notation + local subsection extensions.
- Write subsections in the pattern:
  - short prose,
  - notation,
  - concept,
  - minimal example,
  - forward reference.
- Keep algorithmic details such as SCC detection, IJCSA, and bisection in **Chapter 5**.
- Use only diagrams that directly support concepts you later need.

## Most important immediate next step

The best next concrete step is:

1. create the notation subsection,
2. then rewrite **2.2 Hybrid System Modeling** around the pendulum-wall example.

---

# 12. One-page action plan

## Immediate actions
- [ ] Add `2.0 Notation and Conventions`
- [ ] Standardize symbol usage across Chapter 2
- [ ] Rewrite `2.2 Hybrid System Modeling`
- [ ] Use pendulum + wall as hybrid example
- [ ] Add one hybrid event figure
- [ ] Add \(\theta(t)\) and \(\omega(t)\) plot sketch

## After that
- [ ] Complete conceptual co-simulation subsection
- [ ] Add compact execution strategy figures
- [ ] Scope domain-specific section down to essentials
- [ ] Review all forward references to Chapter 5

## Final review checks
- [ ] No repeated motivation from Chapter 1
- [ ] No unused theory
- [ ] No inconsistent notation
- [ ] No premature implementation detail
- [ ] Clear boundary between theory and implementation
