# Chapter 6 Guideline

This document defines the scope, structure, and boundary rules for Chapter 6.
Chapter 6 covers the controlled-pendulum case study.
It must be read together with the following documents.

- `thesis/guideline.md`
- `research/theory/glossary.md`
- `research/theory/notation.md`
- `thesis/golden_rules_writing_summary.md`

---

## Role of Chapter 6

Chapter 6 is the system-level case-study chapter.
It must not become another implementation chapter.
Its role is to show that the framework features from Chapter 5 work together on a realistic closed-loop system.

The controlled pendulum is used to verify selected co-simulation results against monolithic OpenModelica reference simulations and to validate that the framework workflow combines heterogeneous tools, hybrid events, and runtime model switching.

The chapter is approximately 12 to 15 pages.

### Verification and Validation Terminology

- Comparing `syssimx` co-simulation results with a monolithic OpenModelica model is **numerical verification** against a reference solution.
- Showing that the controlled-pendulum workflow combines FMUs, OpenSim, FEM, structural analysis, hybrid events, and model switching is **case-study validation** of the framework concept.
- Reporting wall-clock time and FEM-active time for switched versus full-FEM execution is a **benchmark** of computational cost. It does not establish correctness on its own.
- Showing that the FEM contact model represents real physical contact would require experimental data. Without such data, FEM contact results are described as a numerical approximation.

This claim boundary must appear at the start of §6.1 verbatim.

```latex
The case study verifies selected co-simulation results against monolithic OpenModelica reference simulations and validates the framework workflow on a controlled pendulum system.
Performance results are reported as benchmarks.
No experimental validation is claimed.
```

Use this exact wording so the boundary is unambiguous.

---

## Case-Study Motivation

Chapter 1 motivates the need for a representative heterogeneous hybrid system simulation case.
It does not fully justify the controlled pendulum itself.
Section §6.1 must therefore give a short case-specific justification.

Use Chapter 1 as the motivation anchor.
Do not repeat the full motivation from Chapter 1.
Explain only why the controlled pendulum is a suitable validation object for the framework.

The controlled pendulum is suitable because it is simple enough to interpret and rich enough to exercise the framework features.
It contains closed-loop control, sensor feedback, actuator dynamics, contact, strong coupling, and alternative plant models with different fidelity levels.
It also permits a monolithic OpenModelica reference for numerical verification.

§6.1 states the **objective** of the case study, namely which features of the framework are validated together and which results are verified numerically against the monolithic reference.

---

## Recommended Chapter Structure

### 6.1 Case-Study Objective and Validation Strategy

- Reference Chapter 1 for the case-study motivation.
- State the case-study objective.
- Insert the verification and validation claim boundary block verbatim.
- Define the role of the OpenModelica monolithic reference.
- State that experimental physical validation is not claimed.
- Introduce the central convergence idea.

```latex
The controlled pendulum is chosen because it is simple enough to interpret but rich enough to exercise the main framework features.
It combines closed-loop control, sensor feedback, actuator dynamics, contact, strong coupling, and alternative plant models with different fidelity levels.
It also permits a monolithic OpenModelica reference model.
This makes it suitable for numerical verification against a reference solution and for workflow validation of the heterogeneous co-simulation framework.
```

### 6.2 Controlled Pendulum System

- Introduce the closed-loop architecture.
- Show one system diagram with setpoint, sensor, controller, drive, and pendulum.
- Define the main signals.
- Define the **port-level plant interface** that all pendulum variants must satisfy.
  - Inputs: torque.
  - Outputs: angle, angular velocity, angular acceleration, contact event.
- Keep component details short.

The port-level interface defined here is the **single contract** that all pendulum variants share.
It is referenced from §6.3 and from each scenario in §6.5 and is not redefined elsewhere.

### 6.3 Pendulum Model Variants

This subsection only describes the **internal model** of each variant.
The shared port-level interface is defined in §6.2 and is not repeated here.

