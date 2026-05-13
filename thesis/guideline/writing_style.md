# Thesis Writing Style

This document defines the preferred writing style for the thesis.
It translates the general Hengl and Gould writing rules into concrete rules for
drafting the `syssimx` thesis.

Use this document together with:

- `README.md`
- `golden_rules_writing_summary.md`
- `glossary.md`
- `notation.md`
- the chapter-specific guideline for the affected chapter

The goal is not to make the thesis sound generic.
The goal is to make the writing clear, precise, consistent, and close to the
author's technical voice.

---

## 1. Core Voice

The thesis voice is:

- direct,
- technical,
- precise,
- restrained,
- evidence-based,
- readable.

The text should sound like a careful engineering thesis, not like marketing
material and not like software API documentation.

Preferred voice:

```text
The hybrid algorithm localizes the first crossing inside the current macro
interval. It then advances the coupled system to the event time and dispatches
the event to the registered listeners.
```

Avoid:

```text
The proposed hybrid methodology facilitates the robust handling of complex
event-related phenomena by means of a sophisticated orchestration mechanism.
```

---

## 2. Sentence Rules

Use short sentences.
Most sentences should express one idea.

Rules:

- Prefer one main statement per sentence.
- Split sentences with more than two commas.
- Avoid sentences joined by colons or semicolons.
- Avoid the pattern "not A; instead B" when the positive statement can be made directly.
- Prefer concrete verbs over abstract nouns.
- Do not hide the subject of the sentence.
- Do not use a long noun chain when a short clause is clearer.

Preferred:

```text
The zero-delay graph may contain directed cycles.
The implementation therefore condenses each strongly connected component before
computing the execution order.
```

Avoid:

```text
Due to the potential occurrence of directed cycles in the zero-delay graph, the
implementation performs a condensation of strongly connected components prior
to the computation of the execution order.
```

Avoid:

```text
The framework is not intended to replace domain-specific simulation tools.
Instead, it provides a common orchestration layer.
```

Better:

```text
The framework provides a common orchestration layer for subsystem models that
remain implemented in their domain-specific simulation tools.
```

---

## 3. Paragraph Rules

A paragraph should have one clear function.
It should not mix setup, result, and interpretation unless it is a short
concluding paragraph.

Common paragraph functions:

- define the local scope,
- explain a mechanism,
- state an assumption,
- describe a figure,
- report a result,
- interpret a result,
- state a limitation,
- transition to the next section.

Preferred paragraph shape:

1. Topic sentence.
2. Two to four supporting sentences.
3. Boundary, consequence, or transition sentence.

Avoid paragraphs that:

- repeat the chapter motivation,
- list methods without explaining their role,
- restate the figure caption,
- mix implementation detail with case-study interpretation,
- end without a clear point.

---

## 4. Word Choice

Use plain technical words when they are accurate.

Prefer:

- uses
- computes
- stores
- detects
- localizes
- advances
- dispatches
- compares
- verifies
- benchmarks
- indicates
- follows from
- is caused by

Avoid unless needed:

- facilitates
- enables in the sense of vague support
- methodology
- paradigm
- manifestation
- elaborate
- sophisticated
- robust without evidence
- novel without stating the actual new contribution
- clearly shows
- it can be observed that
- it should be noted that
- due to the fact that
- in order to when to is enough

Examples:

```text
Poor: It can be observed that the simulation results show convergence.
Better: The error decreased as the macro step size was reduced.
```

```text
Poor: This methodology facilitates heterogeneous simulation workflows.
Better: The framework couples FMU, OpenSim, and FEM components through the same
component interface.
```

---

## 5. Claim Strength

Match the strength of a claim to the evidence.

Use strong statements when the evidence supports them.
Use bounded statements when the evidence is numerical but limited.
Use limitation statements when the evidence is incomplete.

Preferred patterns:

```text
The result verifies the implementation for this minimal scenario.
```

```text
The benchmark shows a speedup of 1.58x for the selected FEM model and contact
scenario.
```

```text
The comparison does not establish physical validation because no experimental
data are used.
```

Avoid:

```text
The framework is validated.
```

Better:

```text
The case study validates the framework workflow for the controlled-pendulum
scenario.
```

---

## 6. Verification, Validation, and Benchmark Wording

Use these terms exactly.

### Verification

Use verification when a result is checked against an expected value,
analytical result, unit test, or numerical reference.

Preferred:

```text
The scenario verifies the closed-loop co-simulation against the monolithic
OpenModelica reference.
```

