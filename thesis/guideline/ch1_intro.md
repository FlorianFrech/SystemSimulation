# Chapter 1 Guideline

This document defines the role, structure, terminology, and writing rules for
Chapter 1 of the thesis.
Use it together with `README.md`, `thesis_concept.md`,
`golden_rules_writing_summary.md`, `writing_style.md`, `glossary.md`, and
`notation.md`.

Chapter 1 must motivate the work, position it in the state of the art, identify
the research gap, introduce `syssimx`, state the research questions and
objectives, and guide the reader through the thesis structure.

---

## 1. Chapter Function

Chapter 1 answers these questions for the reader:

- What kind of engineering problem motivates the thesis?
- Why is system-level simulation needed for this class of systems?
- Why are heterogeneous tools and co-simulation relevant?
- Which parts of the current state of the art are sufficient, and where does a
  gap remain?
- What is the contribution of the thesis?
- Which research questions and objectives structure the work?

The chapter must not become a detailed theory chapter.
It should introduce the problem and the gap, then point to later chapters for
technical depth.

---

## 2. Recommended Section Roles

### 1.1 Context and Motivation

Purpose:

- Start from the application class: active mechatronic devices, powered
  prostheses, exoskeletons, and biomechanical interaction.
- Explain why isolated subsystem analysis is insufficient.
- Motivate system-level simulation and heterogeneous model integration.
- Introduce co-simulation as a natural integration strategy.
- Mention `FMI` as an interface standard, but do not fully explain `FMU` here.

Do not introduce `syssimx` in this section.
The reader should first understand the problem before seeing the proposed
framework.

### 1.2 State of the Art

Purpose:

- Give a focused orientation, not an exhaustive literature review.
- Cover only the tool classes and concepts needed for the thesis argument.
- Explain the current landscape of equation-based modeling, domain-specific
  simulation tools, co-simulation frameworks, hybrid co-simulation, and
  multi-model or multi-fidelity simulation.
- End with the remaining orchestration gap.

Do not present `syssimx` as part of the state of the art.
The state of the art should stay solution-neutral.

### 1.3 Problem Statement and Research Gap

Purpose:

- Compress the gap into a clear problem statement.
- Introduce `syssimx` for the first time.
- State the contribution in a compact list.

Recommended first introduction:

```latex
This thesis addresses this gap by developing \syssimx{}, a Python-based
framework for heterogeneous hybrid co-simulation.
\syssimx{} provides a common orchestration layer for subsystem models that
remain implemented in their domain-specific simulation tools.
It connects heterogeneous models, analyzes their coupling structure, handles
hybrid events, and supports runtime switching between alternative
representations of the same subsystem.
```

Avoid introducing `syssimx` before the gap is clear.

### 1.4 Research Questions

Purpose:

- State one central research question.
- Split it into focused sub-questions that map to the thesis structure.
- Use research questions to define what the thesis must answer.

The research questions should be solution-aware but not implementation-heavy.
They should avoid method names such as `HybridAlgorithm` or `MultiComponent`.

### 1.5 Objectives

Purpose:

- Convert the research questions into concrete thesis tasks.
- Use objectives to define what will be designed, implemented, and evaluated.
- Keep the objectives traceable to later chapters.

Objectives should be action-oriented:

- design,
- develop,
- implement,
- apply,
- evaluate.

### 1.6 Thesis Outline

Purpose:

- Give a concise map of the remaining chapters.
- Mention the function of each chapter.
- Avoid repeating the contribution list.

---

## 3. Terminology Rules for Chapter 1

Use the glossary as binding.
The following rules are especially important in the introduction.

### System, Subsystem, Simulation Unit, Component

- Use **system** for the physical or mathematical whole.
- Use **subsystem** for a conceptual or physical part of the system.
- Use **simulation unit** for a tool-neutral executable unit in a co-simulation.
- Use **component** only when referring to the concrete `syssimx` abstraction.

In the state of the art, prefer:

```text
simulation unit
```

In the contribution and objectives, `component` is acceptable because the text
refers to the `syssimx` framework abstraction.

### CPS and Mechatronic Systems

Use **cyber-physical system** for the general class in which computation and
physical behavior interact.
Use **mechatronic system** for the engineering application class with mechanics,
electronics, sensors, actuators, and control.

Avoid treating the two as unrelated categories.
The motivation can state that active mechatronic devices are typical
cyber-physical systems.

### Modelica and OpenModelica

