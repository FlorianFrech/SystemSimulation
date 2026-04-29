# Chapter 5 Guideline

This document defines the scope, structure, and boundary rules for Chapter 5.
Chapter 5 covers feature implementation and verification.
It must be read together with the following documents.

- `thesis/guideline.md`
- `thesis/glossary.md`
- `thesis/notation.md`

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

## Section Guidance for Structural Analysis and Execution Ordering

### Role
- This section is the implementation counterpart of the structural analysis theory in Chapter 2.
- It should explain how `syssimx` derives persistent graph metadata from registered components, signal connections, and direct-feedthrough information.
- It should address SR-10-02 and SR-10-03 under UR-10.
- It should also address SR-11-02 under UR-11.
- It should not repeat the conceptual theory of zero-delay graphs, SCCs, and condensed generations.

### Recommended Structure
- Start with a short motivation paragraph.
- State that the section builds on the `System` and connection implementation.
- State the implementation inputs.
- Use a compact metadata table for the fields stored on `System`.
- Place the implementation pipeline figure after the metadata table.
- Place the worked implementation-level example after the graph construction subsection.
- Explain graph construction.
- Explain algebraic loop detection.
- Explain condensation and generation ordering.
- Explain delayed producer post-processing as a `syssimx` scheduling heuristic.
- End with a short description of how initialization and master algorithms consume the metadata.
- Use one focused verification example.

### Verification
- Use one minimal verification example.
- A suitable example is a two-component algebraic loop made from direct-feedthrough gain components.
- The setup should contain `GainA.y -> GainB.u` and `GainB.y -> GainA.u`.
- The expected result is one algebraic loop containing both components.
- The observed metadata should include both full-graph edges, a cyclic zero-delay graph, one SCC in `algebraic_loops`, and one execution generation containing both loop members.
- Do not list every structural-analysis unit test.
- Do not verify IJCSA convergence in this section.
- Solver convergence belongs to the algebraic-loop solver section.

---

## Section Guidance for Master Algorithms

### Role
- This section is the implementation counterpart of the execution-strategy theory in Chapter 2.
- It also builds on the algorithm interface of Chapter 4.
- It should explain how `syssimx` orchestrates one macro step for the continuous master algorithms.
- It should cover `JacobiAlgorithm`, `GaussSeidelAlgorithm`, and `IJCSAAlgorithm`.
- It should exclude hybrid event handling.
- Hybrid execution belongs to the hybrid section.

### Boundary Rules
- Do not repeat the strategy-pattern explanation from Chapter 4.
- Do not restate the conceptual Jacobi and Gauss--Seidel theory from Chapter 2.
- Do not restate the structural-analysis logic from the previous section.
- Do not restate the local Newton procedure from the algebraic-loop section.
- Focus on orchestration logic, data flow, and the differences between the concrete algorithm classes.

### Recommended Structure
- Start with a short opening paragraph.
- State that structural analysis already provides `execution_order` and `algebraic_loops`.
- State that the algebraic-loop section already defines the SCC-local solver.
- Add one short subsection on shared metadata.
- Add one subsection for the Jacobi algorithm.
- Add one subsection for the Gauss--Seidel algorithm.
- Add one subsection for the global IJCSA algorithm.
- End with one short verification subsection.

### Shared Metadata
- All three continuous algorithms consume the same system metadata after `System.initialize()`.
- The relevant items are `execution_order`, `algebraic_loops`, and `_set_inputs_for_generation()`.
- Do not emphasize `execution_idx` in this section.
- It is not part of the main orchestration path of these three algorithms.
- State clearly that the algorithms consume existing metadata rather than rebuilding it.

### Jacobi Algorithm
- Explain the two-phase implementation of `JacobiAlgorithm.step()`.
- First all generations receive staged inputs.
- Then every loop block contained in a generation is solved locally.
- Only after all generations are prepared do the components perform `do_step(t, dt)`.
- State explicitly that later generations do not see fresh outputs from earlier generations within the same macro step.
- State explicitly that the current implementation preserves Jacobi semantics but does not execute the system in parallel.

### Gauss--Seidel Algorithm
- Explain the generation-wise pipeline of `GaussSeidelAlgorithm.step()`.
- For each generation the algorithm stages inputs, solves local loop blocks, and immediately steps the generation.
- Later generations therefore see updated outputs from earlier generations in the same macro step.
- Present this as the key implementation difference to Jacobi.
- Do not re-explain the local IJCSA Newton iteration here.

### Global IJCSA Algorithm
- Explain that `IJCSAAlgorithm.step()` first solves the complete zero-delay interface system through `solve_global_interface_ijcsa()`.
- Mention `collect_global_interface_unknowns()` as the entry point for building the global unknown vector and driver map.
- Explain that the residual is evaluated with frozen component states through `evaluate_outputs()`.
- After convergence the interface values are committed.
- The components then perform their macro steps in the existing `execution_order`.
- State explicitly that the global solve does not eliminate the later stepping order.

### Comparison Guidance
- Use one compact table instead of long repeated prose.
- Good comparison rows are input staging, scope of interface solve, visibility of updated outputs inside a macro step, and possible parallelism.
- Keep this comparison at implementation level.
- Do not repeat the conceptual properties already covered in Chapter 2.

### Figure Guidance
- Do not use three full sequence diagrams in the thesis.
- They are too detailed for the purpose of this section.
- Prefer one compact comparison figure for Jacobi and Gauss--Seidel.
- This figure should show only the order of setting inputs, solving loop blocks, and stepping components.
- Add a separate figure for global IJCSA only if the prose is still unclear.
- If such a figure is used, it should emphasize the two phases of the algorithm.
- The first phase is the global interface solve.
- The second phase is the time stepping of the components.
- The existing PlantUML diagrams can serve as drafting material.
- They should be simplified before inclusion in the thesis.
- Avoid duplicating the theory figures from Chapter 2.

### Verification
- Use one simple direct-feedthrough scenario to compare Jacobi and Gauss--Seidel.
- `docs/03_core_tutorials/02_intermediate/01_comparing_algorithms.ipynb` is a suitable source.
- Verify that Gauss--Seidel uses fresh within-step outputs and reduces the phase lag relative to Jacobi.
- If global IJCSA is included in the verification, use a separate minimal looped scenario or explain briefly why its result matches the local-loop treatment on the chosen example.
- Keep the verification focused on orchestration behavior.
- Do not repeat the algebraic-loop solver verification from the previous section.
- Do not list every algorithm test.
