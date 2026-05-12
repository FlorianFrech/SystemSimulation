# Chapter 7 Guideline

This document defines the scope, structure, and boundary rules for Chapter 7.
Chapter 7 closes the thesis with discussion, limitations, conclusions, and outlook.
It must be read together with the following documents.

- `README.md`
- `thesis_concept.md`
- `golden_rules_writing_summary.md`
- `writing_style.md`
- `glossary.md`
- `notation.md`
- `claims_and_evidence.md`
- `ch5_implementation.md`
- `ch6_case_study.md`

---

## Role of Chapter 7

Chapter 7 is the synthesis chapter.
It must not become another implementation chapter and it must not repeat the case-study results in detail.
Its role is to answer what the thesis demonstrated, what the evidence supports, where the limits are, and what should be done next.

Chapter 7 must explicitly close the loop to the introduction.
It should refer back to the research gap, contribution, research questions, and objectives from Chapter 1.
It should not repeat the full motivation.
It should state which research questions were answered, how they were answered, and which limitations remain.

Use the Hengl and Gould writing rules directly.
The chapter must answer the research objective, interpret the results, explain discrepancies, state limitations, and make clear conclusions.
It must be readable as the final argument of the thesis.

### Core Message

The chapter should carry this message.

```text
The thesis demonstrates that heterogeneous hybrid co-simulation with runtime model switching can be implemented in a unified Python framework and applied to a controlled-pendulum case study.
The implementation-level verification confirms the core framework mechanisms.
The case study verifies selected numerical results against monolithic OpenModelica references and validates the combined workflow.
The performance benchmark shows that activating the FEM model only near contact can reduce computational cost.
These claims are bounded by the selected models, solver settings, and lack of experimental validation.
```

Do not expand this message into a new motivation section.
Chapter 1 already explains why the topic matters.

---

## Recommended Chapter Structure

Keep the current chapter structure.

```latex
\section{Discussion of Results}
\section{Limitations}
\section{Conclusions}
\section{Outlook and Future Work}
```

The recommended total length is approximately 5 to 8 pages.
If the chapter becomes longer, remove repeated result descriptions before shortening the limitations.

---

## 7.1 Discussion of Results

### Function

This section interprets the thesis-level evidence.
It should connect the implementation results from Chapter 5 with the case-study results from Chapter 6.
It should not restate all figures and tables.

### Paragraph Order

Use this paragraph order.

1. Return to the research gap and actual contribution.
2. Answer RQ1: heterogeneous integration through the shared component interface.
3. Answer RQ2: structural analysis, algebraic loops, and master-algorithm orchestration.
4. Answer RQ3: hybrid event handling and dense-time behavior.
5. Answer RQ4: runtime model switching and state projection.
6. Answer RQ5: controlled-pendulum case-study interpretation and benchmark evidence.
7. Interpret the performance result.
8. Relate the result to the state of the art without turning the section into a literature review.

### Required Claims

State these claims if the final results support them.

- The framework provides one component interface for FMU, OpenSim, FEM, and multi-model components.
- The structural-analysis metadata enables initialization, execution ordering, algebraic-loop detection, and master-algorithm execution.
- The hybrid algorithm localizes and handles events across coupled components.
- The multi-model component keeps the external plant interface fixed while changing the active internal model.
- The baseline case study shows convergence toward the monolithic OpenModelica reference as the macro step size is refined.
- The contact case study shows that heterogeneous plant models, hybrid contact events, PID reset, and model switching can be combined in one closed-loop scenario.
- The performance benchmark shows a runtime benefit when the FEM model is restricted to the contact-relevant part of the trajectory.

### Research Question Closure

Chapter 7 should contain a compact paragraph or table that maps the research
questions from Chapter 1 to the evidence in Chapters 5 and 6.
Use this mapping as the starting point.

