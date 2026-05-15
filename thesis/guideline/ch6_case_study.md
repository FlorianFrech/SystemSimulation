# Chapter 6 Guideline

This document defines the scope, structure, and boundary rules for Chapter 6.
Chapter 6 covers the controlled-pendulum case study.
It must be read together with the following documents.

- `README.md`
- `thesis_concept.md`
- `golden_rules_writing_summary.md`
- `writing_style.md`
- `glossary.md`
- `notation.md`
- `claims_and_evidence.md`

---

## Role of Chapter 6

Chapter 6 is the system-level case-study chapter.
It must not become another implementation chapter.
Its role is to show that the framework features from Chapter 5 work together on a realistic closed-loop system.

The controlled pendulum is used to verify selected co-simulation results against monolithic OpenModelica reference simulations and to validate that the framework workflow combines heterogeneous tools, hybrid events, and runtime model switching.

The chapter is approximately 15 to 20 pages.

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
For OpenSim, state only the concrete pendulum interface: torque input, angle, angular velocity, angular acceleration, synchronized mass, center-of-mass length, pivot inertia, absence of muscle dynamics, and role as the intermediate-fidelity model.
For FEM, include the concrete geometry, mesh, boundary regions, hinge constraint, torque boundary, contact law, internal stepping, and output projection because these choices affect the interpretation of the contact scenarios.

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
- Mesh and labeled boundary regions.
- Neo-Hookean material choice.
- Newmark time integration.
- Torque application.
- Compliant contact boundary.
- Rigid-body output mapping to `theta`, `omega`, and `alpha`.
- Reason for using high stiffness to approximate rigid contact.
- One FEM-specific figure with two panels:
  - Panel A: FEM mesh or reference configuration with labeled regions: pivot or rotation boundary, torque boundary, contact boundary, and wall or contact surface.
  - Panel B: representative deformed configuration during contact, optionally colored by displacement magnitude or von Mises stress.

Do not include the following details unless they are needed for interpreting a result.

- Full variational derivation.
- Detailed mesh construction.
- Full NGSolve implementation detail.
- Long material-law derivations.
- General FEM theory that is not used in the result discussion.
- Exploratory notebook figures that are not converted into thesis-ready figures.

The chapter may mention that switching between FEM and rigid-body models is a projection.
FEM deformation states are not fully representable in the rigid-body models.
This modeling consequence is discussed in §6.6 for Scenario 6.5.2.

Figures from `docs/04_tool_integration/03_fem/` and `demos/ControlledPendulum/notebooks/master_pendulum/fem/` may be used as source material.
They should not be inserted as notebook screenshots.
Use them to generate one thesis-ready FEM model figure or, at most, one additional appendix figure.
The main text should not contain a separate verification gallery for the FEM pendulum unless a plotted field directly supports a claim in §6.5 or §6.6.

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
One compact figure with three panels.

- Panel A. Trajectory comparison of full-FEM and switched configurations over the full horizon, with the FEM-active interval indicated by a thin mode strip between the trajectory panels.
- Panel B. Magnification of the contact window in which the FEM model is active.
- Panel C. Median wall-clock time of full-FEM and switched configurations, decomposed into total run time and FEM solver time, with the runtime speedup reported as an inset.

**Reference traces in the figure.**
The §6.5.3 figure shows only the two performance-relevant traces: full-FEM and switched.
The OpenModelica rigid-contact reference does **not** appear in the §6.5.3 figure.
It is the verification reference of §6.5.2 and would blur the performance message if added.
The rigid-body bound for the acceptance criterion is reported only as a numerical value in the §6.5.3 table.


**Required honest reporting.**
If switching introduces visible discontinuities or contact artifacts, state this explicitly in §6.6.

Suggested wording for the §6.5.3 introduction.

```latex
The performance comparison evaluates whether the multi-model plant can reduce the cost of the high-fidelity FEM model without changing the relevant contact response.
The switched configuration uses the FEM model only inside the contact window and otherwise advances the rigid-body model.
The comparison therefore measures both numerical deviation and wall-clock runtime.
```

---

## Scenario 6.5.3 — Implementation Findings (engineering notes)

This section captures empirical findings from the implementation of the
performance benchmark that are needed to interpret §6.5.3 and §6.6 honestly.
They are notes for the author and should be condensed into the chapter
discussion, not copied verbatim.

### Headline benchmark numbers (`thesis/notebooks/casestudy_performance.ipynb`)

The final thesis values are medians over five measured runs.
One warm-up run was excluded.
Do not report the earlier single-run timing values in the thesis text.

