# SysSimX — Open Issues

> Working record of what remains. Resolved work is summarized in
> [`CHANGELOG.md`](CHANGELOG.md); the implementation records and measured
> baselines of the runtime-switching redesign are in
> [`MILESTONES.md`](MILESTONES.md).

Identifiers are stable. An issue that has been closed keeps its identifier in
the changelog, so `HYB-06` still means the same defect after it disappears from
this file.

## Scope

What remains open in the runtime model-switching implementation and the
framework around it:

- [`syssimx/core/multi_comp.py`](syssimx/core/multi_comp.py)
- [`syssimx/system/algorithms/hybrid.py`](syssimx/system/algorithms/hybrid.py)
- [`syssimx/components/fmu.py`](syssimx/components/fmu.py)
- [`demos/ControlledPendulum/src/master_pendulum/`](demos/ControlledPendulum/src/master_pendulum/)

`MasterPendulum` combines FEM, OpenSim, and FMU implementations behind one
`MultiComponent`, so it remains the reference case for state transfer, event
localization, rollback, hysteresis, and lifecycle management.

## Where things stand

The switching mechanism is consolidated and released in v0.3.0.
`set_switch_regions()` is the only public model-selection API, transitions
resolve only from localized generated boundaries, transfers are transactional
and declare what they preserve and lose, and speculative advances leave no
observable trace. That work is summarized in
[`CHANGELOG.md`](CHANGELOG.md) and recorded in
[`MILESTONES.md`](MILESTONES.md).

Four themes remain open, in rough order of what gates what:

1. **Detection cost and correctness.** Roughly half of all model time is
   computed and rolled back, and detection still runs on a trajectory the
   system never commits. HYB-01 through HYB-05, EVID-01.
2. **Numerical evidence for the paper.** Convergence order and switch placement
   are unmeasured, and the benchmark is short. EVID-02 through EVID-05.
3. **Backend and platform coverage.** The validation gate is uneven, and a
   green local run does not imply a green CI run for anything touching FMU
   lifecycle. HARD-01, HARD-02.
4. **Native resource lifecycle.** The defective CVODE exports are still
   retained, and no archive's library is ever unmapped. HARD-05, HARD-07.

## Current runtime-switching mechanisms

| Mechanism | Trigger | Placement | Current MasterPendulum use | Status |
|---|---|---|---|---|
| `set_switch_regions()` | Generated boundary events for an ordered scalar region map | Bisection-localized event time | Default typed three-model angle policy | Sole public automatic switching mechanism |
| `_switch_mode()` | Direct internal invocation | Caller-provided time | None | Private transactional transfer primitive, not a switching policy |

### Removed legacy mechanisms

The grid-polled selector and public fixed-target indicator APIs were removed in Milestone 3. Their
placement, arbitration, and registration-order semantics are retained only in the completed issue
records below. Consumers that need scheduled test motion supply time as the scalar region signal in
an external harness; production components do not install time-driven selectors.

### Declarative switch regions

[`set_switch_regions()`](syssimx/core/multi_comp.py) maps one scalar key onto ordered model regions.
It generates one bidirectional event per breakpoint. A nonzero `band` provides Schmitt-trigger
behavior and is the sole chatter-prevention mechanism.

### State transfer

Every accepted region transition calls
[`_perform_state_transfer()`](syssimx/core/multi_comp.py):

1. Export physical state from the outgoing model with `get_state()`.
2. Adapt it for the target model.
3. Replay the most recently received inputs.
4. Import the state into the incoming model with `set_state()`.
5. Refresh incoming output ports.
6. Build the domain transfer report, which validates the preserved invariants and measures the
   acceleration and energy the canonical interface does not carry.
7. Update `active_mode` and `active_comp`.
8. Record the committed switch, its transfer report, and the active region index.

Steps 1 through 6 run inside the transaction, so a rejected report rolls the whole preparation back.
`BACKEND_STATE_SEMANTICS` and `transfer_state_semantics()` in the master pendulum declare which
state each directed transfer preserves, reconstructs, and loses.

## Multi-component and switching

MC-01 through MC-10 and MC-14 are resolved; see the changelog. What follows is
the remainder.

### MC-11 — Dead and duplicated abstractions obscure the real design

**Priority:** Medium

**Status:** Partially resolved by Milestones 1 and 3.

The region-specific duplication is gone: one immutable configuration owns typed one-per-boundary
records, and `active_region_index` is authoritative. The following cleanup remains:

- `StateAdapter` and `state_adapters` are documented but not used by state transfer.
- `_prev_state` and `_curr_state` are unused.
- Wrapper `sync_events` duplicates part of the system event history.

**Suggested solution**

- Remove dead fields or implement the advertised adapter mechanism.
- [x] Replace parallel switching dictionaries with immutable `SwitchRegions` and typed boundaries.
- [x] Store one authoritative active-region index and derive mode/component through properties.
- Record a structured `ModeSwitchEvent` in the common system history.
- [x] Represent one region boundary once, retaining crossing direction as event metadata.

### MC-12 — MultiComponent and MasterPendulum rely heavily on private internals

**Priority:** Medium

**Status:** Partially resolved. The checkpoint/trial contract removed algorithm-side flag
manipulation, and the fixed-target dictionary no longer exists. Subclasses still reach into private
details such as `_unify_ports()` and `_initialize_ports_from_specs()`. `MasterPendulum` also reads
backend-private fields including
`_with_contact`, `_use_gravity`, `_equivalent_length`, and `_get_contact_gap_distance()`.

This makes lifecycle and algorithm behavior dependent on implementation details rather than stable
contracts.

**Suggested solution**

- Add a public configuration query such as `has_switch_regions` if lifecycle code needs it.
- Make port unification/creation an automatic base lifecycle operation.
- Define public backend metadata/proxy interfaces for mass, inertia, length, gravity, contact, and
  monitoring values.
- [x] Replace algorithm flag manipulation with the checkpoint/trial protocol from MC-03.

### MC-13 — MasterPendulum region configuration and naming need cleanup

**Priority:** Low

**Status:** Mostly resolved by Milestone 3. Typed radians-based configuration, initialization-time
region reconciliation, and the external scheduled-test harness replace the former selector code.
Centralizing all mode strings in a stronger type remains optional cleanup.

