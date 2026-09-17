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
- [`syssimx_examples/controlled_pendulum/`](syssimx_examples/controlled_pendulum/)

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

Five themes remain open, in rough order of what gates what:

1. **Reproducibility of the physics.** An identical FEM run does not reproduce
   itself while NGSolve threading is left at its default, and marginal contact
   events appear or vanish between runs. REPRO-02.
2. **Detection cost and correctness.** Roughly half of all model time is
   computed and rolled back, and detection still runs on a trajectory the
   system never commits. HYB-01 through HYB-05, EVID-01.
3. **Numerical evidence for the paper.** Convergence order and switch placement
   are unmeasured, and the benchmark is short. EVID-02 through EVID-05.
4. **Backend and platform coverage.** The validation gate is uneven, and a
   green local run does not imply a green CI run for anything touching FMU
   lifecycle. HARD-01, HARD-02.
5. **Native resource lifecycle.** The defective CVODE exports are still
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

MC-01 through MC-11 and MC-14 are resolved; see the changelog. What follows is
the remainder.

### MC-11 — Dead and duplicated abstractions obscure the real design

**Priority:** Medium

**Status:** Resolved after v0.3.0; summarized under ``Unreleased`` in the changelog.

The region-specific duplication is gone: one immutable configuration owns typed one-per-boundary
records, and `active_region_index` is authoritative. The following cleanup remains:

- [x] Remove unused `StateAdapter` and `state_adapters`.
- [x] Remove unused `_prev_state` and `_curr_state` fields.
- [x] Replace wrapper `sync_events` with typed records in the common component/system history.

**Suggested solution**

- [x] Remove dead fields rather than advertising an unused adapter mechanism.
- [x] Replace parallel switching dictionaries with immutable `SwitchRegions` and typed boundaries.
- [x] Store one authoritative active-region index and derive mode/component through properties.
- [x] Record a structured `ModeSwitchEvent` in the common system history.
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

**The guard's event-branch blind spot was fixed on 2026-09-12.** The accepted-trajectory check
now also runs after the advance to a located event, excluding crossings already seen by the trial
trajectory. A different crossing can therefore no longer hide merely because another event selected
the event-handling branch. Covered by `test_guard_is_armed_when_another_crossing_enters_the_event_branch`.

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