- §6.3.1 FMU pendulum: rigid-body Modelica plant exported for co-simulation.
- §6.3.2 OpenSim pendulum: musculoskeletal-tool integration path.
- §6.3.3 FEM pendulum: deformable high-fidelity model. See *FEM Pendulum Scope* below.
- §6.3.4 `MasterPendulum`: multi-model plant wrapper.

Do not repeat Chapter 5 wrapper implementation details.

### 6.4 Reference Model and Evaluation Metrics

This subsection defines all standards used in §6.5 once and for all.
No metric is redefined in §6.5.

**Reference solver.**
The monolithic OpenModelica model is integrated with the DASSL solver.
State the absolute tolerance, the relative tolerance, the integration order, and the maximum step size.
Example wording.

```latex
The reference uses the DASSL solver with absolute tolerance 1e-8, relative tolerance 1e-6, integration order up to 5, and maximum step size 1e-3 s.
```

**Compared variables.**

- Pendulum angle.
- Drive torque.
- Event time for contact-related scenarios.
- Wall-clock execution time for the performance scenario.

**Error metrics.**

- The headline metric for trajectory comparisons is the $L^\infty$ error of the pendulum angle over the simulated horizon.
- The $L^2$ error is reported in addition because it differentiates schemes that have the same worst-case deviation but different integrated error.
- The headline metric for event timing is the absolute event-time error in seconds.

The two trajectory metrics are complementary.
$L^\infty$ identifies worst-case deviations.
$L^2$ measures integrated deviation across the trajectory.

**Convergence criterion.**
Numerical verification is established by reducing the macro step size and showing that the trajectory error decreases toward the reference within the stated tolerances.

**Acceptance criterion for the performance scenario.**
The switched configuration is acceptable if the angle $L^\infty$ error of the switched configuration against the full-FEM reference does not exceed the angle $L^\infty$ error of the rigid-body model against the same reference.
The benefit is reported as the wall-clock speedup and the reduction of FEM-active time relative to full FEM.

### 6.5 Validation Scenarios

Each scenario states the setup, the expected behavior, the observed result, and the conclusion.
Each subsection title carries its **claim tag** in parentheses.

#### Required scenarios

**6.5.1 Baseline closed loop without contact (numerical verification).**

- Claim. Numerical verification of the FMU-only closed-loop system against the monolithic OpenModelica reference.
- Convergence study with at least three macro step sizes.
- This is the cleanest verification setup and serves as the reference convergence rate for the optional variants.

**6.5.2 Multi-model switching with FEM contact and event handling (numerical verification + workflow validation).**

- Claim. Numerical verification of the switched plant against the monolithic OpenModelica rigid-contact reference for the angle trajectory and the contact-event time. Workflow validation that the framework combines FMU, FEM, structural analysis, hybrid events, model switching, and PID reset.
- This scenario subsumes the previous standalone rigid-contact scenario. The PID-reset behavior is part of the contact event handling.

**6.5.3 Runtime performance of full FEM versus switched FEM usage (benchmark).**

- Claim. Benchmark of computational cost. Correctness of the same configuration is established by Scenario 6.5.2.
- Compare full-FEM execution and `MasterPendulum` switching against the same input trajectory.
- Apply the acceptance criterion of §6.4.

#### Optional scenarios

These are **variants of the baseline** that isolate one feature.
The baseline itself is kept simple. The variants demonstrate one extra feature each so that any deviation against the reference is attributable.

**6.5.A Sensor sampling and quantization (numerical verification, optional).**

- Claim. Numerical verification of the FMU-only closed loop with discrete-time sensor and decoder against the corresponding monolithic OpenModelica variant.
- Variant of 6.5.1 with the quantized sensor enabled.

**6.5.B Strongly coupled drive and pendulum with algebraic loop (numerical verification, optional).**

- Claim. Numerical verification that the SCC-local IJCSA solver produces the same closed-loop trajectory as the monolithic OpenModelica reference under strong coupling.
- Variant of 6.5.1 with feedthrough coupling enabled in the drive-plant connection.

#### Removed from the previous draft

- Standalone rigid-contact scenario. Subsumed by 6.5.2. The multi-model switching scenario contains the same discrete event and the same PID-reset behavior. A separate scenario would duplicate evidence.

