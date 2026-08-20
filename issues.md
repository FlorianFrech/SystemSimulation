# SysSimX — Open Issues and Runtime-Switching Redesign

> Repository-level source of truth for framework work, evidence generation, release hardening, and the runtime-switching redesign.

## Recorded baseline

The last recorded full gate, at `f4895a7` / v0.2.0, was **645 passed, 1 skipped**, with Ruff,
MyPy, and the strict Sphinx build clean. The skipped case was the win64 FMU fixture. Treat this as
a historical baseline until the current working tree is rerun; it is not a claim that the present
uncommitted changes have passed the same gate.

## Scope

This document evaluates the runtime model-switching implementation in:

- [`syssimx/core/multi_comp.py`](syssimx/core/multi_comp.py)
- [`syssimx/system/algorithms/hybrid.py`](syssimx/system/algorithms/hybrid.py)
- [`syssimx/system/system.py`](syssimx/system/system.py)
- [`demos/ControlledPendulum/src/master_pendulum/`](demos/ControlledPendulum/src/master_pendulum/)

The `MasterPendulum` example combines FEM, OpenSim, and FMU implementations behind a
single `MultiComponent` interface. It is therefore the main reference case for evaluating
state transfer, event localization, rollback, hysteresis, lifecycle management, and the
separation between switching configuration and switching execution.

## Executive summary

The central abstraction is useful: `MultiComponent` exposes a stable port interface, advances
one active model, and transfers physical state when the active model changes. The implementation
also contains a capable event-localized switching path.

The main problem is that switching decisions, event registration, hysteresis, rollback protection,
state transfer, logging, and lifecycle management have accumulated inside the same class. There
are now three partially overlapping decision mechanisms with different semantics. The performance
case-study notebook now configures `MasterPendulum` with localized regions, but the component's
fallback behavior and other case-study notebooks still use grid-polled selectors.

The design decision is to expose exactly one public runtime-switching mechanism:
generalized, event-localized region switching through `set_switch_regions()`. It is the only
existing mechanism that combines declarative configuration, support for three or more models,
direction-aware transitions, event-time localization, and signal hysteresis. Grid-polled selectors
and user-managed fixed-target indicators should be removed after all examples and tests migrate.

The recommended direction is an incremental consolidation rather than a rewrite:

1. Fix the concrete correctness and lifecycle defects.
2. Generalize `set_switch_regions()` as the sole public switching API.
3. Remove `mode_selector`, public `add_switch_indicator()`, dwell timing, pending repair, and the
   arbitration concepts needed only when multiple mechanisms coexist.
4. Keep state transfer and checkpoint/trial behavior as explicit internal contracts.
5. Complete the case-study migration and add cross-backend integration tests before deleting the
   legacy paths.

## Existing runtime-switching mechanisms

| Mechanism | Trigger | Placement | Current MasterPendulum use | Design decision |
|---|---|---|---|---|
| `mode_selector` | Function polled before a positive macro step | Communication grid | Default fallback; still used in notebooks 5 and 6 | Remove after migration |
| `add_switch_indicator()` | User-defined zero crossing with a fixed target | Bisection-localized event time | Supported but not configured by default | Remove from the public switching API |
| `set_switch_regions()` | Generated boundary events for an ordered scalar region map | Bisection-localized event time | Configured by `notebooks/performance.ipynb` | Generalize and retain as the sole public mechanism |
| `_switch_mode()` | Direct internal invocation | Caller-provided time | Private execution primitive | Keep private as a transactional commit operation, not a switching mechanism |

### Grid-polled selector

