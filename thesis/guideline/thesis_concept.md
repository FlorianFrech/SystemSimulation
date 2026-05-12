# Thesis Concept

This document defines the stable thesis-level concept.
It states what the thesis is about, what it claims, what it does not claim,
and how the chapters build the argument.

Use this document together with:

- `README.md`
- `golden_rules_writing_summary.md`
- `writing_style.md`
- `glossary.md`
- `notation.md`
- the chapter-specific guideline for the affected chapter

Chapter-specific drafting rules, temporary cleanup tasks, notation details, and
terminology definitions belong in their dedicated guideline documents.

---

## 1. Thesis Objective

The thesis develops and evaluates `syssimx`, a Python framework for
heterogeneous hybrid co-simulation.
The framework targets system-level simulation scenarios in which subsystem
models come from different modeling tools, use different internal solvers, and
must still be coupled through a consistent simulation workflow.

The central objective is to show how such a framework can assemble, analyze,
execute, and evaluate coupled simulations with:

- typed and unit-aware ports,
- a shared component interface,
- backend wrappers for heterogeneous tools,
- structural analysis and execution ordering,
- algebraic-loop resolution,
- continuous and hybrid master algorithms,
- event handling with rollback and superdense time,
- and runtime switching between alternative subsystem models.

---

## 2. Research Problem

System-level simulation of cyber-physical and biomechanical systems often
requires models from several tools and modeling paradigms.
One tool may be suitable for equation-based system models, another for
multibody dynamics, and another for finite-element contact mechanics.
These models cannot be combined by one solver directly when they are available
only as executable simulation units.

The research problem is therefore not only numerical time integration.
It is the construction of a coherent co-simulation workflow that handles
heterogeneous model interfaces, structural dependencies, algebraic loops,
discrete events, and runtime model changes.

---

## 3. Main Contribution

The main contribution is the design, implementation, and evaluation of the
`syssimx` framework.
The framework provides a common component abstraction for heterogeneous
simulation backends and implements the orchestration logic required for
continuous, hybrid, and multi-model co-simulation.

The thesis contribution is not a new physical pendulum model.
The controlled pendulum is the case-study system used to exercise and evaluate
the framework.

---

## 4. Scope and Non-Goals

The thesis covers:

- framework architecture,
- feature implementation,
- feature-level verification,
- system-level case-study evaluation,
- comparison with monolithic model-based references,
- and runtime benchmarking for selected configurations.

The thesis does not claim:

- physical validation against experimental data,
- a general-purpose replacement for specialized simulation tools,
- optimal numerical performance for all co-simulation problems,
- complete support for every FMI or backend feature,
- or universal convergence guarantees for all coupled systems.

Comparisons against OpenModelica are numerical verification against a
model-based reference.
They are not physical validation.

---

## 5. Thesis Narrative

The thesis follows this argument.

1. Heterogeneous system simulation requires a framework that can combine
   different modeling tools and execution semantics.
2. Co-simulation provides the conceptual basis for coupling executable
   subsystem models.
3. The framework architecture defines the abstractions needed to represent
   components, ports, connections, systems, and algorithms.
4. The implementation realizes these abstractions in `syssimx` and verifies
   the main features in focused scenarios.
5. The controlled-pendulum case study evaluates the combined workflow on a
   closed-loop system with heterogeneous plant models, contact events, and
   model switching.
6. The discussion interprets what the framework demonstrates, where the
   results are limited, and what remains for future work.

---

## 6. Chapter Roles

| Chapter | Role |
|---|---|
| Chapter 1 | Motivation, problem context, research gap, contribution, and related work orientation |
| Chapter 2 | Minimum theory needed to understand the framework, implementation, and case study |
| Chapter 3 | Requirements and tool choices |
| Chapter 4 | Framework architecture and abstractions |
| Chapter 5 | Implementation and feature-level verification |
| Chapter 6 | Controlled-pendulum case study and system-level evidence |
| Chapter 7 | Discussion, limitations, conclusions, and outlook |

Do not let one chapter absorb the role of another chapter.
In particular, Chapter 5 must not become API documentation, and Chapter 6 must
not become another implementation chapter.

---

## 7. Main Claims

The thesis should support the following main claims.

1. `syssimx` provides a coherent component abstraction for heterogeneous
   co-simulation.
2. The framework can derive structural execution metadata from component
   connections and direct-feedthrough information.
3. The implemented master algorithms execute coupled simulations consistently
   with the stored structural metadata.
4. The hybrid algorithm can detect, localize, and handle events in coupled
   simulations with rollback-capable event sources.
5. The multi-model component keeps a fixed external interface while switching
   between alternative internal models.
6. The controlled-pendulum case study verifies selected co-simulation results
   against monolithic OpenModelica references.
7. Runtime model switching can reduce the computational cost of using the FEM
   pendulum in the selected contact scenario, with a measurable trajectory
   deviation.

The detailed mapping from claims to evidence belongs in
`claims_and_evidence.md`.

---

## 8. Evidence Strategy

The thesis uses three evidence levels.

| Evidence level | Chapter | Purpose |
|---|---|---|
| Feature-level verification | Chapter 5 | Show that individual framework mechanisms behave as expected |
| Numerical case-study verification | Chapter 6 | Compare selected co-simulation results with monolithic model-based references |
| Runtime benchmark | Chapter 6 | Measure computational cost for selected configurations |

This evidence supports framework behavior and workflow suitability.
It does not establish physical validation.

---

## 9. Global Risks

The main thesis risk is scope control.
The framework has enough technical substance, but the thesis must not become a
software manual.

Current risks:

- Chapter 5 may become too long and too method-oriented.
- Verification sections may read like test coverage reports.
- Chapter 6 may become too short compared with the implementation chapter.
- The discussion may become weak if it only repeats results.
- Terminology may drift between theory-level and implementation-level prose.
- Figures and captions may repeat the surrounding text.

Use the chapter-specific guideline documents to control these risks.

---

## 10. Short Working Rule

Write only what the reader needs at that point in the thesis.
Use the correct chapter for the correct type of content.
Make every claim traceable to evidence.