**Suggested solution**

- [x] Move region parameters into a typed `MasterPendulumSwitchConfig`.
- [x] Store all angular thresholds internally in radians.
- [x] Retain only signal bands for chatter prevention.
- Use a `Mode` enum or centralized constants.
- [x] Derive the initial region and model from the switching signal at `t0`.
- [x] Move the time-driven demonstration cycle into an external test harness.

## Event tolerances and time representation

### TIME-01 — One `tol_time` serves incompatible purposes

**Priority:** High

One global tolerance currently serves both event-hint acceptance and switch localization:

- `FEMPendulum` brackets contact using its 1e-4 s internal step. The hybrid algorithm can accept
  that bracket without further bisection only when `tol_time >= 1e-4`.
- Switch localization resolves only to `tol_time`. A value such as 1.5e-4 s is already 15% of a
  1e-3 s macro step and weakens the distinction from grid placement.

Notebook 6 favors contact with `tol_time = 1.5e-4`; notebook 5 favors switch placement with
`tol_time = 1e-5`. Neither choice is inherently wrong, but the trade-off is hidden in one global
float.

**Suggested solution**

- Let components declare a preferred or minimum meaningful time resolution.
- Negotiate a system/event-layer resolution during initialization.
- Distinguish component hint granularity from the master's desired localization precision.
- Under integer time, represent a component's smallest bracket as an exact number of ticks.

### TIME-02 — `tol_value` is a silent, signal-scaled failure mode

**Priority:** High

After bisection, event collection accepts an indicator only when `abs(value) <= tol_value`.
Therefore `tol_value` must exceed approximately
`max|d(indicator)/dt| * tol_time`. If it does not, the algorithm can bracket and localize a crossing
but then collect no event. Partial switch counts such as 2-of-4 or 4-of-8 can look plausible and do
not raise an error.

Integer time does not by itself solve this problem because `tol_value` is expressed in the value
domain—radians, degrees, metres, and so on.

**Suggested solution**

- Carry the final crossing bracket and sign information into event collection.
- Accept the already-bracketed event from the sign change rather than a scale-dependent magnitude
  test.
- Retain a small numerical zero tolerance only for genuinely zero-valued endpoints, not as the
  primary event-existence test.
- Until that redesign lands, derive or validate a lower bound for `tol_value` from the negotiated
  time resolution and an indicator-rate bound.

This solution also addresses the direction-loss problem in MC-05.

### TIME-03 — Floating-point time creates avoidable correctness workarounds

**Priority:** Medium

Simulation time is a Python `float` throughout `System.run`, component steps, port timestamps,
event hints, and `DenseTime.t`. Multiple tolerances compensate for equality and accumulation
problems:

| Tolerance/workaround | Purpose | Effect of integer time |
|---|---|---|
| `eps = 1e-12` in the hybrid interval loop | Decide whether `t_left < t_right` | Exact comparison |
| `_SUBSTEP_TIME_REL_TOL` in FEM | Suppress a residual substep | Exact accumulation |
| `tol_time` when escaping a handled event | Move beyond the event | Replace with a microstep |
| `tol_time` for hint acceptance | Decide whether a bracket is narrow enough | Exact tick test |
| `tol_time` for bisection termination | Finite event resolution | Exact test at finite resolution |
| `event_dedup_tol` | Suppress nearby duplicates | Exact same-instant test; any time window remains a model choice |
| `tol_value` | Indicator magnitude | Not fixed by integer time |
| `sign_tolerance` | Indicator sign | Not fixed by integer time |

The practical motivation is an observed FEM failure: floating-point accumulation left a
5.2e-18 s residual step, and the Newmark update divided by it, producing a roughly 1e8 rad/s
divergence. A guard now prevents it, but tick arithmetic would make that residual structurally
impossible.

**Suggested solution: staged adoption**

1. Use integer ticks inside the master's event layer while converting to float at the component
   boundary.
2. Add optional component-resolution declarations and negotiate a common resolution.
3. Adopt tick arithmetic inside `FEMComponent` substepping if the added complexity is justified.

The third stage has the narrowest scope and highest cost; the current FEM residual guard should
remain until it is replaced.

### TIME-04 — Superdense time is only partially used

**Priority:** Medium

`DenseTime(t, micro)` represents same-real-time event cascades, but after handling an event the
outer hybrid loop advances real time with `t_left = dense_time.t + tol_time`. This is the kind of
event ordering that the micro index should represent without perturbing physical time.

**Suggested solution**

- Carry `DenseTime` through the outer event interval loop.
- Advance the micro index at the same real time after handling an event.
- Use exact event identity/microstep state to prevent rediscovery rather than nudging real time.

For the paper, integer time and resolution negotiation should be attributed to the established
hybrid co-simulation literature, including Cremona et al. (2019), rather than presented as a novel
contribution.

## Hybrid event detection and localization

This section refines EVID-01. EVID-01 records the measured cost of speculative FEM work. The issues
below record why the obvious reuse fix is not directly legal, which cheaper fixes are available, and
one correctness risk that the current detection scheme carries independently of cost.

### HYB-01 — Detection runs on a trajectory the system never takes

**Priority:** High

**Status:** Guarded on 2026-08-24. `HybridAlgorithm` re-evaluates the indicators after every accepted
advance that detection called event-free, collects anything that slipped through in `missed_events`,
and warns. `raise_on_missed_event` makes the mismatch fatal. Covered by
`tests/unit/system/test_hybrid_missed_events.py`. The underlying mismatch stands; only the silence
is fixed, and escalating the report to a rollback still depends on HYB-02.