3. The reverse also happens: detection can locate a crossing that the accepted trajectory reaches
   only later. Dispatching at the located instant then fires the event early and again at the
   committed crossing. This is HYB-08, fixed in `v0.4.2` by withholding such events until the
   committed state has crossed.

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
[`report_internal_event()`](syssimx_examples/controlled_pendulum/components/fem/fem_pendulum.py#L704),
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
[`_initialize_component()`](syssimx_examples/controlled_pendulum/orchestration/master_pendulum.py#L424)
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

### HYB-07 — Localization can return an instant with no events, and the crossing is lost

**Priority:** High

**Status:** Fix implemented and covered by focused regression tests on 2026-09-12. A direct 0.9 s
contact smoke run then completed with 12 switches, 12 contacts, and zero `missed_events`; the 2 s
campaign horizon has not yet been repeated. The defect was reproduced at `v0.4.0-2-gbb7d0b4` and
blocked the contact campaign in `notebooks/03_switching.ipynb`.

**One consequence for the paper, not a defect.** The recovered event is the one that localized at
exactly the macro endpoint, so it now fires *on* a communication point: `min_off_grid_s = 3.49e-16`
in `T1.smoke.json`, against `5.47e-5` in the pre-fix 0.4 s run, which never hit one. The off-grid
offset is the statistic section 6.1 uses to separate this mechanism from a grid-snapped trigger, so
it must be reported as a distribution over the switches rather than as a minimum.

**Open for the paper.** The fix postdates `v0.4.0`, so the paper baseline revision changes and
`results_predate_tagged_revision` in the comparison manifest must be re-resolved against a new tag.
The confirming artifact is a `.smoke` file at `n_repeats = 1` with a dirty measured surface.

`MasterPendulum` aborts partway through a contact run with

```
RuntimeError: MasterPendulum: Boundary 0 crossed in direction -1 from
inconsistent region 2; expected 1.
```

The message names the symptom, not the cause. The wrapper is in region 2 (`FMU`) while the
region key has fallen to the inner boundary, which can only happen if the intervening
`region_boundary_1` transition never ran. That check in
[`_resolve_region_target()`](syssimx/core/multi_comp.py#L541) is doing its job: without it
the run would commit an `FMU -> FEM` handover that the region map does not define, and that
transfer would enter the T1 handover table as evidence.

**What the instrumented run shows.** Logging every detection, every localization and every
committed switch over a 0.9 s contact run gives 14 detections, of which one is lost:

```
[0.3850,0.3860]  located 0.38529688  handled=True   region_boundary_1   -> OpenSim to FMU
[0.4650,0.4660]  located 0.46600000  handled=False  region_boundary_1   <-- dropped
[0.4950,0.4960]  located 0.49519531  handled=True   region_boundary_0   -> RuntimeError
```

The crossing at `[0.465, 0.466]` **was detected and was localized**. No handler ran, no switch
was committed, and the macro step then advanced past it. Eighty milliseconds later the key
reached the inner boundary and the consistency check refused the two-region jump.

This is not HYB-01. Detection saw this crossing on its own trial trajectory. The event is
dropped after localization.

**Mechanism before the fix.** [`_locate_event_time()`](syssimx/system/algorithms/hybrid.py#L536)
ended at

```python
t_event = right
located_events = self._crossing_brackets_between(
    event_sources, indicators_left_vals, indicators_right_vals, left, right,
)
if not located_events:
    located_events = [
        event for event in hint_events
        if event.t_left <= t_event <= event.t_right + self.tol_time
    ]
return DenseTime(t=t_event, micro=0), located_events
```

`hint_events` is `initial_crossings` filtered to brackets strictly inside the macro interval,
so it holds only internal micro-step hints. A crossing found from a macro-endpoint sign change
is not in it. When the re-evaluation over `[left, right]` yields nothing, the fallback
therefore yields nothing either, and the method returns a located instant with an **empty**
event list.

The caller then advances to that instant and dispatches nothing:

```python
dense_time, initial_events = self._locate_event_time(...)
...
self.gauss_seidel_algorithm.step(system, t_left, dense_time.t - t_left)
while event_pairs and current_time.micro < self.max_microsteps:
```

The loop body never executes with an empty `event_pairs`. The miss is then permanent for the
same reason as in HYB-01: `detect_event_crossings()` requires `prev_sign > 0`, so once the
indicator has settled on the far side the crossing can never be observed again.

The hint path already guarded against exactly this, at
[`hybrid.py#L596`](syssimx/system/algorithms/hybrid.py#L596), with the comment *"Never locate
an instant and then dispatch nothing"* and a second fallback to `initial_crossings`. The
bisection path had the first fallback but not the second.

In the recorded run the localized time was `0.46600000`, exactly the right edge of the macro
interval, which means bisection never narrowed and the final re-evaluation over the full
interval disagreed with the detection that opened it.

**Why the existing guard was silent before the fix.** `raise_on_missed_event = True` was set and
recorded in
the artifact provenance, and it never fired.
[`_report_missed_crossings()`](syssimx/system/algorithms/hybrid.py#L318) was called only inside
the `if not crossings:` branch at
[`hybrid.py#L167`](syssimx/system/algorithms/hybrid.py#L167). A crossing dropped inside the
event-handling branch is structurally invisible to it. **Absence of a missed-event warning is
not evidence that no event was missed.**

**What is ruled out.** A three-region `MultiComponent` using the `MasterPendulumSwitchConfig`
policy verbatim, driven by a prescribed ramp with no FEM, no contact and no coupling,
completes correctly when two boundaries fall inside one macro step (tested at 0.44 and 0.87
steps between the armed edges), producing sequential single-region transitions. Dispatch
ordering is not the cause. `threshold_for()` also returns the same value for boundary 0 in
regions 1 and 2, so committing a switch never moves another boundary's indicator across zero.

**Implemented fix**

- The bisection fallback now matches the hint path: when `located_events` is empty, it falls
  back to `initial_crossings` whose bracket contains `t_event`, so a localized instant always
  dispatches the crossing that opened it.
- An empty result after both fallbacks is recorded as a missed event and routed through the same
  warning/exception policy as accepted-trajectory misses, so
  `raise_on_missed_event` covers it.
- The missed-event guard now also runs on the event-handling branch and excludes crossings already
  detected on the trial trajectory.
- `_resolve_region_target()` remains strict. It is the only reason this
  surfaced instead of silently producing an undefined `FMU -> FEM` handover. Do not relax it
  to tolerate multi-region jumps.

The focused tests are `tests/unit/system/test_hybrid_localization_fallback.py` and
`tests/unit/system/test_hybrid_missed_events.py`. The direct 0.9 s smoke run completed in 756.843 s;
the formerly dropped transition committed at `0.46600000` (`FMU -> OpenSim`), followed by the valid
`0.49519531` transition (`OpenSim -> FEM`). Closing HYB-07 still requires the 2 s contact horizon.

**Reproduction.** `notebooks/03_switching.ipynb` with `HORIZON_S = 0.9`, the contact scenario,
`event_tol_time = 1e-5`, `CAMPAIGN = False`. The exact instant moves between runs under
REPRO-02; the failure recurred on every attempt at 0.9 s and 2.0 s.

### HYB-08 — One wall impact is dispatched twice, 31 microseconds apart

**Priority:** High

**Status:** Fixed in code on 2026-09-17, for release in `v0.4.2`. The cause is
HYB-01 acting in the reverse direction. Covered by
`tests/unit/system/test_hybrid_premature_dispatch.py`. Closing it still needs
the 03_switching rerun at `v0.4.2` to show 14 contacts against 14.

**Observed.** The 1.0 s contact run of `notebooks/03_switching.ipynb` at
`paper-baseline-2026-09-16-3-gaadfe0b`, starting in FMU with the 0.30 rad launch
gate, located **15 contacts against the reference's 14**. The extra one doubles
the fifth contact of the first cluster:

```text
0.33198125
0.33201250    3.125e-05 s later
```

Everything else pairs one-to-one. The 0.4 s run with the same settings shows the
same pair, as 6 contacts against 5.

**Consequence for the evidence.** Contacts are compared pairwise by index, so the
extra event shifts every later pair and the run self-classifies as
`NOT COMPARABLE` with `max |delta| = 1.824e-01 s`. That number describes the
misalignment, not the trajectory. Paired nearest-neighbour with the duplicate
removed, all 14 reference contacts match and the largest deviation is
**7.1e-03 s**. The first dispatch left `omega` unchanged, because the FEM plant
ignores `omega_invert`, so the trajectory itself is not affected; only the
contact count and the pairing are.

**Cause, confirmed by the dispatch diagnostic.** At the first dispatch the
committed state had **not** reached the wall:

```text
dispatch 0.33198125   theta = +6.791e-05 rad   fem.gap = +1.848e-05 m
trial trajectory      theta(0.3320) = -1.416e-04 rad
committed trajectory  theta(0.3320) = +1.797e-05 rad
committed crossing    about 0.3320032 s, 22 us after the first dispatch
```

Localization bisects on the trial trajectory, which holds `Drive.tau` at the
left edge of the macro step. The accepted advance re-reads the updated torque
(HYB-01), so the trial crossing lies about 22 us ahead of the committed one.
The algorithm dispatched at the trial instant, on a state still on the positive
side. The committed crossing then fell into the next macro step, where it was
detected and dispatched again. The duplicate filter lives for one call to
`step()`, so it never saw the first dispatch.

Two explanations recorded earlier were rejected by the same data. Neither signal
had crossed at the first dispatch, so it was not the FEM gap hint and the angle
indicator disagreeing. `theta` never rose between the two dispatches, so it was
not a micro-bounce of the penalty contact.

**Attempt 1, reverted: widen the duplicate-root window.** A window tied to the
located bracket width still produced 6 contacts against 5, because the two
dispatches fall in different macro steps. It was also unsafe, since after the
HYB-07 fallback a bracket can be a whole macro step wide.

**Fix.** After the accepted advance to the located instant, `HybridAlgorithm.step`
checks each located event against the committed state
(`_premature_event_pairs`). An event counts as reached if its indicator has
changed sign since `t_left`, or if its source reported a hint for it during the
accepted advance. The second clause keeps hint-only events from HYB-07. Events
not yet reached are withheld. If nothing is left to dispatch, detection resumes
from the located instant and finds the crossing where the committed state makes
it. `max_deferrals` (default 50) bounds the loop per macro step. Beyond it the
event is dispatched with a warning.

**Behaviour change.** Event instants move from the trial crossing to the
committed one. In the case study that shift is tens of microseconds. Switch
instants that depend on contact handling can move as well, so V1, V2, T1 and T2
must be regenerated at `v0.4.2`.

### HYB-09 — The FEM region clears the bounce envelope by only 3.1 %

**Priority:** Medium

**Status:** Accepted on purpose 2026-09-17. Breakpoint kept at 0.075 rad.

The FEM region is entered below the lower edge and left above the upper one, so a
whole contact episode has to fit under the upper edge. The 1.0 s contact run
measured:

```text
bounce peak       max 0.077575 rad, median 0.065795 rad
region edges      enter below 0.070000, leave above 0.080000 rad
clearance to exit  +0.002425 rad, 3.1 % of the peak
```

A bounce 3.1 % higher would leave FEM in the middle of an episode and return at
once, adding a switch pair.

**Raising the breakpoint was tried and rejected.** At 0.092 rad the clearance
rose to 31.1 %, but the first-cluster contact-time deviation from the rigid
reference roughly tripled, from 3.95e-03 s to 1.15e-02 s, because more of the
swing ran in the deformable model. The case study exists to reproduce ideal
elastic contact with a hyperelastic FEM, so agreement with the rigid reference
matters more here than margin. The extra FEM time at 0.092 rad is small, so part
of the growth likely comes from the handover itself: the FEM starts undeformed at
each switch, and the entry angle sets the elastic transient it begins with. That
is worth reporting under RQ2.

**Why the small margin is acceptable.** With one NGSolve thread the run is
bit-identical, so the 3.1 % margin cannot flip between repetitions. It can flip
under any change to parameters, FMUs, toolchain, or package versions. The
bounce-envelope cell in `03_switching` reports the clearance on every run and is
the guard. The value is declared in section 5 of the manuscript, and figure F7
draws the region strip to scale from it.

**Provenance gap, fixed in the notebook.** `Scenario.provenance()` records
`switch_threshold_rad`, `switch_band_rad` and `region_modes`, but
`MasterPendulum` takes its region map from `MasterPendulumSwitchConfig` and
ignores them, so `T1.json` reported a two-region map for a three-region run.
`03_switching` now builds the switch config from `FEM_BREAKPOINT_RAD` and records
the installed map under `region_map`.

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

- Run a short compatibility spike with PyFMI and CoFMPy, then select one independent master.
- Compare the same FMU trajectory and events; avoid making two comparison toolchains a requirement.

### Execution plan for EVID-02 through EVID-05

This section is the single task list for the paper evidence. The notebooks remain reporting
artifacts; they must not become a second source of experiment definitions or manually entered
numbers. Do not start the expensive runs until the HYB-03 scope decision is closed and the runtime
behaviour is frozen at a recorded commit.

#### Task E1 — Freeze the protocol and raw-data contract

**Dependencies:** HYB-03 scope decision.

**Acceptance criteria**

- [ ] Record the framework commit, operating system, Python and backend versions, model-artifact
  hashes, solver tolerances, initial conditions, time horizon, macro-step grid, warm-up policy, and
  repetition count in a machine-readable manifest.
- [ ] Define one tidy raw-data schema covering run identity, strategy, backend, step size, repeat,
  state errors, switch errors, event counts, work counters, and timing categories.
- [ ] Provide one command that runs a cheap smoke configuration and validates the manifest and raw
  files without executing the full FEM campaign.

**Likely files:** a small runner under `scripts/evidence/`, shared experiment helpers under
`syssimx_examples/controlled_pendulum/`, and raw outputs under a dedicated `evidence/` directory.

**Verification checkpoint:** review the protocol and one smoke-run artifact before any long run.

#### Task E2 — Combine convergence and switch-placement refinement

**Dependencies:** E1. Closes EVID-02 and EVID-03 together.

**Acceptance criteria**

- [ ] Use the smooth, contact-free pendulum with identical parameters and state-transfer rules for
  localized and communication-grid switching. Use at least four step sizes with a refinement ratio
  of two and an independently computed reference finer than the smallest reported step.
- [ ] Record errors in `theta` and `omega` (final and trajectory norms), switch-time error, switch
  count and order, accepted/trial/bisection work, and wall time for every refinement level.
- [ ] Report pairwise and fitted observed order, plus a reference-sensitivity check. Do not claim an
  asymptotic order if the finest levels do not show a stable slope or if event sequences differ.

**Likely reporting files:** `notebooks/02_hybrid_verification.ipynb` for convergence and
`notebooks/05_casestudy_model_switching.ipynb` for placement, both loading the same raw refinement
data rather than rerunning independent variants.

**Verification checkpoint:** inspect the refinement table and event sequences before performance
measurements; a missing or additional switch invalidates the corresponding error comparison.

#### Task E3 — Run the representative performance campaign

**Dependencies:** E2 and a frozen implementation. Closes EVID-04.

**Acceptance criteria**

- [ ] Choose a horizon that contains enough repeated switches to make initialization and one-off
  effects non-dominant; document that choice from a pilot run rather than selecting it after seeing
  the final ratios.
- [ ] Measure full-model and switched cases with and without contact. Separate accepted, trial,
  bisection, transfer, backend-initialization, orchestration, and total wall time.
- [ ] Use a warm-up followed by at least five repetitions per reported case, or preregister a
  resource-based reduction to three. Report every observation and summarize with median and spread,
  not only the fastest run.

**Likely reporting files:** `notebooks/06_casestudy_performance.ipynb` and
`notebooks/07_casestudy_performance_nocontact.ipynb`, rendering archived raw timing data.

**Verification checkpoint:** finish one complete pilot matrix, estimate the overnight budget, and
review it before launching repetitions. Preserve failed runs and reasons instead of silently
discarding them.

#### Task E4 — Cross-validate the FMU-only baseline

**Dependencies:** E1. May run independently of E2 and E3 after the protocol is fixed. Closes
EVID-05.

**Acceptance criteria**

- [ ] Select one independent master after a short compatibility spike; record why it was selected
  and pin its version. Do not make installing two comparison frameworks a requirement.
- [ ] Run the same FMU, inputs, initial state, horizon, and communication grid in SysSimX and the
  independent master, with solver-setting differences documented.
- [ ] Compare aligned `theta`/`omega` trajectories and event times against declared absolute and
  relative tolerances. Explain any discrepancy rather than tuning tolerances after the comparison.

**Verification checkpoint:** archive a minimal comparison run before expanding to the full horizon.

#### Task E5 — Produce the paper reproduction artifact

**Dependencies:** E2 through E4. Completes the numerical part of REPRO-01.

**Acceptance criteria**

- [ ] Every paper figure and table is generated from committed or archived raw files by one
  documented command; notebooks contain no hand-copied result values.
- [ ] Archive the protocol, raw data, environment metadata, logs, artifact hashes, and rendered
  outputs together, tied to one immutable framework commit or release tag.
- [ ] Reproduce the cheap refinement and cross-validation paths in a clean environment; document the
  expected runtime and hardware for the slow FEM campaign rather than requiring reviewers to rerun
  it interactively.

**Final checkpoint:** review claims against the archived tables, then freeze the paper release and
update EVID-02 through EVID-05 and REPRO-01 with links to their evidence artifacts.

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

**Status:** Resolved after v0.3.0; summarized under ``Unreleased`` in the changelog.

SciPy, Matplotlib, ipywidgets, traitlets, and pydot are not imported by the core `syssimx` package
according to the recorded audit.

**Suggested solution**

- [x] Move them to demo, documentation, or visualization extras as appropriate.
- [x] Update the Sphinx and ReadTheDocs environments in the same change, particularly for Matplotlib,
  so the strict documentation build remains green.

### HARD-04 — Release metadata is incomplete

**Priority:** Low

**Status:** v0.4.0 prepared on 2026-09-06. `syssimx/__version__.py` and `CITATION.cff` read 0.4.0,
`CHANGELOG.md` closes the entry with that date, and the tag and PyPI publication are still pending.
The bump is **minor, not patch**: the release removes public API (`StateAdapter`, `state_adapters`,
`sync_events`) and turns three previously silent behaviours into errors. Both author-supplied
identifiers are still missing.

- The `orcid` line in `CITATION.cff` is still commented out, because no ORCID is registered for the
  author yet. It was never a matter of deferral; a wrong ORCID resolves to nothing or to another
  person, so the line stays commented until a real one exists.
- The `doi` line is still commented out, and no Zenodo deposit exists. A version DOI cannot be
  minted before the release it identifies, so it follows the tag.

**Suggested solution**

- Tag `v0.4.0` and let the PyPI workflow publish it.
- Archive the release on Zenodo, then uncomment `doi` with the version DOI it mints. This is the
  same deposit REPRO-01 needs, so do it once and reference it from both.
- Register an ORCID and fill the line in a later release. It blocks nothing.
- Record the release procedure in `CONTRIBUTING.md`. `scripts/bump_version.py` rewrites only
  `syssimx/__version__.py`, while `CHANGELOG.md` and `CITATION.cff` also carry the version and are
  edited by hand, which is easy to miss.

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

### REPRO-02 — FEM results are not reproducible run to run

**Priority:** High

Repeating an identical FEM run changes the answer. The `FemToFemPendulum` control in
`notebooks/06_casestudy_performance.ipynb` puts two identically parameterised FEM pendulums behind
one region map, so the physics is the same on both sides of every switch. Run twice in the same
process, it resolved five wall contacts and then four. Under `ngsolve.SetNumThreads(1)` three runs
produced bit-identical contact *and* switch instants. Raw data, figures, and the driver scripts are
in `results/determinism/`.

The cause is `FEMPendulum._do_step_internal`, which wraps its whole sub-stepping loop in
`with TaskManager():` (`syssimx/components/fem.py`) without pinning a thread count. NGSolve's
parallel reductions accumulate in scheduling-dependent order, so results are not bitwise
reproducible. The component makes a determinism-affecting choice silently and records it nowhere.

`wall_descents` equalled the located contact count in every run, so this is not a detection failure
and is unrelated to HYB-01. The trajectories genuinely differ.

Scope. The first four bounces are reproducible even with threading on; all scatter falls in the
fifth bounce and the departure after it, where the setpoint lifts the pendulum off the wall and
about a millisecond of phase decides whether a fifth contact occurs. So the defect does not
randomise a run — it decides marginal events. That is worse for evidence than uniform noise,
because most runs agree and the disagreement is rare enough to miss in a handful of repetitions.

What it invalidates.

- Any physics claim resting on a single run: contact sequences, handover quality, trajectory error.
  `n = 1` only carries meaning once a run is deterministic.
- The notebook 6 self-check, which compares the located contact instants of two single runs. Without
  a baseline noise band its threshold cannot mean anything.
- EVID-01's contact-case measurements are unaffected: those are medians over repetitions with a
  drift check, which is the correct treatment for a varying quantity.
- RQ2 in the paper's `evidence_plan.md`. NB5's "six switches, zero contract violations" is an `n = 1`
  observation of a quantity that varies unless that notebook already pinned threads. Check which.

**Revised 2026-09-13 for physics evidence.** `notebooks/06_determinism.ipynb`
compared the full-FEM case bit for bit, one process per thread count. One thread
was bit-identical within and across processes. Six threads, equal to the physical
core count, was not, and neither was the default. A fixed count above one is
therefore not enough. `03_switching` now pins one thread through
`Scenario.ngsolve_threads` and takes one run; `record()` marks a run reproducible
only at one thread. Timing evidence in `04_performance` keeps the default, which
answers the objection below: each result declares its setting.

**Superseded decision, 2026-09-11.** The original policy left NGSolve
threading unpinned and repeated all FEM-backed evidence. The
`06_determinism.ipynb` result above invalidated the assumption that a fixed
multi-thread count was reproducible.

**Current policy, 2026-09-13.** `03_switching` pins one NGSolve thread and uses
one deterministic run for correctness and handover evidence. `04_performance`
keeps default threading and reports repeated timing measurements plus distinct
event-sequence classes. `record()` declares a single run reproducible only when
the recorded thread count is one. Existing unpinned physics artifacts remain
inadmissible.

**Remaining work**

1. Re-run every retained physics artifact with the one-thread policy before it
   is quoted.
2. Keep default threading for timing evidence and report its observed spread.
3. State marginal-event sensitivity as a limitation when scheduling changes the
   contact sequence.

## Prioritized next steps

v0.3.0 released the consolidated switching mechanism, the FMU release policy,
and the event-localization fixes. The order below is what gates the paper and
the next release.

**HYB-07 verification comes before all of it.** The localized-empty-dispatch defect is fixed under
focused tests and the 0.9 s contact reproduction completes, but the 2.0 s campaign horizon still
needs to complete before the switching campaign resumes. Every item below assumes a run that
finishes.

1. **Re-run retained physics evidence with one NGSolve thread.** REPRO-02.
   `03_switching` now pins one thread and uses one deterministic run; old
   unpinned artifacts remain inadmissible. Timing evidence stays on default
   threads and uses repetitions.
2. **Settle the detection-cost question before generating paper numbers.**
   EVID-01 now carries four measurements putting speculative model time at about
   half of all model time, with and without contact and with and without
   switching. HYB-03's rate-bounded rejection would move every performance
   number in both benchmark notebooks, and notebook 6 costs about 65 minutes per
   run. Decide whether it is in scope first, then measure once.
3. **Produce the numerical evidence.** EVID-02 and EVID-03 together on the
   smooth pendulum, so one refinement study answers convergence order and switch
   placement. Then EVID-04 for a representative horizon and EVID-05 for an
   independent-master comparison.
4. **Close the platform gap in the gate.** HARD-01 and HARD-02. Shipping
   `win64` binaries for the three fixture FMUs is cheap and removes the case
   where a green local run hides a real regression, which happened during the
   v0.3.0 work. Add standalone OpenSim contracts and a scheduled contact run.
5. **Finish the native lifecycle.** HARD-05 steps 2 through 5 and HARD-07 steps
   2 through 6. The capability probe and the `fmi2GetFMUstate` rollback path are
   the two with real leverage; re-exporting the demo FMUs with euler would
   remove the problem rather than working around it.
6. **Reduce speculative work.** HYB-01's escalation from report to rollback
   depends on HYB-02's re-tearing; HYB-04 pays off on macro steps that contain
   an event. HYB-05 is a one-line cleanup.
7. **Simplify the remaining internals.** MC-12 and MC-13. Replace
   backend-private access with stable contracts and optionally centralize mode
   names.
8. **Improve time semantics incrementally.** TIME-04, then integer ticks in the
   master layer. Address TIME-01 through resolution negotiation before
   propagating ticks through every component API.
9. **Archive a reproducible artifact.** REPRO-01, for the release that
   accompanies the paper.

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