| Metric | Value |
|---|---:|
| Full-FEM total wall time | `464.032 s` |
| Switched total wall time | `294.321 s` |
| End-to-end speedup | `1.577x` |
| Full-FEM solver wall time | `454.951 s` |
| Switched FEM solver wall time | `224.344 s` |
| FEM solver wall-time reduction | `2.03x` |
| Full-FEM solver calls | `850` |
| Switched FEM solver calls | `425` |
| Switched FEM-active simulated time | `0.189 s` |
| Switched FEM-active share | `47.3%` |
| Mode switches | `2` |
| L∞(switched, full) | `2.839e-02 rad` |
| L²(switched, full) | `8.202e-03 rad` |

**Headline statement.** End-to-end speedup is `1.58x`.
The FEM solver wall time is reduced by `2.03x`.
The gap between FEM solver speedup and end-to-end speedup is the
`MasterPendulum` orchestration overhead and the non-FEM part of the
simulation.

### State-projection effect at FMU → FEM switch

The switched and full-FEM runs use **identical FEM parameters** (mesh,
material, contact stiffness, mesh order, gravity, internal step). The
divergence between their trajectories has a different cause.

At the FMU → FEM switch (`MultiComponent._switch_mode`),
`FEMPendulum.set_state` rebuilds `(u, v, a)` as a pure rigid-body rotation
of `(θ, ω, τ)` from the FMU and resets the Newmark history
`(u_old, v_old, a_old) ← (u, v, a)`. The body therefore enters contact
without the deformation field, vibrational modes, or Newmark history that
the full-FEM run has accumulated for ~170 ms before first impact.

Observed consequences in the controlled-pendulum scenario:

- The **first wall-hit time matches to ~10⁻⁵ s** (essentially one FEM
  micro-step).
- Subsequent wall-hit times **drift earlier by ~1 ms per bounce** in the
  switched run. By the fifth bounce the offset is ~4 ms.
- **Wall penetration is greater in full-FEM than in switched** at every
  bounce, because the full-FEM body carries vibrational kinetic energy
  and pre-stress at impact while the switched body does not.

### Required honest reporting in §6.6

The above effect is exactly the modeling cost the chapter must discuss
under "Discuss the consequences of approximating rigid contact with stiff
compliant FEM contact in 6.5.2". Suggested phrasing for §6.6:

> The switched configuration enters FEM contact from a rigid-body
> projection of the FMU state. Compared with the full-FEM run the
> switched body lacks the deformation field and Newmark history
> accumulated during the upswing. As a result the switched body
> penetrates the wall less deeply at each bounce, and the contact times
> drift earlier by approximately 1 ms per bounce. This is the modeling
> cost of state projection at a mode switch and bounds the sense in
> which the switched configuration "reproduces" the full-FEM trajectory.

### Acceptance-criterion plumbing (§6.4)

The §6.5.3 figure shows only `Full FEM` and `Switched` trajectories
(plus a thin FEM-active mode strip between the two trajectory panels).
The rigid-contact OpenModelica reference is deliberately omitted from the
figure to keep the performance message clean and is instead reported as
a numerical row in the §6.5.3 metrics table.

Two error rows are required in the §6.5.3 table:

1. `theta_E∞(switched, full-FEM)` — already computed in the notebook.
2. `theta_E∞(rigid, full-FEM)` — the rigid-body lower bound. Compute it
   by adding a third "Rigid pendulum" run to `casestudy_performance.ipynb`
   that uses the FMU pendulum as the plant with `omega_invert` event
   handling enabled. The same Modelica rigid-contact trace already
   loaded in the notebook can be reused if its timing aligns with the
   syssimx macro grid.

The acceptance criterion `L∞(switched, full-FEM) ≤ L∞(rigid, full-FEM)`
is then checked numerically and stated as a one-line claim under §6.5.3.

A separate row `theta_E∞(syssimx, monolithic-Modelica)` belongs to
Section 6.5.2 only and is reused from `casestudy_model_switching.ipynb`.
It is not part of the §6.5.3 table.


### Implementation-side optimizations applied

Four library and notebook changes were necessary to obtain the headline
numbers above. They are *implementation choices* that belong to Chapter 5,
but their motivation is rooted in the Chapter 6 case study. The §6.6
discussion should reference them only by effect, not by code site.

1. **Internal-event-hint forwarding through `MultiComponent`.**
   `MultiComponent.get_internal_event_hints` now delegates unconditionally
   to `active_comp.get_internal_event_hints`, so the hybrid algorithm can
   short-circuit bisection when the FEM has already localized a contact
   crossing during its own micro-stepping. Without forwarding, every
   contact event in the switched run incurred a full bisection that
   re-stepped the FEM 4–17 times per event.