### 6.6 Discussion of Results

Per-scenario interpretation.

- Interpret each scenario in the order it appears in §6.5.
- For required scenarios, discuss where co-simulation converges to the monolithic reference and where modeling differences remain.
- Discuss the consequences of approximating rigid contact with stiff compliant FEM contact in 6.5.2.
- Discuss the tradeoff between accuracy and runtime in 6.5.3.
- Keep broader framework limitations for Chapter 7.

### 6.7 Case-Study Summary

Chapter-level synthesis.

- State which framework features were validated together.
- State the main numerical verification result.
- State the main performance result of model switching.
- Prepare the transition to the conclusion chapter.

If §6.7 ends up restating §6.6, drop §6.7 and let the last paragraph of §6.6 carry the transition.

---

## FEM Pendulum Scope

The FEM pendulum is the mathematically most advanced pendulum model in the case study.
It receives more explanation than the rigid pendulum variants.
The subsection §6.3.3 stays focused on the case-study role.

§6.3.3 is budgeted at approximately 1.5 to 2 pages.

Include the following topics.

- Geometry and hinge constraint.
- Neo-Hookean material choice.
- Newmark time integration.
- Torque application.
- Compliant contact boundary.
- Rigid-body output mapping to `theta`, `omega`, and `alpha`.
- Reason for using high stiffness to approximate rigid contact.

Do not include the following details unless they are needed for interpreting a result.

- Full variational derivation.
- Detailed mesh construction.
- Full NGSolve implementation detail.
- Long material-law derivations.
- General FEM theory that is not used in the result discussion.

The chapter may mention that switching between FEM and rigid-body models is a projection.
FEM deformation states are not fully representable in the rigid-body models.
This modeling consequence is discussed in §6.6 for Scenario 6.5.2.

---

## Scenario Priorities

The required and optional scenario lists in §6.5 are **binding**.

If the chapter exceeds 15 pages, drop content in this order.

1. Optional scenario 6.5.B (algebraic loop).
2. Optional scenario 6.5.A (quantization).
3. Reduce the 6.5.1 convergence study from four macro step sizes to three.

Do not drop 6.5.2 or 6.5.3.
Do not reduce the 6.5.1 convergence study below three step sizes.

---

## Performance Evaluation for Fidelity Switching

Scenario 6.5.3 evaluates whether the multi-model plant reduces the cost of the high-fidelity FEM model without changing the relevant contact response.

**Comparison setup.**

- Run the same contact scenario with the FEM pendulum active for the full trajectory.
- Run the same scenario with `MasterPendulum` switching to FEM only near contact.
- Use the same macro step size, tolerances, input trajectory, and contact parameters.

**Reported metrics.**

- Total wall-clock time.
- Number of FEM steps or accumulated FEM-active time.
- Angle $L^\infty$ error of the switched configuration against the full-FEM reference.
- Angle $L^\infty$ error of the rigid-body model against the same full-FEM reference, as a lower-quality bound.

**Acceptance criterion.**
The switched configuration is acceptable if its angle $L^\infty$ error against the full-FEM reference is at most the angle $L^\infty$ error of the rigid-body model against the same reference.
The benefit is reported as the wall-clock speedup and the reduction of FEM-active time.

**Figure shape.**
One compact figure with two panels.

- Panel A. Trajectory or contact-window comparison for full FEM, switched, and rigid-body.
- Panel B. Wall-clock time bars or normalized speedup against the rigid-body lower bound.

**Required honest reporting.**
If switching introduces visible discontinuities or contact artifacts, state this explicitly in §6.6.

Suggested wording for the §6.5.3 introduction.

```latex
The performance comparison evaluates whether the multi-model plant can reduce the cost of the high-fidelity FEM model without changing the relevant contact response.
The switched configuration uses the FEM model only inside the contact window and otherwise advances the rigid-body model.
The comparison therefore measures both numerical deviation and wall-clock runtime.
```

---

## Reproducibility

The case-study scenarios are reproducible from the public `SystemSimulation` repository.