| Research question | Answer in Chapter 7 |
|---|---|
| RQ1: unified representation of heterogeneous models | Answer through the component abstraction, port system, and FMU/OpenSim/FEM wrappers |
| RQ2: dependency analysis and execution order | Answer through structural analysis, direct-feedthrough metadata, SCC detection, condensation, and algebraic-loop handling |
| RQ3: hybrid phenomena | Answer through event indicators, trial stepping, event localization, rollback, dense-time event handling, and PID-reset/contact scenarios |
| RQ4: runtime switching between alternative models | Answer through the `MultiComponent` and `MasterPendulum`, including state adaptation and switching limitations |
| RQ5: reproduction of representative system behavior | Answer through the controlled-pendulum scenarios, OpenModelica reference comparisons, and runtime benchmark |

Do not repeat all implementation details while answering these questions.
State the answer, cite the evidence, and explain the remaining boundary.

### Required Boundaries

State these boundaries clearly.

- The case study is numerical verification and workflow validation.
- The case study is not experimental physical validation.
- The OpenModelica model is a numerical reference, not ground truth.
- The FEM contact model approximates rigid contact by stiff compliant contact.
- The runtime speedup is scenario-specific.

### Citation Guidance

Use citations sparingly.
Do not create a broad literature comparison in this section.
Use citations only to interpret the observed behavior.

Recommended citation targets.

- Co-simulation accuracy and macro-step dependence: `\cite{gomes_co-simulation_2019, arnold_error_2013, kubler_two_2000}`
- Hybrid co-simulation and event handling: `\cite{broman_requirements_2015, StepRevision_Cremona, cremona_hybrid_2019}`
- Algebraic loops and implicit coupling: `\cite{sicklinger_interface_2014, schweizer_implicit_2016}`
- FMI-based interoperability: `\cite{FMI2.0, FMI3.0}`
- Multi-fidelity and switched-fidelity simulation: `\cite{peherstorfer_survey_2018, fernandez-godino_review_2023, Choi2017, williams_switched-fidelity_2014}`

### What Not To Do

- Do not repeat the complete scenario setup from Chapter 6.
- Do not introduce new plots or new metrics.
- Do not re-explain the algorithms from Chapter 5.
- Do not compare against other frameworks unless the same benchmark was actually run.
- Do not claim general speedup from one controlled-pendulum benchmark.

---

## 7.2 Limitations

### Function

This section states the limits of the thesis openly.
It should separate framework limitations from modeling limitations.
This is required by the Hengl and Gould rule to be self-critical and not hide unexpected findings.

### Recommended Structure

Use short paragraphs with clear topics.

1. Validation boundary.
2. FMI and backend capability limitations.
3. Numerical and solver limitations.
4. Hybrid-time representation limitations.
5. Algebraic-loop solver limitations.
6. Modeling limitations of contact.
7. Runtime switching and state-projection limitations.
8. Scalability and performance limitations.
9. Tool-wrapper limitations.

### Required Limitation Points

Include these points unless later results invalidate them.

- No experimental validation was performed.
- The monolithic OpenModelica reference verifies numerical consistency with another model formulation.
- The reference does not establish physical correctness of the pendulum or contact model.
- The FEM contact formulation uses stiff compliant contact to approximate rigid impact.
- Switching into FEM reconstructs the FEM state from reduced rigid-body variables.
- The switched FEM state cannot preserve deformation history that was never simulated.
- Performance results depend on the FEM mesh, solver tolerances, macro step size, switching thresholds, and hardware.
- The OpenSim integration path is demonstrated on a simple pendulum and not on a full musculoskeletal model.
- The OpenSim wrapper covers the main functionality required by the case study, but it is not a general-purpose OpenSim co-simulation interface.
- The FEM integration is model-specific and does not yet provide a generic NGSolve wrapper comparable to the FMU wrapper.
- The implementation is constrained by the capabilities exposed by the exported FMUs.
- The thesis uses FMI 2.0 Co-Simulation FMUs. It does not implement FMI 3.0 clocks, scheduled execution, or a full FMI 3.0 hybrid co-simulation workflow.
- Some FMI capabilities that are useful for hybrid co-simulation, such as complete rollback support, are optional or backend-dependent.
- OpenModelica FMU exports used in the thesis therefore limit which hybrid mechanisms can be realized through FMUs alone.
- No adaptive macro-step-size or error-controlled master algorithm is implemented.
- A general adaptive master algorithm would require rollback or state reconstruction support for all components that may need to be re-stepped.
- Dense time is represented with floating-point physical time and an integer microstep index.
- More rigorous hybrid semantics would represent physical time on an integer tick grid or another exactly comparable time base to avoid floating-point equality issues.
- The algebraic-loop implementation is SCC-local and practical for the tested scenarios, but it is not a full optimized IJCSA implementation.
- The current loop solver does not reuse a constant Jacobian across iterations or time steps.
- Reusing the Jacobian could reduce cost for loops whose local linearization remains unchanged.
- Parallel execution of independent generations is not implemented.
- Large-scale scalability was not systematically benchmarked.