2. **`get_state` removed from `MultiComponent._do_step_internal`.**
   The mode selector is now invoked with `(t, None)` and reads what it
   needs from cached output ports (`self.outputs[...].get()`). The
   previous implementation called `FEMPendulum._rigid_proxy()` (six
   NGSolve mesh integrals) once per macro step while FEM was active,
   contributing tens of seconds of orchestration overhead.

3. **Hysteresis-aware short-circuit.**
   `_do_step_internal` checks the dwell window before invoking the
   selector. When the dwell has not elapsed, the selector is skipped
   entirely. Defensive optimization for selectors that are not yet
   following lever (2).

4. **Hybrid-algorithm tolerance tuning per scenario.**
   `tol_time = 1e-5 s` (10 µs ≈ 1 % of macro step) and
   `event_dedup_tol = 5e-4 s` are set on `system.algorithm` after
   `system.initialize`. The first reduces bisection iterations from
   ~17 to ~3 per event when the hint short-circuit does not fire; the
   second folds the spurious double-event observed at the second bounce
   in early experiments.

### Performance instrumentation pitfall

`fem_wall_s` and `fem_calls` must be measured by wrapping
`FEMPendulum._do_step_internal`, **not** `do_step`. The hybrid algorithm
calls `_do_step_internal` directly on event sources for trial steps in
`_detect_crossings`, for bisection iterations in `_locate_event_time`,
and for the post-localization event-collection re-step. Wrapping
`do_step` would miss those calls in the full-FEM case (where the FEM is
the event source) but catch them in the switched case (where they
delegate via `MasterPendulum.active_comp.do_step`), making the two
cases incomparable. With the wrong wrapping, `fem_calls` reads 405 for
full-FEM and 425 for switched — appearing to show *more* FEM work in the
switched case. With the correct wrapping the numbers are 850 and 425, a
clean 2× reduction.

### Where the orchestration overhead goes

For the §6.6 discussion of "tradeoff between accuracy and runtime", the
gap between the FEM solver speedup and the observed end-to-end speedup is
consumed by:

- mode-selector evaluations (one cached-output read per macro step),
- `_detect_crossings` trial steps that delegate FMU/FEM stepping
  through `MasterPendulum`,
- per-event post-localization re-step,
- `set_inputs` propagation to all three sub-components every macro step,
- `MasterPendulum.set_state` at each mode switch, including
  `_rigid_proxy` evaluation in the source component.

This is a *constant* per macro step, so the relative cost shrinks as the
FEM problem becomes more expensive (finer mesh, longer horizon).
The reported end-to-end speedup should therefore be interpreted as a
benchmark for the present model size, not as a general upper bound.

### Configuration parameters used by the figure

These are the values that produce the published `performance_switching.pdf`.
They are repeated here because they cross-cut the figure caption and
table footnotes in the chapter.

- `T_END = 0.4 s`
- `MACRO_DT = FEM_INTERNAL_DT = 1e-3 s`
- `CONTACT_STIFFNESS = 2e9 N/m`
- `DWELL_TIME = 0.05 s`
- `FEM_SWITCH_THRESHOLD_RAD = 0.075 rad ≈ 4.3°`
- `algorithm.tol_time = 1e-5 s`
- `algorithm.event_dedup_tol = 5e-4 s`
- Material: SVK, `E = 2.1·10¹¹ Pa`, `ν = 0.3`, `ρ = 7850 kg/m³`
- Mesh: order 2, `max_element_size = 0.03`, curved
- Geometry: defaults from `pendulum_config.py`
  (`r_rod = 0.015`, `r_head = 0.06`, `l_center = 0.24`, `wall_len_y = 0.25`)

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
| FEM model figure with mesh/boundaries and representative contact deformation or stress field | §6.3.3 | recommended |
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
- `docs/04_tool_integration/03_fem/01_fem_pendulum_basics.ipynb` can provide source material for the FEM mesh, geometry, and hinge-constraint explanation.
- `docs/04_tool_integration/03_fem/02_fem_pendulum_torque.ipynb` can provide source material for the torque-boundary explanation.
- `docs/04_tool_integration/03_fem/03_fem_pendulum_contact.ipynb` can provide source material for the contact-boundary and contact-field figure.
- `docs/04_tool_integration/04_master_pendulum/` contains the MasterPendulum tutorials for model switching and contact-aware modes.
- `demos/ControlledPendulum/notebooks/master_pendulum/fem/` contains exploratory FEM pendulum checks for driven motion, swing, impact, and event detection. Use these notebooks for author verification and figure generation, not as direct thesis figures.

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