[`_detect_crossings()`](syssimx/system/algorithms/hybrid.py#L328) advances every event source with
the inputs cached at `t_left`. The accepted advance re-reads inputs after the upstream generation
has already stepped, in
[`GaussSeidelAlgorithm.step()`](syssimx/system/algorithms/gauss_seidel.py#L63). In the case-study
system `Drive` precedes `MasterPendulum`, so the trial advance consumes `tau(t_left)` while the
accepted advance consumes `tau(t_left + dt)`. Detection therefore evaluates indicators on a
trajectory that is never committed.

This has two consequences.

1. The trial endpoint cannot be reused as the accepted endpoint without changing the coupling. See
   HYB-02.
2. A crossing that is present on the accepted trajectory but absent on the trial trajectory is never
   detected. For a falling indicator the miss is permanent rather than deferred by one macro step.
   [`detect_event_crossings()`](syssimx/core/base.py#L1348) requires `prev_sign > 0`, so once the
   indicator has gone negative without the event firing, the following macro step starts below zero
   and the crossing can no longer be observed. The notebook `wall_hit` indicator is registered with
   `direction=-1`, so a missed contact means the pendulum passes through the wall and never
   recovers.

The window is narrow, because the crossing must fall inside the band by which one macro step of
torque difference displaces `theta`, and no such miss has been observed in the recorded runs. The
failure is silent, which is what makes it worth a guard rather than an assumption.

**Suggested solution**

- Re-evaluate the indicators after the accepted advance in the no-crossing branch
  ([`HybridAlgorithm.step()`](syssimx/system/algorithms/hybrid.py#L131)) and compare them against
  `indicators_left`. For the case-study indicators this reads cached output ports and costs no
  backend advance.
- Report a crossing that appears on the accepted trajectory and was missed during detection, instead
  of dropping it.
- Escalate from a report to a rollback and a normal localization pass once HYB-02 has established a
  transactional accepted advance for event sources.

**Acceptance criteria**

- A regression test builds an event source whose trial and accepted trajectories straddle the
  threshold differently, and asserts that the mismatch is reported rather than silently discarded.

### HYB-02 — A trial endpoint cannot be committed without re-tearing the execution order

**Priority:** Medium

EVID-01 proposes reusing a trial endpoint as the accepted endpoint. That reuse is not directly legal
for the reason recorded in HYB-01. The naive alternative, accepting every advance and rolling the
system back when detection finds a crossing, is blocked by the rollback contract.
[`FMUComponent`](syssimx/components/fmu.py#L49) implements neither `snapshot_state()` nor
`restore_state()`, so `supports_rollback` is `False` for `Setpoint`, `PID`, `Drive`, and both
sensors. Only the three pendulum backends can be un-stepped, and a speculative full sweep would
require rollback from every component in the system.

A narrower restructuring keeps rollback scoped to event sources. Pin event sources to the front of
the execution order, advance them once with the inputs at `t_left`, retain that advance, and let
Gauss-Seidel advance only the remaining components. Roll the event sources back when a crossing is
found, which they support by contract. Nothing without rollback ever advances speculatively, and a
no-crossing macro step costs one backend advance per event source instead of two.

The reordering is a different tearing of the same feedback loop rather than a coupling downgrade,
provided the event source carries no relevant direct-feedthrough edge.
[`graph.py`](syssimx/system/graph.py#L98) already computes that condition, because a feedthrough
dependency becomes a zero-delay edge only when the output is actually connected. In the case study
`theta` and `omega` are not feedthrough outputs and `alpha` is unconnected, so `MasterPendulum` is a
free node in the `Drive`/`MasterPendulum` cycle and either side may step first.

**Suggested solution**

- Add a skip set to `GaussSeidelAlgorithm.step()` so the hybrid algorithm can exclude components it
  has already advanced.
- Replace the unconditional trial-and-restore with a checkpointed advance that is restored only when
  a crossing is found. Framework history is part of `ComponentCheckpoint`, so it rolls back together
  with the solver state.
- Fall back to the current two-advance path whenever an event source carries a relevant feedthrough
  edge, and assert that condition rather than assuming it.
- Record the residue that the checkpoint does not cover, which is the monitoring state, the FEM
  scene, and `sync_events`, and either suppress it during the speculative advance or re-emit it at
  commit time. This depends on MC-03.
- Note that `_set_inputs_for_generation()` still writes the later input values into the event
  source's ports. Recorded input history will not match the values the advance actually consumed
  unless those ports are skipped as well.

**Acceptance criteria**

- A no-crossing macro step invokes `_do_step_internal()` exactly once per event source.
- A crossing macro step produces the same located event time and the same accepted trajectory as the
  current implementation.

### HYB-03 — Detection is unconditional and has no cheap rejection test

**Priority:** High

Every macro step pays a full backend advance per event source, whether or not a crossing is
plausible. For the master pendulum all three indicators, `wall_hit` and both region boundaries, are
functions of `theta` alone, and their derivative is bounded by the already available `omega` and
`alpha`. A macro step whose indicator value exceeds that bound times `dt` cannot contain a crossing,
so its detection advance is provably unnecessary.

At `dt = 1e-3` and the angular rates reached in the case study, the resulting guard band is a few
milliradians wide. The detection advance then survives only in the one or two macro steps that
actually bracket a crossing, which removes almost all speculative FEM work without changing any
result. This is the cheapest of the options listed under EVID-01, and it requires no rollback
changes and no execution-order changes.

**Suggested solution**

- Extend `add_event_indicator()` with an optional derivative bound, supplied either as a constant or
  as a callable evaluated at `t_left`.
- Skip the detection advance for an indicator when `abs(g(t_left))` exceeds the bound times `dt`,
  with an explicit safety margin.
- Treat a missing bound as "no rejection possible" so existing components keep the current behavior.
- As a second variant for `MultiComponent`, use a cheap sibling model as the predictor. The master
  pendulum already owns a rigid-body FMU of the same plant, which can bracket a purely kinematic
  indicator such as `theta - theta_wall` at negligible cost. This variant does not extend to the
  deformation-driven contact gap, where the FEM internal hint remains the authority.

**Acceptance criteria**

- The contact benchmark reports a materially reduced trial-advance count at an unchanged accepted
  trajectory and unchanged located event times.
- A test asserts that an indicator without a declared bound still takes the detection advance.

### HYB-04 — Localization re-steps every event source and ignores the available internal bracket

**Priority:** High

Bisection is the dominant cost of a macro step that does contain an event, not the single discarded
trial advance. [`_locate_event_time()`](syssimx/system/algorithms/hybrid.py#L524) iterates up to
`max_iter = 50` times, and each
[`_evaluate_indicators_at()`](syssimx/system/algorithms/hybrid.py#L640) call re-advances **every**
event source from `t_left` to the midpoint. An event raised by a cheap component therefore still
pays repeated FEM advances.

The FEM backend already reports an exact micro-step bracket through
[`report_internal_event()`](demos/ControlledPendulum/src/master_pendulum/components/fem/fem_pendulum.py#L704),
but that hint short-circuits localization only when the bracket is narrower than `tol_time`
([hybrid.py](syssimx/system/algorithms/hybrid.py#L484)). A sub-step of `1e-4` never satisfies a
`tol_time` of `1e-8`, so the hint narrows the interval and bisection still runs.

Raising `tol_time` to reach that short-circuit is what exposed HYB-06, which lived in the same code
and silently dropped events whenever a hint and the macro endpoints agreed. That defect is fixed;
the work below should keep its regression tests green.

**Suggested solution**

- Restrict the midpoint evaluation to event sources that actually crossed over the macro interval,
  and document that this assumes one crossing per indicator and macro step.
- Accept an internal hint bracket directly as the located event time when its width is below a
  declared localization resolution, rather than requiring `tol_time`. This depends on TIME-01,
  because the two uses of `tol_time` must be separated first.
- Report the bisection iteration count per located event so the benchmark can attribute localization
  cost.

**Acceptance criteria**

- Locating a contact event on the FEM backend consumes no bisection advances when a usable internal
  bracket exists.
- Locating an event raised by a cheap component consumes no FEM advances.

### HYB-05 — MasterPendulum discards its declared direct feedthrough

**Priority:** Low

`MasterPendulum.__init__()` builds `direct_feedthrough` from `PENDULUM_DIRECT_FEEDTHROUGH`, which
declares that `alpha` depends on `tau`.
[`_initialize_component()`](demos/ControlledPendulum/src/master_pendulum/orchestration/master_pendulum.py#L424)
then overwrites it with `self.active_comp.direct_feedthrough`, and no pendulum backend declares one,
so the wrapper's declared dependency is lost during initialization.

This is currently harmless, because `alpha` is unconnected in every case-study system and
[`graph.py`](syssimx/system/graph.py#L98) ignores feedthrough on unconnected outputs. It stops being
harmless as soon as `alpha` is wired, and HYB-02 would read the wiped map when checking whether an
event source may be moved to the front of the execution order.

**Suggested solution**

- Remove the overwrite and keep the declared map, or make the assignment merge rather than replace.
- Assert during initialization that every registered backend agrees with the declared map, in the
  same way that `MultiComponent._detect_direct_feedthrough()` already does for its models.

## Numerical evidence and performance

### EVID-01 — Speculative FEM work is approximately half of runtime

**Priority:** High

`_detect_crossings()` advances every event source across the macro step and restores it. If no
crossing is present, Gauss-Seidel then advances the same interval again. The recorded contact
benchmark measured roughly 400 accepted macro steps and 806 FEM calls, plus approximately 20
bisection calls.

| Work | Approximate calls | Role |
|---|---:|---|
| Accepted | 400 | Retained solution |
| Trial | 400 | Rolled back |
| Bisection | 20 | Rolled back |

**The waste belongs to detection, not to switching**

Measured on 2026-08-24 in `notebooks/07_casestudy_performance_nocontact.ipynb`, after its baseline
was given a constant, never-crossing indicator so that both cases run `HybridAlgorithm` and pay the
same detection overhead. Before that change the baseline fell back to `GaussSeidelAlgorithm`, took
no trial advance at all, and the discarded share existed only for the switched case, where it could
be read as a cost of model switching.

| Notebook | Case | Accepted | Trial | Bisection | Discarded model time |
|---|---|---:|---:|---:|---:|
| 7, no contact | Full FEM, no switching | 28.92 s / 400 calls | 28.57 s / 400 calls | none | **49.7 %** |
| 7, no contact | Switched FEM/FMU | 6.00 s / 405 calls | 5.86 s / 405 calls | 1.40 s / 37 calls | **54.8 %** |
| 6, with contact | Full FEM, no switching | 216.18 s / 403 calls | 221.54 s / 403 calls | none | **50.6 %** |
| 6, with contact | Switched FMU/FEM | 100.31 s / 404 calls | 105.03 s / 404 calls | 1.36 s / 7 calls | **51.5 %** |

Four measurements across two notebooks, with contact and without, switching and not. A configuration
that never switches discards essentially the same fraction as one that does, so the trial-step waste
is a property of the hybrid detection scheme rather than of `MultiComponent`. That is the empirical
case for HYB-03.

The two notebooks also bracket what HYB-04 is worth. Notebook 6 spends 1.36 s over 7 bisection calls,
0.7 % of its model time, because `FEMPendulum` reports its own contact bracket and `tol_time = 1.5e-4`
is coarse enough to accept it. Notebook 7 has no such hint and spends 1.40 s over 37 calls, 10.6 % of
its model time, to localize five switches. Localization is nearly free exactly when a component
reports its own bracket and the algorithm is permitted to use it.

Bookkeeping scales the other way. Orchestration is 2.1 % and 2.5 % of the two runs in notebook 6,
where a FEM solve costs about 0.54 s, against 13.4 % and 23.5 % in notebook 7, where it costs about
0.07 s. Checkpoint and restore have a roughly fixed price per macro step, so they dominate where the
models are cheap.

The same run separates a cost this issue's call table does not. Making the baseline an event source
moved its orchestration from 1.39 s to 8.93 s, so 7.54 s of checkpoint, restore, and indicator
bookkeeping sits on top of the 28.57 s of discarded solve. Detection therefore costs that baseline
36.1 s of a 66.4 s run, or 54 %, and the bookkeeping share is proportionally larger when the model
itself is cheap: 23.5 % of the switched run against 13.4 % of the baseline. Any estimate of what
HYB-03 recovers must count the bookkeeping, not only the solve.

Two further numbers from the same run. Removing a stale tolerance margin raised bisection from 4.4
to 7.4 evaluations per switch, which is what `tol_time = 1e-5` actually costs, for 0.40 s or about
2 % of the switched run. And the like-for-like wall-time ratio is 3.82x, against the 1.96x the
mismatched-algorithm comparison reported and the 5.37x its accepted-work column reported; the
confounded pair bracketed the honest number from both sides.

**Suggested solution**

Evaluate, in increasing architectural scope:

1. Reuse a trial endpoint as the accepted endpoint when no crossing exists and the checkpoint can
   be committed safely.
2. Predict whether detection can be skipped from indicator value/rate bounds.
3. Add a component hook such as `can_skip_detection(t, dt)`.
4. Let event sources provide dense output or a cheap indicator predictor.

Any reuse optimization depends on MC-03, because a speculative step must be transactional before it
can be committed safely.

The four options above are analyzed in the "Hybrid event detection and localization" section.
Option 1 is not directly legal as stated and needs the re-tearing recorded in HYB-02, because trial
and accepted advances consume different inputs (HYB-01). Options 2 through 4 are consolidated in
HYB-03, which is the cheapest change and the one to attempt first. The table above also understates
localization work, because bisection re-advances every event source at every midpoint (HYB-04).

### EVID-02 — A convergence study is missing

**Priority:** High

The existing algorithm-verification notebook checks a first-order linear ODE against its analytic
solution but does not measure observed order under step refinement.

**Suggested solution**

- Run a step-size refinement study on the contact-free pendulum.
- Use localized switching so grid-placement error does not cap the full experiment at first order.
- Report state error, observed convergence order, switch-time error, and runtime.
- Keep the contact case separate because repeated impacts amplify sub-millisecond differences.

### EVID-03 — Existing placement results do not rank the strategies

**Priority:** High

Notebook 5 shows that localized switches occur off the communication grid, but its accuracy result
is mixed: the recorded run was about 30% better over the full horizon and about 2.4 times worse in
the contact window. That experiment cannot isolate placement accuracy because:

1. repeated impacts amplify small timing differences; and
2. the monolithic OpenModelica reference never switches, so the comparison combines model mismatch
   with switch-placement error.

**Suggested solution**

- Use the smooth pendulum and a fine-step grid-switch run as the placement reference.
- Test whether localized switching at `dt = 1e-3` already matches the grid method as `dt -> 0`.
- Combine this with EVID-02 so one refinement study answers both convergence and placement.

### EVID-04 — The performance benchmark is too short

**Priority:** Medium

The recorded benchmark covers 0.4 s and two switches. That is too little switching activity for a
stable published performance claim. A 2 s all-FEM run is estimated at about 39 minutes, so repeated
runs need an explicit overnight budget.

**Suggested solution**

- Extend the horizon and switch count.
- Record accepted, trial, bisection, transfer, and backend-initialization time separately.
- Run multiple repetitions and report variance.
- Archive raw timing data rather than only notebook output.

### EVID-05 — Cross-validation against another master is missing

**Priority:** Medium

There is no independent master-algorithm comparison for the FMU-only baseline.

**Suggested solution**

- Run the same FMU through PyFMI and CoFMPy and compare trajectories/events.
- Prefer these pip-installable tools over heavier toolchains whose setup cost is disproportionate.

## Framework hardening and release work

### HARD-01 — Backend validation is unbalanced

**Priority:** High

**Status:** Partially resolved by Milestones 4 and 5. The real composition now exercises OpenSim and every
directed backend transfer in CI. Standalone OpenSim contracts, platform-complete generic FMU
fixtures, and a second structural FEM example remain open.

`tests/unit/components/test_opensim.py` is empty. The real composition raises recorded coverage of
`syssimx/components/opensim.py` to 90%, but does not isolate its contracts. OpenSim represents one
third of the heterogeneity claim. FMU coverage is also incomplete on platforms without fixtures,
and FEM has only one structural case study.

**Suggested solution**

- Add OpenSim unit and contract tests.
- Add mocked FMU unit coverage plus platform-complete integration fixtures where feasible.
- Add a second structural FEM example to demonstrate that `FEMComponent` generalizes beyond the
  pendulum.
- [x] Include the real `MasterPendulum` switching tests from MC-14.

### HARD-02 — Slow FEM regressions are outside the normal gate

**Priority:** High

The full FEM physics suite takes roughly 29 minutes and is normally deselected. A regression that
produced an approximately 1e8 rad/s result passed the ordinary test gate.

**Suggested solution**

- Add a short, bounded contact-divergence smoke test to the normal or scheduled gate.
- Run the full physics suite on a scheduled/nightly workflow.
- Ensure shell pipelines preserve pytest's exit status; avoid reporting the status of `tail` or a
  similar downstream command.

### HARD-03 — Runtime dependencies include demo/documentation packages

**Priority:** Low

SciPy, Matplotlib, ipywidgets, traitlets, and pydot are not imported by the core `syssimx` package
according to the recorded audit.

**Suggested solution**

- Move them to demo, documentation, or visualization extras as appropriate.
- Update the Sphinx and ReadTheDocs environments in the same change, particularly for Matplotlib,
  so the strict documentation build remains green.

### HARD-04 — Release metadata is incomplete

**Priority:** Low

**Status:** Mostly resolved by the v0.3.0 release on 2026-08-24. `CHANGELOG.md` exists,
`syssimx/__version__.py` and `CITATION.cff` read 0.3.0 with a real release date, and the tag
published to PyPI. Two author-supplied identifiers are still missing.

- The `orcid` line in `CITATION.cff` is still commented out. It was deliberately left for the next
  release rather than guessed, because a wrong ORCID resolves to nothing or to another person.
- The `doi` line is still commented out, and no Zenodo deposit exists. A version DOI cannot be
  minted before the release it identifies, so this was always going to follow the first tag.

**Suggested solution**

- Add the ORCID to `CITATION.cff`.
- Archive the release on Zenodo, then uncomment `doi` with the version DOI it mints.
- Both land in v0.3.1 or the next minor release; neither warrants a release of its own.

### HARD-05 — OpenModelica CVODE exports corrupt the heap in `fmi2FreeInstance`

**Priority:** High

**Status:** Root cause isolated on 2026-08-22. Step 1 landed on 2026-08-24: release is now governed
by a static per-archive policy instead of a blanket retain-everything workaround. The defective
exports are unchanged, and steps 2 through 5 remain open.

`resolve_release_policy()` reads the solver flag out of the archive and the continuous-state count
out of the model description, so a component knows before it ever instantiates whether releasing is
safe. `FMUComponent.release_policy` carries the verdict and its reason. `reset()`,
`reinitialize_instance()`, and the restored `free()` release when it allows and retain when it does
not; `soft_reset()` refuses outright on a retained archive, because `fmi2Reset` fails on exactly the
same exports. Verified against all thirteen checked-in archives, and against the release path itself
in a subprocess so a wrong verdict would be an exit code rather than a lost session.

Six of the thirteen archives are now released rather than stranded, including four of the six FMUs in
the quantization system. Step 5 of the plan below is done: the lifecycle tests assert the policy
rather than the raw calls.

The policy separates two questions, because the evidence only covers one platform. Retention is
conservative everywhere, since being wrong that way leaks memory while being wrong the other way
aborts the process. Refusing `fmi2Reset` removes working functionality instead, so
`FMUReleasePolicy.resettable` refuses only where the fault is recorded. Linux CI exercises
`soft_reset()` successfully on `tests/fixtures/fmus/Pendulum.fmu`, a CVODE export with two continuous
states, which is the first direct evidence bearing on step 4: at least `fmi2Reset` on at least that
export does not fault on Linux. Nothing yet says whether `fmi2FreeInstance` behaves there.

Calling `fmi2FreeInstance` on an affected FMU raises Windows exception `0xC0000374`, heap corruption,
which takes the whole process down. `FMUComponent` therefore no longer calls `fmi2Terminate` or
`fmi2FreeInstance` and no longer removes the extraction directory. `reset()` drops the instance
reference and `reinitialize_instance()` builds a new slave over the retained directory. Both
master-pendulum tutorials, both FMU tutorials, and the master-pendulum switching path work again with
the default `cvode` solver.

**Which call fails**

Every scenario below was run in its own subprocess against each checked-in FMU, so a corrupted heap
is a recorded exit code rather than a lost session. The scenarios build up from a bare instantiation
to a full stepped run.

| Scenario | Calls after instantiation | Affected FMUs | Unaffected FMUs |
|---|---|---|---|
| `inst_free` | `fmi2FreeInstance` | heap corruption | ok |
| `init_free` | initialize, `fmi2FreeInstance` | heap corruption | ok |
| `init_term` | initialize, `fmi2Terminate` | ok | ok |
| `init_term_free` | initialize, terminate, free | heap corruption | ok |
| `step_term` | 10 steps, `fmi2Terminate` | ok | ok |
| `step_free` | 10 steps, `fmi2FreeInstance` | heap corruption | ok |
| `step_term_free` | 10 steps, terminate, free | heap corruption | ok |
| `step_term_free_lib` | 10 steps, terminate, free, `freeLibrary` | heap corruption | ok |
| `step_reset` | 10 steps, `fmi2Reset` | heap corruption | ok |
| `step_reset_reinit_step` | 10 steps, reset, initialize, 10 steps | heap corruption | ok |
| `reinstantiate_x5` | five further `fmi2Instantiate` cycles, nothing released | ok | ok |

Three results matter. `fmi2FreeInstance` is the only failing call, and it already fails on a bare
instantiation, before initialization mode and before any step. `fmi2Terminate` is safe everywhere,
so terminating without freeing is a legitimate partial cleanup. `fmi2Reset` fails on exactly the same
FMUs, which removes `soft_reset()` from the list of escapes and rules out rollback, stepping,
accumulated solver state, and the hybrid trial machinery as causes.

**Which FMUs fail**

The failure is a property of the export, not of the model. Each affected FMU declares `"s": "cvode"`
in `resources/<model>_flags.json` and has at least one continuous state. Zero-state CVODE exports
never allocate the solver and are unaffected.

| FMU | Solver flag | Continuous states | `fmi2FreeInstance` |
|---|---|---|---|
| `Plants/Pendulum_cvode` | cvode | 2 | heap corruption |
| `Plants/Pendulum_euler` | euler | 2 | ok |
| `Plants/PendulumWithDiscreteWall` | cvode | 2 | heap corruption |
| `Controllers/PIDControllerReset_cvode` | cvode | 2 | heap corruption |
| `Controllers/PIDControllerReset_euler` | euler | 2 | ok |
| `Controllers/PIDController` | cvode | 2 | heap corruption |
| `Actuators/DriveDynamic` | cvode | 1 | heap corruption |
| `Sensors/AngleSensor` | cvode | 0 | ok |
| `Sensors/AngleDecoder` | cvode | 0 | ok |
| `Trajectories/SetPoint` | cvode | 0 | ok |
| `docs/.../pendulum_cvode` | cvode | 2 | heap corruption |
| `docs/.../pendulum_euler` | euler | 2 | ok |

The rule was derived from the first eight rows and then used to predict the remaining four before
they were run. All four predictions held, including the two zero-state CVODE exports that survive
and the one-state `DriveDynamic` that does not. Every FMU was produced by OpenModelica 1.26.3.

This makes the fault the CVODE teardown inside the OpenModelica runtime rather than the framework's
calling sequence. The likely mechanism is a double free or a free of an uninitialized SUNDIALS
handle, reachable as soon as the solver object exists, which is why a model with no continuous
states escapes it.

**Suggested solution**

The staged plan below restores real cleanup for the FMUs that can take it, without putting a
crashing call back on any path.

1. Give `FMUComponent` a release policy derived statically at construction. The predicate above is
   readable from the archive without executing anything, so a component can know whether releasing
   is safe before it ever instantiates. Release when safe and retain when not. This alone restores
   correct lifecycle handling for every euler export and for the three zero-state sensor and
   trajectory FMUs, which is half of the quantization system.
2. Back the static predicate with an out-of-process capability probe for FMUs it does not recognize,
   such as exports from another tool. One subprocess per FMU file runs instantiate, terminate, and
   free, and the result is cached against the file's path, size, and modification time. A crashed
   probe marks the file unsafe and costs one process, not the session.
3. Re-export the affected demo FMUs with the euler solver, or with a newer OpenModelica, and confirm
   with the matrix above. The euler exports are already known good, and switching the demo default
   away from `cvode` removes the problem from the published tutorials rather than working around it.
4. Report the defect upstream with the minimal reproduction, which is instantiate followed by
   `fmi2FreeInstance` on any CVODE export with at least one continuous state. Check whether
   OpenModelica 1.27 or a nightly build still shows it, and whether the same export crashes on Linux.
5. Extend the lifecycle tests to both checked-in solver variants instead of only the euler one, and
   assert the release policy rather than the raw calls, so a regression in either variant is visible.
   This overlaps HARD-01's uneven backend coverage.

Until step 3 lands, the demo default staying `cvode` is a deliberate choice that keeps a defective
binary in the published tutorials and pays for it with the retained resources HARD-07 measures.

### HARD-06 — Published notebooks are unexecuted and leak machine-specific paths

**Priority:** Medium

**Status:** Partially addressed by Milestone 7.

Two separate problems in the published notebook set.

First, execution. `nb_execution_mode = "off"` means a notebook can rot, or carry no outputs at all,
without any job failing. Milestone 7 adds an nbmake gate, but it covers only the two switching
notebooks that need no simulation backend. Everything else remains ungated: the master-pendulum
tutorials while HARD-05 is open, the tool-integration notebooks that need real backends, and the
long-running Wave 2 evidence notebooks.

Second, output hygiene. `set_professional_style()` returns the `pyplot` module, so a bare call as
the last expression of a cell renders a repr containing the executing machine's absolute install
path. Notebook 3 was fixed with a semicolon. Five published notebooks still call it the same way
and will leak when re-executed:

- `notebooks/01_algorithm_verification.ipynb`
- `notebooks/02_hybrid_verification.ipynb`
- `notebooks/04_casestudy_baseline.ipynb`
- `notebooks/05_casestudy_model_switching.ipynb`
- `notebooks/06_casestudy_performance.ipynb`
- `notebooks/performance.ipynb`

Two published notebooks already carry leaked paths in committed outputs, from runs predating the
switching work:

- `docs/03_core_tutorials/01_fundamentals/02_importing_fmus.ipynb`, cells 1 and 17
- `docs/04_tool_integration/01_modelica/01_modelica_pendulum_basics.ipynb`, cell 3

**Suggested solution**

- Apply the semicolon to each remaining published caller as it is re-executed, or stop returning
  `plt` and update the `demos/` notebooks that bind its result.
- Re-execute the two notebooks carrying leaked paths and confirm the scan is clean.
- Extend the nbmake gate as blockers clear: the master-pendulum tutorials once HARD-05 is fixed,
  and the backend tutorials in the `test-fem` job.
- Run the long Wave 2 notebooks in the scheduled physics gate from HARD-02 rather than on pull
  requests.
- Add the absolute-path scan to CI so a leak cannot be committed again.
- Make the saved figures reproducible. `notebooks/03_multi_comp_verification.ipynb` writes the
  tracked `notebooks/figures/03_multi_component_switching.pdf`, and every execution rewrites it with
  identical size but different bytes, because Matplotlib stamps a creation date into the PDF. Any
  notebook run therefore dirties the working tree and any re-run produces a spurious diff. Setting
  `SOURCE_DATE_EPOCH`, or `pdf.compression`/metadata options, removes the churn.

### HARD-07 — Native FMU instances and extraction directories are never released

**Priority:** Medium

**Status:** Measured on 2026-08-22 in `notebooks/08_fmu_memory.ipynb`. Step 1 landed on 2026-08-24:
extraction is cached on the archive's identity, so the disk cost is gone for every FMU. Steps 2
through 6 remain open.

`extract_cached()` keys on path, size, and modification time, so every component and every repeated
`initialize()` reuses one directory, while a rebuilt archive is still extracted afresh.
`clear_extraction_cache()` provides the teardown that step 4 will build on. Measured over ten
`reset()`/`initialize()` cycles: **zero** new extraction directories, for a releasable and a retained
archive alike, against one whole directory per cycle before.

Resident growth is down to roughly 0.11 MB per cycle and is now dominated by the `ctypes` library
mapping rather than by the FMI instance, because `freeLibrary` is still never called. That is the
next thing to attack, and it is independent of the OpenModelica defect.

Creating one usable FMU allocates in three places, and Python owns only one of them. `fmpy.extract()`
unpacks the archive into a temporary directory that nobody removes on its own. `FMU2Slave` loads the
model library through `ctypes`, which keeps it mapped until `freeLibrary` is called. `fmi2Instantiate`
allocates the model state on the C heap, reachable only through the opaque component pointer and
releasable only by `fmi2FreeInstance`.

`fmpy.fmi2.FMU2Slave` defines no finalizer anywhere in its class hierarchy, so garbage collecting the
wrapper cannot release any of it. Dropping the wrapper is in fact worse than leaking, because the
pointer that `fmi2FreeInstance` needs is discarded with the object. The notebook measures this
directly. Deleting an initialized component and forcing a full collection reclaimed 315 Python
objects and 0.00 MB of resident memory, and left the extraction directory in place.

**Measured cost**

| Path | Resident growth | Disk growth | Extraction directory |
|---|---|---|---|
| `reset()` then `initialize()`, one plant FMU | 0.63 MB per cycle | 5.12 MB per cycle | new every cycle |
| `reset()` then `initialize()` then `run()`, quantization system of six FMUs | 2.55 MB per cycle | 30.8 MB per cycle | six new every cycle |
| `reinitialize_instance()`, the hybrid rollback path, euler plant | 0.037 MB per call | none | reused |
| `reinitialize_instance()`, the hybrid rollback path, CVODE plant | 0.004 MB per call | none | reused |
| terminate, free, and re-instantiate, the same loop with release, euler plant | 0.00 MB per call | none | reused |

Two things follow. Rollback is much cheaper than the initialization cycle and does not re-extract
anything, so a hybrid run with many bisection restores grows slowly and only in native heap. The
expensive path is repeated initialization, where each cycle strands a whole extraction directory, and
that is the path every parameter study takes. Across the whole measurement the Python heap moved
0.06 MB per system cycle against 2.55 MB of resident growth, which is what identifies the growth as
native rather than collectable.

The last row is the control. When the instance is released, the same twenty-cycle loop returns to
where it started, so the memory is reclaimable in principle and only the affected exports make
reclaiming it unsafe.

For the current notebooks and tests this is affordable, because they initialize a handful of times
and the kernel then exits. It is not affordable for a long parameter study, a many-switch run, or a
session that keeps one kernel alive. One execution of the measurement notebook itself leaves 47
extraction directories and 241 MB of temporary files behind, which Windows keeps locked until the
kernel exits.

**Suggested solution**

1. Cache extraction per FMU file rather than per initialization. Key the cache on the resolved path
   with its size and modification time, and let every component and every later `initialize()` reuse
   the same directory. This removes the entire disk cost and the repeated unzip, is independent of
   HARD-05, and is safe for every FMU.
2. Give rollback an ordered strategy instead of one fixed mechanism. Prefer `fmi2GetFMUstate` and
   `fmi2SetFMUstate` when the FMU declares the capability, which allocates nothing per restore. Fall
   back to `fmi2Reset` when the HARD-05 release policy says the FMU tolerates it. Fall back to
   terminate, free, and re-instantiate when release is safe. Keep today's retain-and-re-instantiate
   only as the last resort for the affected exports.
3. Re-export the demo FMUs with `-d=fmuExperimental` so they declare `canGetAndSetFMUstate`. The two
   FMUs under `docs/04_tool_integration/01_modelica/fmus` already declare it while none of the demo
   FMUs do, which is why rollback currently re-instantiates instead of restoring state. Pair this with
   the euler re-export from HARD-05, because tutorial 03 already shows that restoring a CVODE FMU's
   state produces a fatal `fmi2DoStep` on the next step while the euler FMU restores cleanly.
4. Release everything releasable at teardown. A `System`-level teardown, or a context manager around
   a run, can free every instance whose release policy allows it and remove the cached extraction
   directories, so a completed study returns its memory instead of holding it until the interpreter
   exits.
5. Count what is retained and expose it. A per-component counter of stranded instances, surfaced in
   the run summary and warned on past a threshold, turns a silent leak into a visible number and
   gives the performance work in EVID-01 a quantity to report.
6. Consider process isolation only if an affected FMU ever has to be released mid-run. Running that
   FMU in a worker process gives both crash isolation and real release, at the cost of marshalling
   every port value across the boundary.

Steps 1 and 2 are worth doing regardless of whether the OpenModelica defect is ever fixed.

## Reproducibility

### REPRO-01 — No archived, pinned reproduction artifact

**Priority:** High

There is no archived release tying together the source, locked environments, usable platform FMUs,
raw benchmark data, and one-command reproduction of convergence, switching-error, and performance
results. The FMU artifact directory is roughly 32 MB and lacks win64 support.

**Suggested solution**

- Tag and archive the release used for the paper.
- Pin that tag from the paper repository rather than vendoring a moving `syssimx` checkout.
- Publish platform-specific FMUs as release artifacts rather than expanding the Git repository.
- Provide one-command or scripted reproduction for every reported figure/table.
- Store raw numerical outputs and environment metadata alongside rendered notebooks.

## Prioritized next steps

v0.3.0 released the consolidated switching mechanism, the FMU release policy,
and the event-localization fixes. The order below is what gates the paper and
the next release.

1. **Settle the detection-cost question before generating paper numbers.**
   EVID-01 now carries four measurements putting speculative model time at about
   half of all model time, with and without contact and with and without
   switching. HYB-03's rate-bounded rejection would move every performance
   number in both benchmark notebooks, and notebook 6 costs about 65 minutes per
   run. Decide whether it is in scope first, then measure once.
2. **Produce the numerical evidence.** EVID-02 and EVID-03 together on the
   smooth pendulum, so one refinement study answers convergence order and switch
   placement. Then EVID-04 for a representative horizon and EVID-05 for an
   independent-master comparison.
3. **Close the platform gap in the gate.** HARD-01 and HARD-02. Shipping
   `win64` binaries for the three fixture FMUs is cheap and removes the case
   where a green local run hides a real regression, which happened during the
   v0.3.0 work. Add standalone OpenSim contracts and a scheduled contact run.
4. **Finish the native lifecycle.** HARD-05 steps 2 through 5 and HARD-07 steps
   2 through 6. The capability probe and the `fmi2GetFMUstate` rollback path are
   the two with real leverage; re-exporting the demo FMUs with euler would
   remove the problem rather than working around it.
5. **Reduce speculative work.** HYB-01's escalation from report to rollback
   depends on HYB-02's re-tearing; HYB-04 pays off on macro steps that contain
   an event. HYB-05 is a one-line cleanup.
6. **Simplify the remaining internals.** MC-11, MC-12, MC-13. Remove dead
   adapter and state fields, consolidate switch history, and replace
   backend-private access with stable contracts.
7. **Improve time semantics incrementally.** TIME-04, then integer ticks in the
   master layer. Address TIME-01 through resolution negotiation before
   propagating ticks through every component API.
8. **Archive a reproducible artifact.** HARD-03 and REPRO-01, for the release
   that accompanies the paper.

## Definition of done

The runtime-switching redesign is complete, and shipped in v0.3.0:

- `set_switch_regions()` is the only public `MultiComponent` model-selection API;
- every runtime transition originates from one localized region-boundary crossing;
- state-dependent switches are localized independently of macro-step size;
- nonzero region bands provide signal hysteresis and no minimum-dwell state remains;
- active region identity is explicit and supports a model assigned to multiple regions;
- trial advances have no externally observable effects;
- reset/reinitialize is equivalent to a fresh component instance;
- every reachable localized mode has a validated rollback contract;
- state-transfer losses and preserved invariants are explicit and tested;
- generic and real-backend tests cover switching, rollback, and repeated runs.

One item from that list is still partial: `MasterPendulum` continues to depend
on private switching and backend internals (MC-12).

The repository is ready to serve as the paper baseline when:

- the convergence and switch-placement studies report error, work, and configuration together;
- the benchmark covers all intended regimes and is reproducible from archived raw data;
- FMU-only results agree with at least one independent master within declared tolerances;
- supported backends have meaningful automated coverage on every supported platform,
  including the scheduled slow FEM gate;
- environments and platform FMUs are pinned or attached to the release.