- The Jupyter notebooks under `docs/05_case_study/` contain the exact scenario configurations used in Chapter 6.
- The OpenModelica reference models are stored under `demos/ControlledPendulum/src/modelica/`.
- The reference solutions are exported once and loaded by the Chapter 6 figures so that recompilation does not require an OpenModelica installation.
- Reproducing the reference solutions from the `.mo` files requires OpenModelica. State the version used.

State this once at the start of §6.4.
Do not repeat repository paths in §6.5.

---

## Boundary Rules

- Do not repeat Chapter 5 implementation details.
- Do not explain `System`, `Connection`, structural analysis, IJCSA, or hybrid event handling again.
- Refer to Chapter 5 for implementation mechanisms.
- Focus on setup, reference comparison, numerical results, and interpretation.
- Do not claim physical validation unless experimental data is used.
- Each scenario is self-contained at the **scenario** level (setup, result, conclusion in one place).
- Each scenario is **not** self-contained at the **mechanism** level (defer mechanism to Chapter 5).
- Avoid long notebook-style procedure descriptions.
- Do not include screenshots from notebooks unless they are converted into thesis-ready figures.
- Prefer a small number of high-quality figures over many exploratory plots.

---

## Figure Guidance

Each recommended figure is tagged with the scenario it serves.

| Figure | Scenario | Required? |
|---|---|---|
| Closed-loop system architecture diagram | §6.2 | required |
| Assembled `syssimx` system graph | §6.2 | required |
| Baseline convergence figure against OpenModelica | §6.5.1 | required |
| Multi-model switching figure with active-mode timeline and contact-event overlay | §6.5.2 | required |
| Performance figure comparing full-FEM and switched-FEM execution | §6.5.3 | required |
| Quantization comparison figure | §6.5.A | only if 6.5.A is included |
| Algebraic-loop result figure | §6.5.B | only if 6.5.B is included |

The multi-model switching figure (§6.5.2) and the performance figure (§6.5.3) **may share one two-panel figure** if the trajectory comparison and the active-mode timeline can be combined cleanly.
Otherwise keep them as separate figures.

Avoid duplicating figures from Chapter 5.
Chapter 6 figures must show the case-study system and its results, not implementation mechanisms.

---

## Repository Lookup for Chapter 6

Use this section to find the relevant case-study material quickly.
Do not describe repository paths in the thesis text unless they are needed for reproducibility.

### Thesis Figures

- `thesis/figures/6_case_study/controlled_pendulum/system_assembly.tex` defines the TikZ source for the closed-loop system diagram.
- `thesis/figures/6_case_study/controlled_pendulum/system_assembly.pdf` is the compiled diagram.
- `thesis/figures/6_case_study/controlled_pendulum/components/` contains reusable TikZ component drawings for the setpoint, PID controller, drive, pendulum, sensor, ADC, and decoder.
- `thesis/figures/6_case_study/controlled_pendulum/styles.tex` contains local TikZ styling for the controlled-pendulum diagram.

### Case-Study Notebooks

- `docs/05_case_study/00_overview.ipynb` gives the scenario roadmap and the conceptual block-level overview.
- `docs/05_case_study/01_baseline.ipynb` covers the required Scenario 6.5.1.
- `docs/05_case_study/02_quantization.ipynb` covers the optional Scenario 6.5.A.
- `docs/05_case_study/03_algebraic_loop.ipynb` covers the optional Scenario 6.5.B.
- `docs/05_case_study/04_rigid_contact.ipynb` is superseded by `05_multi_model_switching.ipynb` for the thesis. Keep for documentation purposes.
- `docs/05_case_study/05_multi_model_switching.ipynb` covers the required Scenarios 6.5.2 and 6.5.3.
- `docs/05_case_study/figures/graphs/` contains exported system graph visualizations for the case-study scenarios.

### Tool-Integration Notebooks

- `docs/04_tool_integration/01_modelica/` contains Modelica pendulum, contact, FMU export, and rollback material.
- `docs/04_tool_integration/02_opensim/` contains OpenSim pendulum setup, torque actuation, and contact tutorials.
- `docs/04_tool_integration/03_fem/` contains FEM pendulum setup, torque application, and compliant contact tutorials.
- `docs/04_tool_integration/04_master_pendulum/` contains the MasterPendulum tutorials for model switching and contact-aware modes.

