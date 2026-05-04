# Chapter 5 Guideline

This document defines the scope, structure, and boundary rules for Chapter 5.
Chapter 5 covers feature implementation and verification.
It must be read together with the following documents.

- `thesis/guideline.md`
- `research/theory/glossary.md`
- `research/theory/notation.md`
- `thesis/golden_rules_writing_summary.md`

---

## Structure of the Implementation Sections

### Motivation
- Use 1 to 3 sentences.
- Always include this part.
- Reference the relevant SRs.
- Mention the parent UR in parentheses.
- Connect to the dependency chain.
- State which previously introduced features this section builds on.

### Theory / Background
- Use 0.5 to 1 page if needed.
- Include this part only if the implementation requires concepts not covered in Chapter 2.
- Examples include the IJCSA iteration scheme, bisection-based event localization, and zero-crossing functions.
- Skip this part for features where the implementation itself is the explanation.
- Examples include the port system and history recording.
- Reference Chapter 2 for shared foundations instead of repeating them.

### Implementation
- This is the core of each section.
- Use the most appropriate medium.
- Use a class diagram when the contribution is structural.
- Use a code listing when a specific algorithm or mechanism matters.
- Use prose with inline code when a diagram or listing would be excessive.
- Keep listings short.
- Prefer 15 to 25 lines.
- Simplify or excerpt source code instead of showing full files.

### Verification
- Use 0.5 to 1 page.
- Show one well-chosen minimal example.
- The example must demonstrate correctness of this specific feature in isolation.
- Present the setup, expected behavior, observed result, and brief discussion.
- Use a figure or table for quantitative results where useful.
- Note known limitations if any.
- Do not show comprehensive test coverage.
- The case study in Chapter 6 validates at system level.

## Boundary Rules
- Each section must be self-contained and focused on a single feature.
- Avoid mixing multiple features in one section.
- Do not repeat theory from Chapter 2 unless absolutely necessary.
- Reference Chapter 2 instead.
- Do not include implementation details that are not directly relevant to the feature being explained.
- Keep the section concise and focused.
- Do not include verification cases that test multiple features at once.
- Each verification case should isolate the feature being verified.
- Do not include comprehensive test results or coverage metrics.
- Focus on one illustrative example for verification.
- The case study in Chapter 6 covers system-level validation.

---

## Current Chapter 5 Draft Status

### Completion judgement
- Chapter 5 is now a complete first draft in terms of feature coverage.
- It is not yet a final polished chapter.
- The chapter can now move from drafting mode to cleanup and reduction mode.
- No new standalone implementation sections should be added unless a missing requirement cannot be covered by an existing section.

### Required cleanup before calling the draft complete
- Remove the obsolete reference to `sec:impl_visualization` from `5_implementation.tex`.
- Keep the system graph visualizer as a short metadata-consumer paragraph in the structural-analysis section.
- Do not reintroduce `510_visualization.tex` as a standalone section.
- Ensure that the structural-analysis verification table is complete and referenced.
- Fix small prose and spelling issues before compilation.
- Compile the full thesis and check unresolved references, float placement, and overfull boxes.

### Coverage check
- The port system covers typed and unit-aware data exchange.
- The component interface covers lifecycle, ports, state, history, structural metadata, and hybrid hooks.
- The backend wrappers cover FMI, OpenSim, and finite-element integration.
- The system section covers component registration, signal connections, event connections, algorithm selection, lifecycle orchestration, and history aggregation.
- The structural-analysis section covers full graphs, zero-delay graphs, SCC detection, condensation, delayed producers, execution metadata, and graph visualization as an inspection helper.
- The algebraic-loop section covers SCC-local interface iteration.
- The master-algorithm section covers Jacobi, Gauss--Seidel, and global IJCSA orchestration.
- The hybrid section covers trial stepping, localization, dense-time event handling, and selected verification cases.
- The multi-model section covers runtime switching, state adaptation, hysteresis, active-model delegation, and verification.

### Current balance risk
- Chapter 5 is technically strong but long.
- Structural analysis and hybrid execution are the largest sections.
- This is acceptable because they are central contributions.
- Wrapper sections should be checked for repeated lifecycle prose.
- Verification tables should be checked for method-list style.
- Chapter 6 must not be shorter in argumentative weight than Chapter 5.

---

## Discussion Guidance for Chapter 5

Chapter 5 may discuss direct consequences of implementation choices.
Such discussion must stay short.
Broader limitations and interpretation belong to Chapter 7.

Use one or two consequence sentences per section where helpful.
Do not create separate discussion subsections inside Chapter 5.

