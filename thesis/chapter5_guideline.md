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

### Implementation Inputs
- Registered components from `System.components`.
- Signal connections from `System.connections`.
- Direct-feedthrough metadata from each component.
- Active output usage derived from outgoing signal connections.

### Stored Metadata
- Prefer a table with the columns `Attribute`, `Produced by`, and `Purpose`.
- Include `graph`, `_dag`, `_incoming_by_dst`, `_input_sources`, `algebraic_loops`, `_scc_index`, `execution_order`, and `execution_idx`.
- Describe `_dag` as the zero-delay graph.
- Do not call `_dag` a DAG before condensation.
- It may contain cycles before algebraic loop condensation.
- The attribute names in this table are the tags used by the worked implementation-level example.

### Graph Construction
- Explain that `build_graphs()` first clears cached structural metadata.
- Explain that all registered components become nodes of both graph representations.
- Explain that every registered signal connection becomes an annotated edge of the full connection graph.
- Explain that `_incoming_by_dst` and `_input_sources` are populated for input propagation.
- Describe the multiple-driver check as a defensive graph-construction guard.
- The primary single-assignment check belongs to the `System and Connections` section.
- Explain the active-output filter explicitly.
- State that a zero-delay edge is added only when the connected destination input affects an output that is used by a downstream connection.

### Algebraic Loops and Execution Order
- State that SCCs are computed on the zero-delay graph.
- Store multi-node SCCs as algebraic loops.
- Treat a self-loop as a one-component algebraic loop.
- Condense the zero-delay graph after loop detection.
- Compute topological generations on the condensed graph.
- Expand each condensed node back to component names.
- Store the result in `execution_order` and `execution_idx`.

### Delayed Producers
- Keep this part short.
- State that delayed producer handling is a `syssimx` scheduling choice.
- Do not present it as a general property of co-simulation theory.
- Explain only that components which feed zero-delay structure through delayed paths can be moved to a final generation.

### Figure Guidance
- The section uses two complementary figures.
- The first is the implementation pipeline diagram.
- Place it after the stored metadata table and before graph construction.
- The pipeline figure should show inputs, `build_graphs()`, `compute_execution_order()`, and stored outputs.
- The inputs should be components, connections, and direct-feedthrough metadata.
- The outputs should include the full graph, zero-delay graph, input lookup maps, algebraic loops, and execution order.
- The pipeline figure should show that later initialization and master algorithms consume the stored metadata.
- The second figure is a worked implementation-level example of the same scenario used in the Chapter 2 structural-analysis figure.
- The reuse is deliberate, so that the reader transfers intuition from Chapter 2 to the implementation level.
- The caption must state explicitly that this is the same scenario as the Chapter 2 figure, refined to the implementation level.
- The worked example must expose implementation artifacts that are not visible in the Chapter 2 figure.
- Do not duplicate the Chapter 2 conceptual structural-analysis figure.
- Do not create another conceptual dependency graph for this section.
- The conceptual dependency graph belongs to Chapter 2.

#### Worked Example: Required Implementation Details
- Draw edges at port level, not at component level, in the panels that represent port-level structures.
- Label every port-level edge with the concrete source and destination port names.
- Render the direct-feedthrough map of each component as a literal dictionary next to the component node.
- Include at least one component whose direct-feedthrough dictionary is empty.
- The scenario must be constructed so that this component is detected as a delayed producer by `is_delayed_producer()` and relocated to the final generation by `move_delayed_producers_to_last_generation()`.
- Without a visible delayed-producer relocation, the worked example does not earn its place in the section.
- Tag each panel with the name of the stored metadata attribute it corresponds to.
- Example tags are `graph`, `_dag`, `algebraic_loops`, `execution_order`, and `execution_idx`.
- Render `execution_order` and `execution_idx` as literal data, not only as a colored generation diagram.

#### Worked Example: Panel Plan
- Panel (a) shows the input data.
- Panel (a) contains the component set, the connection list, and the direct-feedthrough dictionaries.
- Panel (a) must include at least one component with an empty direct-feedthrough dictionary.
- Panel (a) must show at least one connection that enters the no-feedthrough component and one connection that leaves it toward a zero-delay node, so that the delayed-producer criterion of `is_delayed_producer()` is satisfied.
- Panel (b1) shows the full connection graph `graph`.
- Panel (b1) uses port-labeled edges.
- Panel (b1) must preserve parallel edges, because `graph` is a `MultiDiGraph`.
- Panel (b2) shows the zero-delay graph `_dag` after feedthrough composition and the active-output filter.
- Edges that appear in (b1) but are absent in (b2) are the teaching moment and must remain visible as ghosted edges.
- Ghosted edges include those dropped because the receiving component has no feedthrough and those dropped because the contributing output is inactive.
- The no-feedthrough component must be rendered in a visually distinct style in (b2), so the reader sees that it is not part of `_dag` even though it remains a registered component.
- Panel (b2) component-level edges do not carry port-pair labels, because `_dag` is a `DiGraph` and port information has been abstracted away.
- Panel (b2) may annotate a coalesced edge that represents multiple parallel connections from (b1) with a multiplicity hint.
- Panel (c) highlights the SCC on `_dag` and tags it as `algebraic_loops`.
- Panel (c) may be merged into panel (b2) by drawing the SCC boundary directly on `_dag` if space is tight.
- Panels (b1) and (b2) must never be merged.
- Panel (d) shows the condensed graph with topological generations.
- Panel (d) must render two successive states of `execution_order`: the result of plain topological generations on the condensed graph, and the result after `move_delayed_producers_to_last_generation()`.
- The transition between the two states must be labeled with the post-processing step, so the reader sees the relocation as an explicit operation rather than an artifact of topological sorting.
- Panel (d) additionally renders the final `execution_order` and `execution_idx` as literal data structures.

#### Figure Ordering and Placement
- Place the pipeline figure before the worked example.
- Place the pipeline figure after the stored metadata table and before the graph construction subsection.
- Place the worked example after the graph construction subsection.
- The worked example may be referenced from subsequent subsections on algebraic loop detection and execution order.
- Do not place the worked example before the pipeline figure.


### Verification
- Use one minimal verification example.
- A suitable example is a two-component algebraic loop made from direct-feedthrough gain components.
- The setup should contain `GainA.y -> GainB.u` and `GainB.y -> GainA.u`.
- The expected result is one algebraic loop containing both components.
- The observed metadata should include both full-graph edges, a cyclic zero-delay graph, one SCC in `algebraic_loops`, and one execution generation containing both loop members.
- Do not list every structural-analysis unit test.
- Do not verify IJCSA convergence in this section.
- Solver convergence belongs to the algebraic-loop solver section.