Use **Modelica** for the modeling language and the model formulation.
Use **OpenModelica** for the tool, compiler, simulator, FMU exporter, or
monolithic reference environment.

Preferred:

```text
The subsystem is modeled in Modelica and simulated with OpenModelica.
```

Avoid:

```text
The subsystem is an OpenModelica model.
```

unless the sentence explicitly refers to a model file in the OpenModelica
project.

### FMI and FMU

Introduce `FMI` before `FMU`.
Use `FMU` only after the relation has been stated.

Recommended state-of-the-art introduction:

```latex
For tool interoperability, the \ac{FMI} standard has become particularly
important \cite{FMI2.0}.
It defines how simulation units are packaged as \acp{FMU} and how an importing
environment instantiates them, sets inputs and parameters, advances them
through standardized calls, and reads their outputs at communication points.
```

Do not explain the full FMI standard in Chapter 1.
Detailed concepts belong in Chapter 2.

---

## 4. Acronym Rules

Use the acronym package consistently.

- Use `\ac{FMI}` for first use and later short use.
- Use `\acp{FMU}` for plural.
- Use `\acs{...}` only when the short form is required explicitly.
- Do not manually write `Functional Mock-up Interface (FMI)` after the acronym
  system is active.
- If an acronym appears in the abstract or front matter, `\acresetall` in
  `main.tex` keeps the main text first-use behavior intact.

Check that every acronym used in Chapter 1 is defined in
`thesis/other/acronyms.tex`.
Currently important candidates include:

- CPS,
- CAD,
- FMI,
- FMU,
- FEM.

---

## 5. State-of-the-Art Scope

The state-of-the-art section should cover five focused areas.

1. Equation-based modeling and FMI-based simulation units.
2. Domain-specific simulation environments such as OpenSim and FEM tools.
3. Co-simulation frameworks and orchestration.
4. Hybrid co-simulation and event handling.
5. Multi-model and multi-fidelity simulation.

The section should not become a survey of all tools.
Each subsection should end with the consequence for the thesis.

Good pattern:

```text
Tool class -> capability -> limitation for heterogeneous hybrid simulation.
```

Avoid:

```text
Tool class -> long feature list -> no connection to the thesis gap.
```

### Frameworks versus FMI Libraries in Section 1.2.3

Section 1.2.3 must keep two paragraphs distinct.

- **FMI-based orchestration frameworks** are full co-simulation environments with coordinator, master algorithms, and scenario assembly. Place OMSimulator, INTO-CPS Maestro, and CoFMPy in this paragraph.
- **Python FMI libraries** are lower-level interfaces to the FMI standard. Place FMPy and PyFMI in this paragraph.

CoFMPy is a framework, not a library.
It provides FMU coupling, Jacobi and Gauss-Seidel master algorithms, fixed-point algebraic-loop handling, a Python FMU proxy for non-FMU components, and Digital-Twin oriented communication and storage blocks.
Placing it next to FMPy and PyFMI underrepresents its scope and weakens the gap statement in Section 1.3.

Recommended introduction sentence for CoFMPy in the frameworks paragraph:

```latex
CoFMPy is a more recent Python-native framework for rapid prototyping of FMI-based Digital Twins, combining FMU co-simulation, algebraic-loop handling, datastream communication, and a Python FMU proxy for non-FMU components~\cite{friedrich_cofmpy_2025}.
```

Do not include the full CoFMPy architecture in Chapter 1.
The contribution boundary against CoFMPy belongs in Chapter 7.

---

## 6. Research Gap Rules

The research gap should be stated as a missing workflow capability.
It should not claim that existing tools are weak in general.

Preferred gap:

```text
Existing approaches are strong either in standardized FMU-based coupling or in
domain-specific analysis, but they provide only limited support for the unified
integration of FMU models, musculoskeletal models, and finite-element models
within one common simulation environment.
```

The gap should combine these aspects:

- heterogeneous tool coupling,
- dependency-aware execution,
- algebraic-loop handling,
- hybrid event handling,
- runtime switching between alternative subsystem models.

Avoid overclaiming.
Do not state that no framework can do any of these things.
State that the combined workflow is insufficiently addressed for the thesis
scope.

---

## 7. Contribution List Rules

The contribution list should use compact noun phrases.
It should not contain implementation details or result claims.

Preferred:

```latex
\begin{itemize}
    \item a unified component abstraction for heterogeneous subsystem models,
    \item graph-based structural analysis for dependency detection,
          execution-order resolution, and algebraic-loop identification,
    \item hybrid event handling for detection, localization, dispatch, and
          cascaded event processing,
    \item a multi-model component concept for runtime switching between
          alternative subsystem models with state synchronization, and
    \item a controlled-pendulum case study combining \acp{FMU}, OpenSim, and
          \ac{FEM} models.
\end{itemize}
```

Do not include benchmark values or detailed verification outcomes in the
contribution list.

---

## 8. Research Question Rules

The central research question should cover the full thesis:

- heterogeneous subsystem models,
- hybrid co-simulation,
- orchestration,
- event handling,
- runtime switching.

Sub-questions should map to later chapters.

Suggested mapping:

| Research question | Main evidence |
|---|---|
| RQ1 component abstraction | Chapters 4 and 5 |
| RQ2 dependency analysis | Chapters 4 and 5 |
| RQ3 hybrid event handling | Chapter 5 and Chapter 6 |
| RQ4 runtime switching | Chapter 5 and Chapter 6 |
| RQ5 framework behavior and benchmark scenarios | Chapter 6 |

Avoid using `component` in a tool-neutral way.
If the question refers to `syssimx`, `component interface` is acceptable.
If it refers to the general problem, use `simulation unit`.

---

## 9. Objective Rules

Objectives should be concrete and verifiable by later chapters.

Use:

- Design a ...
- Develop a ...
- Implement ...
- Apply ...
- Evaluate ...

Avoid:

- Explore ...
- Investigate ...
- Discuss ...

unless no concrete implementation or evidence is expected.

The objectives should not claim physical validation.
Use `evaluate` for framework behavior and case-study evidence.

---

## 10. Writing Style Rules for Chapter 1

Apply `writing_style.md` strictly.
In Chapter 1 this means:

- Use short paragraphs.
- Avoid broad generic motivation.
- Avoid long tool feature lists.
- Avoid "not A; instead B" patterns.
- Avoid "facilitates", "methodology", "sophisticated", and "robust" unless
  supported by evidence.
- Avoid repeating the same gap in multiple sections.
- Use positive direct statements.

Preferred:

```text
\syssimx{} provides a common orchestration layer for subsystem models that
remain implemented in their domain-specific simulation tools.
```

Avoid:

```text
The framework is not intended to replace domain-specific simulation tools.
Instead, it provides a common orchestration layer.
```

---

## 11. Citation Rules

Use citations where Chapter 1 discusses external facts, standards, or prior
work.

Typical citation roles:

- CPS and system-level motivation: Lee, virtual engineering, biomechanical
  interaction.
- Co-simulation and FMI: Gomes, FMI 2.0, FMI 3.0.
- Structural dependencies and algebraic loops: Broman, Sicklinger.
- Hybrid co-simulation and events: Broman, Cremona, Step Revision.
- Multi-fidelity and switching: Peherstorfer, Fernandez-Godino, Choi, Williams.

Do not cite sources for your own framework contribution.
Do not overload one sentence with many citations if the sources support
different claims.

---

## 12. Common Chapter 1 Risks

Risk: `syssimx` appears before the gap is introduced.
Correction: Mention the framework first in Section 1.3.

Risk: The state of the art repeats the motivation.
Correction: Keep Section 1.2 focused on tool classes and orchestration limits.

Risk: `FMU` is used before the `FMI` and `FMU` relation is introduced.
Correction: Introduce `FMU` in the FMI paragraph of the state of the art.

Risk: `component` is used for tool-neutral simulation units.
Correction: Use `simulation unit` until the text refers to `syssimx`.

Risk: The gap is too broad.
Correction: Bound it to heterogeneous hybrid co-simulation with model switching.

Risk: The research questions and objectives duplicate each other.
Correction: Use research questions for what must be answered and objectives for
what will be done.

---

## 13. Chapter 1 Review Checklist

Before accepting Chapter 1, check:

- The motivation explains why heterogeneous system-level simulation is needed.
- `syssimx` is first introduced in the research-gap section.
- `FMI` is introduced before `FMU`.
- All acronyms used in Chapter 1 are defined in `other/acronyms.tex`.
- The state of the art is selective and thesis-focused.
- The research gap follows logically from the state of the art.
- The contribution list is compact and does not contain result claims.
- Research questions map to later chapters.
- Objectives are concrete and evaluable.
- The outline describes chapter functions without repeating the thesis.
- Terminology follows `glossary.md`.
- The prose follows `writing_style.md`.

---

## 14. Short Rule

Chapter 1 should move from problem to gap to contribution.
Do not explain the solution before the reader understands why it is needed.