### Validation

Use validation only for the suitability of the framework workflow in the stated
case-study scope.

Preferred:

```text
The case study validates that the framework workflow combines heterogeneous
components, hybrid events, and runtime model switching in one closed-loop
simulation.
```

### Physical validation

Use physical validation only if experimental data are used.

Preferred:

```text
No physical validation is claimed because the case study does not use
experimental measurements.
```

### Benchmark

Use benchmark for runtime or computational-cost measurements.

Preferred:

```text
The performance scenario is a benchmark of computational cost.
It does not verify correctness on its own.
```

---

## 7. Tense Rules

Use tense consistently.

| Context | Preferred tense | Example |
|---|---|---|
| Established theory | Present | Co-simulation decomposes a system into simulation units. |
| Implemented code behavior | Present | The method builds the zero-delay graph. |
| Case-study setup | Present or past, but stay consistent | The scenario uses the FMU pendulum. |
| Reported results | Past | The error decreased with the macro step size. |
| Discussion conclusions | Present or past, depending on scope | The result shows that the workflow is consistent for this scenario. |

Avoid switching tense inside one paragraph unless the meaning changes.

---

## 8. Chapter-Specific Style

### Chapter 2

Write conceptually.
Do not use code names unless they are needed for orientation.

Preferred:

```text
An algebraic loop arises when simulation units depend on each other through
instantaneous input-output relations.
```

Avoid:

```text
The `System` object stores the detected loop in `algebraic_loops`.
```

### Chapter 5

Write about implementation mechanisms.
Explain data flow, control flow, and design consequences.
Do not document every method.

Preferred:

```text
The structural analysis stores the execution order on the `System` instance.
The master algorithms use this order without recomputing the dependency graph.
```

### Chapter 6

Write about setup, numerical evidence, and interpretation.
Do not re-explain Chapter 5 mechanisms.

Preferred:

```text
The switched configuration follows the reference before the first contact.
The remaining deviation is concentrated in the contact window.
```

### Chapter 7

Synthesize.
Do not introduce new implementation detail or new results.

Preferred:

```text
The case study showed that the framework can combine heterogeneous simulation
tools in one hybrid closed-loop scenario. The result is limited to numerical
verification against model-based references.
```

---

## 9. Figure Style

Figures must help the reader understand the result or mechanism.
Do not include exploratory notebook plots in the thesis.

Rules from the thesis guide:

- Refer to every figure in the text.
- Refer to figures in the correct order.
- Label axes clearly.
- Include units on axes.
- Use panel labels such as (a), (b), and (c) for multi-panel figures.
- Keep labels and symbols readable after scaling.
- Use colors, but keep lines and markers distinguishable in black and white.
- Avoid unnecessary 3D plots, dense grids, and decorative styling.
- Keep figure elements aligned.
- Do not show raw data when a summarized figure communicates the result better.

Preferred figure text:

```text
Figure~\ref{fig:case_baseline_convergence} compares the co-simulation
trajectory with the monolithic reference and reports the step-size dependence
of the angle error.
```

Avoid:

```text
As can clearly be seen from Figure~\ref{fig:case_baseline_convergence}, the
results are very good.
```

---

## 10. Caption Style

Captions should state what is shown and why it matters.
They should not repeat the full surrounding paragraph.

Preferred caption pattern:

```latex
\caption{Step-size convergence of the baseline closed-loop co-simulation.
Panels~(a) and~(b) compare the pendulum angle with the OpenModelica reference.
Panel~(c) reports the maximum and integrated angle errors for decreasing macro
step sizes.}
```

Avoid:

```latex
\caption{The figure shows that the results are good and that the proposed
method works very well for the baseline case.}
```

---

## 11. Table Style

Tables should summarize structured information.
They should not replace interpretation.

Rules from the thesis guide:

- Keep tables simple.
- Avoid data dumping.
- Include units in column headers where appropriate.
- Use concise horizontal rules.
- Do not use decorative backgrounds.
- Use notes below the table only when needed for interpretation.
- Do not use a table for a trend that is better shown as a figure.

Preferred table role:

```text
Table~\ref{tab:case_performance_metrics} summarizes the median runtime,
FEM solver time, and trajectory deviation for the full-FEM and switched
configurations.
```

Avoid tables that list every unit test or every method call unless the table is
the most compact way to support the argument.

---

## 12. Equation Style

Use equations only when they support the explanation.
Do not add equations only to make the text look more formal.