### Limitation Evaluation Notes

Use these points carefully.
They are valid limitations, but they should not all be written with the same weight.

- The FMI and wrapper limitations are important because they bound framework generality.
- The missing adaptive master algorithm is important because it affects accuracy control.
- The dense-time floating-point limitation is technically important, but it should be stated briefly and linked to future work.
- The algebraic-loop Jacobian limitation is an optimization and completeness limitation, not a correctness failure for the tested examples.
- Missing parallel execution is a scalability limitation, not a conceptual limitation of the framework architecture.

### Wording Rule

Use direct wording.

Prefer:

```latex
This comparison verifies numerical consistency with the selected reference model.
It does not validate the physical contact law.
```

Avoid:

```latex
It may be said that the comparison could be interpreted as validation.
```

---

## 7.3 Conclusions

### Function

This section answers the thesis objective directly.
It should be short and assertive.
It should not introduce new details, new citations, or new evidence.

### Recommended Paragraph Order

Use this paragraph order.

1. Restate the problem in one sentence.
2. State the implemented solution.
3. State what was verified in Chapter 5.
4. State what was shown in Chapter 6.
5. State the final thesis claim.

### Required Conclusion Claims

Use claims at this level of strength.

- The thesis developed `syssimx` as a framework for heterogeneous hybrid co-simulation.
- The framework integrates standardized FMU models and tool-specific OpenSim and FEM models through a shared component abstraction.
- The implementation supports structural analysis, algebraic-loop resolution, continuous master algorithms, hybrid event handling, and runtime model switching.
- The controlled-pendulum case study demonstrates the combined use of these features.
- The results support the feasibility of the framework for the tested class of heterogeneous hybrid simulation scenarios.

### Claim Boundaries

Do not claim the following.

- Do not claim universal numerical stability.
- Do not claim physical validation of the contact model.
- Do not claim general speedup for all multi-fidelity simulations.
- Do not claim complete FMI 3.0 hybrid co-simulation support unless it was implemented.
- Do not claim full musculoskeletal validation from the OpenSim pendulum wrapper.

### Possible Final Sentence

Use this as a candidate final sentence.

```latex
The main contribution of the thesis is therefore not a new pendulum model, but an implementation architecture that combines heterogeneous simulation tools, hybrid event handling, and runtime fidelity switching in one controlled co-simulation workflow.
```

---

## 7.4 Outlook and Future Work

### Function

This section turns the limitations into concrete future work.
It should not reopen the thesis.
Use only realistic extensions.

### Recommended Future Work Topics

Use a small selection of these topics.

- Experimental validation with a physical pendulum or comparable laboratory setup.
- Improved state projection for switching into FEM models.
- Adaptive switching thresholds based on error indicators or contact prediction.
- Adaptive and error-controlled master algorithms with rollback-aware step rejection.
- Larger FEM models and larger coupled systems for scalability studies.
- Parallel execution of independent execution generations.
- More robust rollback support for additional backend wrappers.
- Broader OpenSim examples with biomechanical models and muscle actuation.
- FMI 3.0 clocks and scheduled execution for stronger support of sampled and event-driven behavior.
- Exact or tick-based time representation for dense-time event ordering.
- Optimized algebraic-loop solvers with Jacobian reuse when the local loop structure is constant.
- A more generic FEM backend wrapper that separates NGSolve-specific model code from the shared component interface.
- Automated benchmark suite for co-simulation accuracy, event timing, and runtime cost.
- More user-facing diagnostics for structural analysis, algebraic loops, and switching decisions.