### Port System
- Discuss that strict type and unit validation catches connection errors before simulation.
- Mention that the unit registry defines the accepted unit vocabulary.
- Do not discuss general dimensional-analysis theory.

### Component Interface
- Discuss that the template-method lifecycle centralizes time advancement, output refresh, and history recording.
- Mention that wrappers only implement model-specific hooks.
- Mention that state transfer and rollback are intentionally separate concepts.
- Do not list every base-class method.

### Component Wrappers
- Discuss backend asymmetry explicitly.
- FMI can be wrapped generically because the FMU descriptor exposes ports, parameters, and dependencies.
- OpenSim needs concrete subclasses because no equivalent descriptor defines a co-simulation interface.
- FEM support is intentionally minimal because discretization, state representation, and solver state are model-specific.
- Mention rollback limitations for generic wrappers only where relevant.
- Defer concrete FE pendulum details to Chapter 6.

### System and Connections
- Discuss that registration validates the structural definition before simulation.
- Mention that single assignment ensures every input has a unique driver.
- Mention that event connections route events but do not define event semantics.
- Mention that system history supports interaction requirements for recorded results.
- Do not repeat structural-analysis logic.

### Structural Analysis
- Discuss that the implementation assumes fixed direct-feedthrough metadata during a run.
- Mention that the active-output filter reduces unnecessary zero-delay constraints.
- Mention that delayed-producer relocation is a `syssimx` scheduling choice.
- Mention that graph visualization is an inspection helper and not part of simulation semantics.
- Do not discuss IJCSA convergence here.

### Algebraic Loop Resolution
- Discuss that SCC-local IJCSA keeps loop solving local to the detected interface variables.
- Mention that the solver commits only consistent interface values.
- Mention convergence assumptions only briefly.
- Defer numerical robustness limitations to Chapter 7 if needed.

### Master Algorithms
- Discuss the implementation consequence of each algorithm.
- Jacobi stages all inputs before stepping and therefore preserves old-output visibility within a macro step.
- Gauss--Seidel interleaves propagation and stepping generation by generation.
- Global IJCSA solves the zero-delay interface globally before the normal step order continues.
- Mention that Jacobi is not parallelized in the current implementation.
- Do not repeat Chapter 2 execution-strategy theory.

### Hybrid Co-Simulation Algorithm
- Discuss that the hybrid path reuses Gauss--Seidel input preparation and stepping.
- Mention that trial stepping and localization require rollback-capable event sources.
- Mention that dense time makes cascaded events deterministic at one physical time.
- Mention that commutativity checks avoid nondeterministic simultaneous event handling.
- Keep algorithmic consequences short.
- Leave broader limitations for Chapter 7.

### Multi-Model Component
- Discuss that the wrapper keeps the external interface fixed while the active internal model changes.
- Mention that state adaptation is the central extension point.
- Mention that inactive models receive current inputs but are not continuously state-synchronized.
- Mention that hysteresis reduces switching chatter.
- Defer the realistic MasterPendulum use case to Chapter 6.

---

## Reduction and Compaction Guidance

### High-priority compaction targets
- Shorten repeated lifecycle descriptions in the FMU and OpenSim wrapper sections.
- Shorten verification tables that read like test coverage reports.
- Shorten captions that restate full paragraphs.
- Remove repeated definitions of direct feedthrough, SCCs, execution order, rollback, dense time, and event localization.
- Replace repeated explanations with cross-references.
- Keep only figures that explain data flow, control flow, or verification evidence.

### Sections that should not be expanded further
- Port System
- Component Interface
- System and Connections
- Structural Analysis and Execution Ordering
- Hybrid Co-Simulation Algorithm
- Multi-Model Component and Mode Switching

These sections already contain enough implementation detail for a thesis draft.
Future work on them should focus on clarity and reduction.

### Sections that may need alignment rather than expansion
- Component Wrappers
- Algebraic Loop Resolution
- Master Algorithms

The wrapper section should keep the backend asymmetry visible.
The algebraic-loop section is compact and should remain compact.
The master-algorithm section should stay focused on orchestration behavior.

### Table of contents guidance
- The table of contents should show only major framework features.
- Sections should appear in the table of contents.
- Subsections may appear if the thesis class includes them by default.
- Subsubsections and paragraphs should not be used to expose local implementation details in the table of contents.
- Do not make `System Graph Visualization` a table-of-contents section.

### Final transition rule
- End Chapter 5 with a short transition to Chapter 6.
- State that Chapter 5 verified framework features in isolation.
- State that Chapter 6 evaluates their combined use in the controlled-pendulum case study.
- Do not add new technical claims in the transition.