[`MultiComponent._do_step_internal()`](syssimx/core/multi_comp.py#L947) asks
[`_select_target_mode()`](syssimx/core/multi_comp.py#L982) for a target before advancing the
active model. If the target differs, the switch happens at the current communication point.

`MasterPendulum` installs either a time-based selector or an angle-based selector during
initialization. See
[`MasterPendulum._initialize_component()`](demos/ControlledPendulum/src/master_pendulum/orchestration/master_pendulum.py#L75).

### Fixed-target localized indicators

[`add_switch_indicator()`](syssimx/core/multi_comp.py#L529) adds a wrapper-owned event indicator
whose event requests one target model. The `System` registers the wrapper as its own listener and
selects `HybridAlgorithm` when event sources exist.

The hybrid algorithm speculatively advances the event source, detects a sign change, rolls back,
localizes the event by bisection, advances the real system to the event time, and dispatches the
event. Switching is disabled during speculative execution so a snapshot is not restored into a
different active model.

### Declarative switch regions

[`set_switch_regions()`](syssimx/core/multi_comp.py#L623) maps one scalar key onto ordered model
regions. It generates directional boundary events around every breakpoint. A nonzero `band`
provides Schmitt-trigger behavior and is the sole chatter-prevention mechanism in the target
design. Minimum dwell timing and its pending-repair state should be removed.

### State transfer

All decision paths eventually call
[`_perform_state_transfer()`](syssimx/core/multi_comp.py#L1036):

1. Export physical state from the outgoing model with `get_state()`.
2. Adapt it for the target model.
3. Replay the most recently received inputs.
4. Import the state into the incoming model with `set_state()`.
5. Refresh incoming output ports.
6. Update `active_mode` and `active_comp`.
7. Record the committed switch and active region index.

## Findings and proposed solutions

### MC-01 — The case-study migration to localized switching is incomplete

**Priority:** High

`notebooks/performance.ipynb` now declares a three-model region map on `|theta|`, with breakpoints at
6° and 13° and a 1° band. `MasterPendulum._initialize_component()` also avoids installing its
fallback selector when switch indicators or a region map are already configured. This closes the
mechanism-level conflict in that path.

The migration is not complete: case-study notebooks 5 and 6 still use `mode_selector`, and the
component's default contact behavior still implements its angle regions through
[`_gap_based_mode_selector()`](demos/ControlledPendulum/src/master_pendulum/orchestration/master_pendulum.py#L184).
Those switches remain macro-grid placed. A physical threshold crossing can therefore precede the
actual switch by as much as one macro step, during which the system advances the wrong model and
supplies its dynamics to coupled components.

The method name is also misleading: it reads `theta`, not an actual contact gap.

The configured `dwell_time = 0.05 s` is longer than the roughly `0.039 s` contact-bounce interval
seen in the tutorial. It suppresses physically valid full-band recrossings and requires pending
repair logic. It should be removed; the region band should be sized to reject threshold chatter.

**Suggested solution**

- Migrate notebooks 5 and 6 to `set_switch_regions()`. A temporary comparison with
  `mode_selector` may be used to document the migration, but the selector path should not remain as
  a supported alternative.
- Re-run `performance.ipynb`; its new three-model occupancy and speculative-work results are not
  yet measured.
- Configure the default contact region map through `set_switch_regions()`.
- Use a canonical key in radians, for example `abs(theta)`.
- Reconcile the performance notebook's 6°/13° breakpoints with the intended 0.075 rad/15° contact
  thresholds, then define the selected values once in typed configuration.
- Configure explicit, nonzero entry/exit bands.
- Remove the time-based initial hold from runtime switching. If FEM requires preparation, perform
  it as an explicit initialization phase before region switching is armed.
- If actual contact distance is the intended signal, expose a shared `contact_distance` or
  `contact_proxy` output across all three models and use that instead of angle.

**Acceptance criteria**

- State-dependent switches are localized independently of the macro-step size.
- Switch times converge according to `tol_time`/`tol_value`, not `dt`.
- The configuration name and documentation describe the signal actually used.
- The performance notebook contains fresh executed results for occupancy, switch count, and
  speculative work.

### MC-02 — MasterPendulum bypasses base-class region initialization

**Priority:** High

The base `MultiComponent._initialize_component()` initializes all models and arms initial region
reconciliation. `MasterPendulum` overrides the entire method to initialize FEM first, synchronize
parameters, and initialize the remaining models. It cannot safely call `super()` because doing so
would initialize the models twice.

As a result, a region map declared on `MasterPendulum` does not receive the base class's initial
reconciliation behavior. An initial mode inconsistent with the initial signal can persist until a
later crossing.

**Suggested solution**

Split the lifecycle into template hooks owned by `MultiComponent`, for example:

- `_prepare_models(t0)`
- `_initialize_models(t0)`
- `_after_models_initialized(t0)`

The base `initialize` path should always run shared post-initialization invariants, including port
validation, active-reference validation, initial region reconciliation, and generated-event setup.
`MasterPendulum` should override only the model-ordering/parameter-synchronization hook.

**Acceptance criteria**

- A region-configured `MasterPendulum` reconciles an inconsistent initial mode at `t0`.
- No submodel is initialized twice.
- Shared switching lifecycle logic cannot be skipped accidentally by a subclass.

### MC-03 — Speculative hybrid advances are not side-effect-free

**Priority:** High

[`HybridAlgorithm._trial_step()`](syssimx/system/algorithms/hybrid.py#L398) toggles the private
`_record_history` and `_allow_mode_switching` flags. It does not suppress other externally visible
effects such as monitoring updates, visualization redraws, callbacks, or backend-specific history
writes.

This matters for the master pendulum because FEM substeps invoke monitoring/visualization hooks,
and `MasterPendulum._update_output_states()` also updates monitoring and the FEM scene. These hooks
can observe speculative endpoint and bisection states that are later rolled back.

`FMUPendulum.restore_state()` additionally calls `_record_outputs()` unconditionally, so repeated
rollback during localization can pollute its component history.

**Suggested solution**

- Introduce a public, recursive `component.trial_context()` or checkpoint transaction.
- Make the context suppress all observational side effects: histories, monitoring, visualization,
  notifications, synchronization logs, and switching.
- Require child components of a composite to enter the same trial context.
- Make restore operations pure with respect to history and observers.
- Perform explicit `commit()` work only for accepted advances.

**Acceptance criteria**

- Event detection and bisection leave histories, monitors, scenes, switch logs, and callbacks
  unchanged.
- The active backend and every nested backend are restored to the same accepted state and time.
- Tests cover FEM/FMU-style backend side effects, not only scalar mock components.

### MC-04 — Reset does not restore the switching lifecycle

**Priority:** High

[`MultiComponent.reset()`](syssimx/core/multi_comp.py#L1391) resets the wrapper and submodels but
does not restore the original mode or reset all switching metadata. In particular:

- `active_mode` and `active_comp` remain at the final mode of the previous run.
- `sync_events` remains populated.
- Initial region reconciliation is not rearmed.
- An automatically installed `mode_selector` remains configured.

A subsequent run can therefore start in the wrong mode and region, retain a legacy switching path,
and mix switch records from multiple runs.

**Suggested solution**

- Clear `active_region_index` on reset and recompute it from the switching signal at initialization;
  derive `active_mode` and `active_comp` from the region assignment.
- Clear switch logs by default, or provide an explicit `preserve_history` option.
- Rearm initial region reconciliation during reinitialization.
- Keep the immutable region configuration across reset while recreating its runtime event state.
- Remove an automatically installed selector during the migration and then remove selector support.

**Acceptance criteria**

- `reset(); initialize(t0)` behaves like constructing a new equivalent component.
- Repeated runs produce independent switch histories and identical initial region behavior.

### MC-05 — `band=0` creates coincident directional events

**Priority:** High

`set_switch_regions()` defaults `band` to zero. In that case the rising and falling indicators for
one breakpoint use the same threshold. Event localization lands at that threshold, and
[`HybridAlgorithm._collect_events_at_time()`](syssimx/system/algorithms/hybrid.py#L696) collects all
indicators whose magnitude is within `tol_value` without preserving the direction that crossed.
Both directional events can therefore be dispatched for one physical crossing.

This can emit incorrect event ports, notify unrelated listeners, or trigger the simultaneous-event
commutativity path.

**Suggested solution**

- Require a nonzero band for every boundary so entry and exit thresholds are distinct.
- Represent each region boundary once rather than as two independently dispatchable public events.
- Preserve the detected crossing direction and final before/after sign bracket through localization.
- Resolve the destination region from the boundary plus direction and dispatch exactly that
  transition.

**Acceptance criteria**

- Exactly one directed region transition is dispatched for one crossing.
- Event listeners do not receive the opposite-direction event.
- The default configuration is safe.

### MC-06 — Region identity is ambiguous when a mode appears more than once

**Priority:** Medium

Validation rejects equal neighboring modes but permits a map such as `A, B, A`.
`SwitchRegions.index_of()` returns only the first occurrence, so the active mode cannot identify
whether the component occupies the lower or upper `A` region. Hysteretic settlement may therefore
start from the wrong region near a boundary.

The fallback from an unknown mode to region zero also hides invariant violations.

**Suggested solution**

- Track `active_region_index` as the authoritative runtime identity.
- Derive `active_mode` and `active_comp` from the region assignment.
- Permit repeated model assignments in disconnected regions.
- Raise when runtime state is inconsistent with the configured region map instead of silently using
  region zero.

### MC-07 — Minimum dwell time duplicates and weakens region hysteresis

**Priority:** Medium

Minimum dwell time suppresses a transition based on elapsed time rather than the switching signal.
The implementation must then remember `_pending_region_repair` and later poll the current region to
recover a crossing that was deliberately ignored. This adds temporal state, delayed transitions,
and grid-placement risks to a mechanism that already has Schmitt-trigger region bands.

For the intended region model, a signal that crosses one threshold but remains inside the band does
not switch back. A signal that crosses the entire band represents a real region transition and
should not be suppressed merely because it happened soon after the previous transition.

**Suggested solution**

- Remove `dwell_time`, `last_switch_time`, `can_switch()`, and the minimum-dwell configuration.
- Remove `_pending_region_repair` and all deferred/polled repair behavior.
- Retain nonzero per-boundary region bands as the only chatter-prevention mechanism.
- If noisy measurements can traverse the full band spuriously, widen the band or filter the
  switching signal explicitly rather than adding a second time-based switching rule.

**Acceptance criteria**

- Every full-band crossing produces one localized transition regardless of time since the previous
  transition.
- Remaining region state consists only of the active region and generated boundary-event state.
- No dwell or pending-repair concept remains in the public API, implementation, or tests.

### MC-08 — Rollback capability is checked only for the current mode

**Priority:** Medium

`MultiComponent.supports_rollback` delegates to the active component. A wrapper-level switch
indicator can therefore be registered while the initial model supports rollback even if another
reachable mode does not. After switching, the system's event classification remains active but a
later checkpoint can fail.

The same dynamic behavior applies to physics event exposure: `has_state_events` depends partly on
the currently active child, while system classification occurs during initialization.

**Suggested solution**

- Define composite capabilities from all modes reachable through the configured regions.
- For localized switching, require rollback support from every reachable mode.
- Alternatively, reject regions whose models cannot participate in localized event handling.
- Keep system event capability stable after initialization.

### MC-09 — Multiple switching mechanisms create unnecessary conflicts

**Priority:** Medium

`mode_selector`, fixed switch indicators, and region indicators can coexist. Selector decisions are
handled before a step, event decisions are handled during event dispatch, and region repair is only
consulted if the selector did not already request another mode. The resulting precedence is implicit
and can cause a localized event to be reversed by the selector at the next grid point.

Fixed-target simultaneous events also use registration order, while region proposals use distance
from the active region.

**Suggested solution**

- Make `set_switch_regions()` the only public runtime-switching configuration method.
- Remove `mode_selector` and its polling from `_do_step_internal()` after migrating consumers.
- Remove public `add_switch_indicator()`; boundary indicators become private implementation details
  generated exclusively from the region map.
- Remove `SwitchRequest`, policy precedence, priorities, deferred requests, and `SwitchArbiter` from
  the proposed design. They solve conflicts that no longer exist with one decision mechanism.
- Keep one private transactional operation that commits the region transition and state transfer.

**Acceptance criteria**

- It is impossible to configure two competing model-selection paths on one `MultiComponent`.
- Every runtime transition originates from a localized crossing of the configured region map.
- The implementation contains no registration-order or policy-precedence behavior.

### MC-10 — State transfer has no explicit fidelity or conservation contract

**Priority:** Medium

The transfer interface preserves a small human-readable state, but the meaning and losses are left
to each component. In the master pendulum:

- FEM exports a rigid proxy for a deformable field.
- Re-entering FEM reconstructs rigid displacement/velocity/acceleration fields and loses flexible
  deformation, stress, and elastic energy.
- OpenSim recreates its integration manager.
- The CVODE FMU is reconstructed from physical variables rather than a complete solver state.

Position and velocity may remain continuous while acceleration, energy, contact state, or solver
history jump. Frequent switching can therefore introduce artificial transients.

**Suggested solution**

- Define a canonical `PendulumState` with explicit units and optional fidelity-specific fields.
- Support adapters keyed by `(source_mode, target_mode)`, not only the target.
- Define preserved invariants for every transition: angle, angular velocity, torque, and optionally
  energy/contact state.
- Return transfer diagnostics such as projection residuals or lost-state warnings.
- Validate output continuity after transfer within configurable tolerances.
- Make switching transactional so a failed target import leaves the previous mode fully intact.

### MC-11 — Dead and duplicated abstractions obscure the real design

**Priority:** Medium

The following structures are unused or redundant:

- `StateAdapter` and `state_adapters` are documented but not used by state transfer.
- `_prev_state` and `_curr_state` are unused.
- `_switch_targets` uses `None` as a dynamic-target sentinel while `_boundary_events` stores related
  metadata in a parallel dictionary.
- `active_mode` and `active_comp` duplicate the same identity.
- Wrapper `sync_events` duplicates part of the system event history.
- Region switching generates two indicators per boundary even though they represent one boundary.

**Suggested solution**

- Remove dead fields or implement the advertised adapter mechanism.
- Replace parallel dictionaries with one immutable `SwitchRegions` configuration and typed
  `RegionBoundary` records generated from it.
- Store one authoritative active-region index and derive the active mode and component through
  properties.
- Record a structured `ModeSwitchEvent` in the common system history.
- Represent one region boundary once, retaining crossing direction as event metadata.

### MC-12 — MultiComponent and MasterPendulum rely heavily on private internals

**Priority:** Medium

Subclasses and the hybrid algorithm reach into private details such as `_switch_targets`,
`_allow_mode_switching`, `_record_history`, `_unify_ports()`, and
`_initialize_ports_from_specs()`. `MasterPendulum` also reads backend-private fields including
`_with_contact`, `_use_gravity`, `_equivalent_length`, and `_get_contact_gap_distance()`.

This makes lifecycle and algorithm behavior dependent on implementation details rather than stable
contracts.

**Suggested solution**

- Add a public configuration query such as `has_switch_regions` if lifecycle code needs it.
- Make port unification/creation an automatic base lifecycle operation.
- Define public backend metadata/proxy interfaces for mass, inertia, length, gravity, contact, and
  monitoring values.
- Replace algorithm flag manipulation with the checkpoint/trial protocol proposed in MC-03.

### MC-13 — MasterPendulum region configuration and naming need cleanup

**Priority:** Low

The current master implementation contains several avoidable inconsistencies:

- `_gap_based_mode_selector` is angle-based.
- Thresholds mix degrees and radians inside the decision function.
- The initial transient condition is labeled as hysteresis although it is a time hold.
- The documented time-based order differs from the implemented order.
- Default `initial_mode="FMU"` is immediately replaced with FEM at the first nonzero no-contact
  step.
- Mode strings are repeated in several branches.

**Suggested solution**

- Move region parameters into a typed `MasterPendulumSwitchConfig`.
- Store all angular thresholds internally in radians or as Pint quantities.
- Remove `initial_hold_time` and dwell timing from runtime switching; retain only signal bands.
- Use a `Mode` enum or centralized constants.
- Derive the initial region and model from the switching signal at `t0`; do not let an unrelated
  `initial_mode` override conflict with the region map.
- Remove the time-driven demonstration cycle from the production switching API. If it remains
  useful, implement it as a test/demo harness outside `MultiComponent`.

### MC-14 — Tests validate generic mechanics but not the real three-backend composition

**Priority:** Medium

The unit and integration tests cover `MultiComponent`, fixed indicators, region maps, dwell repair,
event placement, and rollback using lightweight mock/ramp/triangle components. There is no automated
test that switches a real `MasterPendulum` among FEM, OpenSim, and FMU.

Consequently, generic tests cannot detect backend-specific projection losses, speculative UI/history
side effects, initialization-order regressions, or resource lifecycle failures.

**Suggested solution**

Add layered tests:

1. Backend-independent contract tests for every component implementation.
2. Pairwise transfer tests for FEM ↔ OpenSim, FEM ↔ FMU, and OpenSim ↔ FMU.
3. A short three-mode trajectory test with switch-time and continuity assertions.
4. Trial-step purity tests for history, monitoring, visualization, and logs.
5. Reset/reinitialize tests covering active region, active mode, and switch history.
6. Macro-step-independence tests for the real region configuration.

Tests dedicated to fixed indicators and dwell repair should be removed with those features. Their
useful localization and rollback assertions should be retained against generated region boundaries.

Heavy backend tests can be marked and run in environments where NGSolve, OpenSim, and the FMU
artifacts are available. Contract tests should remain runnable with lightweight fakes.

## Existing work to retain during consolidation

### Region-map switching provides the canonical foundation

`MultiComponent.set_switch_regions()` closes three earlier problems in hand-registered switching:

- the target is derived from the crossed boundary and direction instead of registration order;
- one declaration generates and validates all boundary indicators and their bands.
- a nonzero band separates entry and exit thresholds to prevent threshold chatter.

This behavior is covered by `TestMultiModeSwitching`, `TestSwitchRegionsMap`, and
`TestSetSwitchRegions`. Preserve the region mapping, directional target resolution, and true event
localization while consolidating the APIs. Rewrite useful fixed-indicator tests against generated
region boundaries and delete tests whose only purpose is dwell suppression or pending repair.

Removing dwell makes pending repair unnecessary. Do not replace it with unconditional polling of
the region map: during development, polling read a speculative output and placed every switch on a
communication point at 0.054 s instead of the 0.055 s band edge. Reconcile the initial region once
at initialization; after that, transitions must come only from localized boundary crossings. Keep
regression tolerances much smaller than the macro step and use an incommensurate macro grid to
distinguish localization from grid placement.

### Trial rollback now restores wrapper output ports

Hybrid trial steps previously restored solver state but left cached output ports at `t + dt`.
Downstream Gauss-Seidel consumers and `MultiComponent` selectors could therefore read a future
value while the component state had returned to `t`.

`HybridAlgorithm` now captures state, inputs, output values, and output timestamps in one rollback
record and restores them together. The commutativity probe restores ports as well. This completed
fix must be preserved, but it does not close MC-03: monitoring, visualization, callbacks, nested
backend histories, and other external side effects still need a formal trial context.

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

**Suggested solution**

Evaluate, in increasing architectural scope:

1. Reuse a trial endpoint as the accepted endpoint when no crossing exists and the checkpoint can
   be committed safely.
2. Predict whether detection can be skipped from indicator value/rate bounds.
3. Add a component hook such as `can_skip_detection(t, dt)`.
4. Let event sources provide dense output or a cheap indicator predictor.

Any reuse optimization depends on MC-03: a speculative step must be transactional before it can be
committed safely.

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

`tests/unit/components/test_opensim.py` is empty and `syssimx/components/opensim.py` has low recorded
coverage. OpenSim represents one third of the heterogeneity claim. FMU coverage is also incomplete
on platforms without fixtures, and FEM has only one structural case study.

**Suggested solution**

- Add OpenSim unit and contract tests.
- Add mocked FMU unit coverage plus platform-complete integration fixtures where feasible.
- Add a second structural FEM example to demonstrate that `FEMComponent` generalizes beyond the
  pendulum.
- Include the real `MasterPendulum` switching tests from MC-14.

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

### HARD-04 — Release metadata is stale

**Priority:** Medium

`CITATION.cff` still records v0.2.0 and the prior release date. Generalized region switching and
`self_handled_events` change the public behavior, while the selector and fixed-indicator switching
APIs are being removed before release. The next release should therefore be a minor release,
v0.3.0, rather than a patch.

**Suggested solution**

- Complete the selected release-blocking fixes and evidence first.
- Update version, release date, ORCID, DOI, changelog/release notes, and API documentation.
- Tag v0.3.0 only after the full reproducibility gate is archived.

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

## Proposed target architecture

### 1. MultiComponent as façade and executor

`MultiComponent` should remain responsible for:

- exposing the unified ports;
- owning the model registry;
- delegating accepted steps to the active model;
- executing an already-approved transition atomically;
- exposing stable composite capabilities.

It should not contain case-specific threshold logic or several independent arbitration paths.

### 2. SwitchRegions as the sole public switching configuration

Retain and generalize `set_switch_regions()` as the only public model-selection API. Its immutable
configuration should contain:

- one continuous scalar signal with a documented unit;
- `N - 1` strictly ordered breakpoints;
- `N` region-to-model assignments;
- one nonzero hysteresis band per boundary; and
- validation of every model and every reachable model's rollback capability.

Store `active_region_index` independently from the model key so configurations such as
`FEM → OpenSim → FEM → FMU` remain valid. Derive the active model from the region assignment.

Do not introduce a general `SwitchPolicy` hierarchy. Grid-polled, scheduled, and arbitrary
fixed-target policies are outside the required `MultiComponent` runtime-switching use case.

### 3. Generated boundary events and transition resolution

Generate all event indicators privately from the region configuration. Prefer one bidirectional
event representation per boundary, carrying the detected direction and final sign-change bracket
through localization. At an event:

1. Select the earliest boundary crossing in the trial interval.
2. Localize it from the sign-change bracket.
3. Resolve the destination region from the crossed boundary and direction.
4. Commit exactly one transactional state transfer.
5. Continue the unused part of the macro step and detect another boundary if necessary.

No request arbiter is needed because there is one source of switching decisions. Initial
reconciliation is a lifecycle operation performed once at initialization, not a competing polled
mechanism. Region bands are the only runtime chatter guard; there is no dwell or deferred repair.

### 4. StateTransfer

Introduce an explicit transfer service:

```python
class StateTransfer(Protocol):
    def transfer(
        self,
        source_mode: ModeKey,
        target_mode: ModeKey,
        source: CoSimComponent,
        target: CoSimComponent,
        t: float,
    ) -> TransferReport: ...
```

`TransferReport` should describe preserved variables, projection residuals, warnings, and output
continuity. The executor commits the active-region change only after a successful report.

### 5. Checkpoint and speculative execution

Define a component checkpoint contract that captures everything needed to make speculative work
unobservable:

- solver state and time;
- input/output port values and timestamps;
- active region index for `MultiComponent`, from which its mode is derived;
- event-hint buffers;
- suppression of monitoring, visualization, callbacks, and histories.

The hybrid algorithm should operate only through this contract and public stepping/evaluation
methods.

### 6. MasterPendulum configuration

The intended contact switching should be expressed declaratively through the sole public API:

```python
plant.set_switch_regions(
    key=lambda view: abs(view.theta),
    breakpoints=config.breakpoints,
    modes=(Mode.FEM, Mode.OPENSIM, Mode.FMU),
    bands=config.bands,
)
```

The exact thresholds must be reconciled with the physical contact requirements and then defined in
one typed `MasterPendulumSwitchConfig`. The time-driven demonstration cycle and selector fallback
should be removed from `MultiComponent`; test-only forced cycling belongs in an external harness.

## Staged implementation plan

### Stage 1 — Correctness fixes

- Preserve the final sign-change bracket during event collection instead of making event existence
  depend on `tol_value`.
- Represent each boundary once with crossing direction, and require a nonzero band.
- Track the active region index so repeated model assignments are unambiguous.
- Remove minimum dwell timing and pending region repair.
- Complete reset semantics.
- Ensure `MasterPendulum` runs shared post-initialization logic.
- Stop speculative history/monitoring/visualization changes.
- Validate rollback capability for all reachable modes.
- Add regression tests for each fix.

### Stage 2 — Consolidate on region switching

- Generalize and document `set_switch_regions()` as the sole public switching API.
- Replace `_switch_targets`/`_boundary_events` with the immutable region configuration and generated
  typed boundary records.
- Migrate generic localization, rollback, and reset tests to generated region boundaries.
- Deprecate the selector and public fixed-indicator paths while downstream examples are migrated.
- Remove request arbitration, precedence, dwell, and deferred-request code that is no longer needed.

### Stage 3 — Formalize state transfer and checkpoints

- Add canonical or pairwise state adapters and `TransferReport`.
- Make switches transactional.
- Add the recursive checkpoint/trial protocol.
- Remove direct manipulation of private component flags from `HybridAlgorithm`.

### Stage 4 — Migrate MasterPendulum

- Move the localized angle policy into explicit, reusable `MasterPendulum` configuration and
  migrate notebooks 5 and 6 away from selector-only switching.
- Remove the time-driven demo cycle from production switching; keep any forced-cycle experiment in
  an external test harness.
- Move thresholds and signal bands into typed configuration.
- Add real-backend pairwise and end-to-end switching tests.
- Document which physical quantities are preserved or lost for each transition.
- After all examples and tests use regions, remove `mode_selector`, public
  `add_switch_indicator()`, and their fixed-target/registration-order infrastructure.

### Stage 5 — Cleanup

- Remove dead state fields and unused adapter APIs.
- Consolidate switch logging with system history.
- Automate port unification and initialization.
- Replace backend-private accesses with public capability/metadata interfaces.
- Update tutorials and notebooks to demonstrate the unified API only.

## Prioritized next steps

The order below resolves correctness risks before treating the current API as a release baseline.
Items on the same line can be developed together, but their evidence should land in the repository
before the dependent release step.

1. **Fix event acceptance and lifecycle correctness:** TIME-02/MC-05, MC-02, MC-04, and MC-03.
   Preserve the sign-change bracket, make reset equivalent to a fresh instance, and make trial
   advances externally pure.
2. **Consolidate on the sole switching mechanism:** MC-01, MC-07, MC-09, and MC-14. Remove dwell and
   pending repair, migrate notebooks 5 and 6, rerun the performance notebook, add three-backend
   transition tests, and then delete the selector and public fixed-indicator paths.
3. **Remove avoidable speculative work:** EVID-01, after the checkpoint/trial contract prevents
   optimization from changing observable behavior.
4. **Produce numerical evidence:** EVID-02 and EVID-03 together on the smooth pendulum, followed by
   EVID-04 and EVID-05 for a representative benchmark and independent-master comparison.
5. **Strengthen the validation gate:** HARD-01 and HARD-02, including a real OpenSim assertion and
   a scheduled FEM physics run.
6. **Simplify the remaining internals:** MC-06 through MC-12 using an authoritative region index,
   typed boundary records, transactional state transfer, and a recursive checkpoint contract. Do
   not add a request arbiter or general switching-policy hierarchy.
7. **Improve time semantics incrementally:** finish TIME-04, then introduce integer ticks in the
   master layer. Address TIME-01 through resolution negotiation before propagating ticks through
   every component API.
8. **Archive a reproducible minor release:** HARD-03, HARD-04, and REPRO-01. Update metadata and tag
   v0.3.0 only after the chosen gate and paper evidence are archived; the tag triggers the existing
   `publish-pypi.yml` workflow.

## Definition of done

The runtime-switching redesign is complete when:

- `set_switch_regions()` is the only public `MultiComponent` model-selection API;
- every runtime transition originates from one localized region-boundary crossing;
- state-dependent switches are localized independently of macro-step size;
- nonzero region bands provide signal hysteresis and no minimum-dwell state remains;
- active region identity is explicit and supports a model assigned to multiple regions;
- trial advances have no externally observable effects;
- reset/reinitialize is equivalent to a fresh component instance;
- every reachable localized mode has a validated rollback contract;
- state-transfer losses and preserved invariants are explicit and tested;
- `MasterPendulum` no longer depends on private switching or backend lifecycle internals;
- generic and real-backend tests cover switching, rollback, and repeated runs.

The repository is ready to serve as the paper/release baseline when, in addition:

- the convergence and switch-placement studies report error, work, and configuration together;
- the benchmark covers all intended regimes and is reproducible from archived raw data;
- FMU-only results agree with at least one independent master within declared tolerances;
- supported backends have meaningful automated coverage, including the scheduled slow FEM gate;
- environments and platform FMUs are pinned or attached to the release; and
- package, citation, DOI/ORCID, changelog, and v0.3.0 release metadata agree.