### Implementation Sources

- `demos/ControlledPendulum/src/master_pendulum/orchestration/master_pendulum.py` implements the `MasterPendulum`.
- `demos/ControlledPendulum/src/master_pendulum/components/fmu/fmu_pendulum.py` implements the FMU pendulum wrapper.
- `demos/ControlledPendulum/src/master_pendulum/components/opensim/opensim_pendulum.py` implements the OpenSim pendulum wrapper.
- `demos/ControlledPendulum/src/master_pendulum/components/fem/fem_pendulum.py` implements the FEM pendulum component.
- `demos/ControlledPendulum/src/master_pendulum/components/fem/material_laws.py` contains the FEM material model.
- `demos/ControlledPendulum/src/master_pendulum/components/fem/pendulum_config.py` contains FEM pendulum parameters.
- `demos/ControlledPendulum/src/master_pendulum/components/fem/pendulum_mesh.py` contains geometry and mesh setup.

### Modelica Reference Package

- `demos/ControlledPendulum/src/modelica/ControlledPendulum/Examples/NoContact/Baseline.mo` defines the baseline monolithic reference.
- `demos/ControlledPendulum/src/modelica/ControlledPendulum/Examples/NoContact/Quantization.mo` defines the quantization reference.
- `demos/ControlledPendulum/src/modelica/ControlledPendulum/Examples/NoContact/AlgebraicLoop.mo` defines the strongly coupled reference.
- `demos/ControlledPendulum/src/modelica/ControlledPendulum/Examples/Contact/RigidContact.mo` defines the rigid-contact reference.
- `demos/ControlledPendulum/src/modelica/ControlledPendulum/Examples/Contact/CompliantContact.mo` defines the compliant-contact reference.
- `demos/ControlledPendulum/src/modelica/ControlledPendulum/Actuators/` contains drive models.
- `demos/ControlledPendulum/src/modelica/ControlledPendulum/Controllers/` contains PID controller variants.
- `demos/ControlledPendulum/src/modelica/ControlledPendulum/Plants/` contains pendulum and wall-contact models.
- `demos/ControlledPendulum/src/modelica/ControlledPendulum/Sensors/` contains the angle sensor and decoder.
- `demos/ControlledPendulum/src/modelica/ControlledPendulum/Trajectories/` contains the setpoint model.

### Background Notes

- `research/theory/06_case_study/introduction.md` contains early motivation notes for the case study.
- `research/theory/06_case_study/pendulum_dynamics.ipynb` contains pendulum dynamics notes.
- `research/theory/06_case_study/actuator.ipynb` contains actuator notes.
- `research/theory/06_case_study/dimensioning.ipynb` contains dimensioning notes.

---

## Component Background Depth

The case-study chapter explains component **roles**, not full component theory.
Use the system diagram of §6.2 to introduce the signal flow.
Then explain only the physical background that is needed to interpret the validation plots.

### Controller, Drive, and Sensor

- Explain the PID controller as the source of the control signal from the reference error.
- Explain anti-windup only if Scenario 6.5.2 compares PID behavior with and without integrator reset.
- Explain the BLDC drive only as a torque-producing dynamic actuator.
- Do not derive electromagnetic motor equations unless the drive dynamics are part of the result interpretation.
- Explain the angle sensor and decoder only as the source of sampled and quantized angle feedback.
- Do not explain potentiometer physics or ADC theory in detail.

### Pendulum Models

- Explain the Modelica pendulum as the monolithic reference and as the source for FMU plant variants.
- Explain the OpenSim pendulum only to the level needed to justify tool heterogeneity.
- Explain the FEM pendulum in more detail because it is the high-fidelity contact model.
- Keep the FEM explanation tied to the case-study outputs and contact behavior.
- Avoid repeating wrapper implementation from Chapter 5.

### Recommended Rule

Explain a concept only when an observed deviation in the result depends on it.
If a concept only explains how a standard component works internally, reference the component role and keep the detail out of Chapter 6.