Rules from the thesis guide:

- Explain every variable when it is first used.
- Use displayed equations for important relations.
- Use inline equations for simple expressions.
- Refer to numbered equations as `Equation~\eqref{...}` or `Eqs.~\eqref{...}`
  according to the thesis convention.
- Keep mathematical notation consistent with `notation.md`.
- Do not redefine a symbol locally if it already has a global meaning.

Preferred:

```text
The event indicator is denoted by $\gamma_j$.
An event is detected when $\gamma_j$ changes sign inside the macro interval.
```

Avoid:

```text
Let $q$ be the Cartesian position of the pendulum tip.
```

Reason: `q` is reserved for discrete modes in `notation.md`.

---

## 13. Abstract Style

The abstract must work as a standalone summary.

Rules from the thesis guide and Hengl and Gould:

- Do not cite references in the abstract.
- Define abbreviations if they are unavoidable.
- State the problem.
- State the approach.
- State the key results.
- State the conclusion.
- Include key quantitative results where possible.
- Keep the abstract concise.
- Do not exceed three sentences on any one part of the story.

Preferred abstract pattern:

1. One or two sentences on the problem and gap.
2. One or two sentences on the framework and method.
3. One or two sentences on implementation and case-study evidence.
4. One sentence on the main conclusion and limitation.

---

## 14. Reference Style

Use the citation style configured in the thesis.
The university guide shows numeric references as an example, but the active
LaTeX thesis style is authoritative.

Rules:

- Cite sources where prior work, standards, or external methods are discussed.
- Prefer primary sources for standards and algorithms.
- Do not cite sources for your own implementation results.
- Do not overload result paragraphs with literature comparison.
- Keep literature comparison mostly in introduction, theory, and discussion.

---

## 15. Cross-Reference Style

Use cross-references to avoid repetition.

Preferred:

```latex
The hybrid algorithm uses the event-localization mechanism described in
Section~\ref{sec:impl_hybrid_localization}.
```

Avoid:

```latex
As mentioned before, the algorithm again uses the previously introduced event
localization mechanism, which was described in detail earlier.
```

Rules:

- Use specific labels.
- Do not refer vaguely to "above" or "the previous section" when a label is
  available.
- Avoid chains of repeated references in one sentence.
- Do not use cross-references to compensate for missing explanation.

---

## 16. Transition Style

Transitions should state why the next section follows.
They should not summarize the whole previous section again.

Preferred:

```text
The structural metadata defines the order in which components are evaluated.
The next section explains how algebraic loops inside this order are resolved.
```

Avoid:

```text
After having introduced all the important aspects of the structural analysis,
which were necessary to understand the following parts, the next section will
now deal with algebraic loops.
```

---

## 17. Limitation Style

Limitations should be stated directly.
Do not hide them behind weak wording.

Preferred:

```text
The result does not establish physical validation because no experimental data
are used.
```

```text
The switched FEM state is reconstructed from rigid-body variables.
It therefore cannot preserve deformation history accumulated before the switch.
```

Avoid:

```text
It should be kept in mind that the result might not fully represent all
possible physical effects.
```

---

## 18. Common Rewrite Patterns

| Avoid | Prefer |
|---|---|
| It can be observed that the error decreases. | The error decreased. |
| This section deals with the implementation of... | This section describes how ... is implemented. |
| The proposed methodology facilitates... | The framework uses... |
| Due to the fact that... | Because... |
| In order to compute... | To compute... |
| The results are shown in Figure... | Figure... compares... |
| It is important to mention that... | State the point directly. |
| This proves that... | This verifies... for the tested scenario. |
| This validates the model. | This verifies the numerical result against the reference. |
| The results are acceptable. | The maximum angle error was ... rad. |

---

## 19. Agent Checklist Before Returning Draft Prose

Before returning a thesis draft, check:

- Does the paragraph belong in this chapter?
- Does it use the glossary terms correctly?
- Does it use the notation correctly?
- Does it make a claim?
- Is the claim supported by evidence?
- Is verification, validation, and benchmarking terminology correct?
- Are sentences short enough?
- Are vague phrases removed?
- Are figure and table references specific?
- Is the paragraph LaTeX-ready if the user asked for insertable text?

If one of these checks fails, fix the draft before returning it.

---

## 20. Short Rule

Write naturally first, then make the text shorter, clearer, and more precise.
Every paragraph must either prepare, explain, show, interpret, or conclude.