### What Not To Add

- Do not add speculative features that are not connected to a limitation.
- Do not add a long roadmap for software engineering cleanup.
- Do not promise full industrial validation without data.
- Do not suggest replacing the whole framework.

---

## Relationship to Previous Chapters

### Chapter 5

Chapter 5 provides implementation evidence.
Chapter 7 should refer to it only at feature level.

Good:

```latex
The implementation verified the individual orchestration mechanisms before they were combined in the case study.
```

Avoid:

```latex
The method `_detect_crossings()` first stores snapshots and then performs trial steps.
```

### Chapter 6

Chapter 6 provides system-level evidence.
Chapter 7 should use Chapter 6 to support conclusions, not to repeat scenarios.

Good:

```latex
The baseline scenario confirmed the expected reduction of trajectory error with smaller macro step sizes.
```

Avoid:

```latex
The baseline scenario used the setpoint generator, PID controller, drive, and FMU pendulum with sensor sampling disabled.
```

---

## Results Versus Discussion Boundary

Follow the Hengl and Gould distinction.

Chapter 6 results should present what was observed.
Chapter 7 should explain what the observations mean.

Examples.

- Chapter 6 states the measured error and speedup.
- Chapter 7 explains why the speedup is smaller than the FEM-solver speedup.
- Chapter 6 states that contact-window deviations remain.
- Chapter 7 explains that the deviations follow from compliant contact and state projection.
- Chapter 6 states that no experimental validation is claimed.
- Chapter 7 explains what this means for the generality of the conclusions.

---

## Style Rules for Chapter 7

- Use strong statements when the evidence supports them.
- Use cautious statements when the evidence is scenario-specific.
- Keep sentences short.
- Avoid new terminology.
- Avoid new equations.
- Avoid new figures unless a one-table summary of contributions and evidence is truly useful.
- Do not use screenshots.
- Do not use implementation method names unless they are essential.
- Do not write a chronological project summary.
- Do not start every paragraph with "This thesis".
- Keep the distinction between verification, validation, and benchmark.

---

## Optional Summary Table

A compact table may be useful if Chapter 7 needs a clear synthesis.
Use at most one table.

Suggested columns.

- Thesis objective or requirement.
- Framework feature.
- Evidence.
- Remaining limitation.

Use the table only if it replaces repeated prose.
Do not add it if the chapter is already clear.

---

## Drafting Checklist

Before drafting Chapter 7, check the following.

- [ ] Are all Chapter 6 result values final?
- [ ] Are placeholder timing values replaced?
- [ ] Are the three claim types kept separate?
- [ ] Numerical verification against OpenModelica.
- [ ] Workflow validation of the framework.
- [ ] Runtime benchmark for performance.
- [ ] Are limitations separated into implementation, modeling, validation, and performance limits?
- [ ] Are the conclusions linked to the thesis objective?
- [ ] Are citations used only to support interpretation?
- [ ] Are no new technical details introduced?
- [ ] Does the final paragraph state the main contribution directly?

---

## Common Failure Modes

- Repeating Chapter 6 results instead of interpreting them.
- Hiding the lack of experimental validation.
- Overstating the performance benchmark.
- Treating OpenModelica as physical ground truth.
- Discussing implementation methods instead of thesis-level consequences.
- Adding too many future-work items.
- Ending with a weak or generic final sentence.

---

## Short Working Rule

Use this rule while writing Chapter 7.

```text
State what was demonstrated, defend it with the evidence already shown, state the limits, and end with the contribution.
```
