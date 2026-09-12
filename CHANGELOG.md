# Changelog

All notable changes to SysSimX are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Issue identifiers such as `MC-05` or `HARD-07` refer to the working record in
[`issues.md`](issues.md); resolved entries are summarized here and removed from
that document. The detailed implementation records for the runtime-switching
redesign are in [`MILESTONES.md`](MILESTONES.md).

## [Unreleased]

## [0.4.0] — 2026-09-12

### Added

- Exported `MultiComponent`, `SwitchRegions`, and the new typed
  `ModeSwitchEvent` from the primary `syssimx` API. Committed handovers are
  available through `MultiComponent.switch_events`, `SystemHistory`, and
  `SimulationResult.mode_switches`.
- Added validated constructor options for `HybridAlgorithm`; stale or unknown
  options now fail instead of becoming inert instance attributes. The
  experimental declarative loader forwards algorithm options and rejects
  malformed ones.

### Changed

- Systems with event sources now always use `HybridAlgorithm`. An untouched
  default is promoted automatically, an explicitly configured hybrid instance
  is preserved, and an explicit non-hybrid choice raises instead of being
  silently replaced.
- `SimulationResult` preserves port units in tables and CSV exports and rejects
  malformed, non-monotone, or misaligned histories rather than omitting data.
- Clarified the minimum custom-component contract as three lifecycle hooks.
  `PortSpec` now validates its name, enum type, direction, and description, and
  component initialization validates dictionary keys and collection direction.
- Curated the published API reference around supported interfaces. The
  declarative loader and CLI are now explicitly labeled experimental.
- Reduced the basic installation to NumPy, Pint, and NetworkX. Results, YAML,
  visualization, and notebook interfaces now have focused optional extras and
  are imported only when used. Unused SciPy and pydot requirements were
  removed.

### Fixed

- `System.initialize()` now raises instead of running a second time. It was
  not idempotent: component `initialize()` returns early when already
  initialized, but the zero-length step at `t0` did not, so a second call
  appended another sample at `t0` to every component history after the run
  had advanced past it. The recorded time axis then stopped increasing
  monotonically, and re-running an initialization cell in a notebook
  silently corrupted the data. Call `reset()` to start a fresh run.

- `t0` is recorded once per port instead of twice. `initialize()` records a
  provisional sample before a generation's inputs have propagated, and the
  zero-length settling step then records the values that actually start the
  run; both were kept. Every trace began with a doubled point, and any
  difference over the timestamps saw a zero-length interval. The provisional
  sample is now dropped, so the recorded `t0` holds the settled values.
  **Sample counts drop by one per port; re-run notebooks to regenerate.**

- `_record_outputs()` no longer skips output ports individually. The guard was
  unreachable — `PortState` assigns a type-appropriate default on construction,
  so a port always holds a value — but it implied that partial recording was
  acceptable, which would desynchronize a component's histories.

- `ComponentHistory.to_arrays()` now verifies that the exported ports share
  one time axis instead of returning the first port's timestamps for all of
  them. A port that had dropped a sample was previously exported against a
  longer axis, which silently shifted its values against every other port
  and still produced a plottable result.

### Removed

- Removed the unused `StateAdapter` protocol, `state_adapters`, `_prev_state`,
  and `_curr_state` switching fields. The duplicate dictionary-based
  `sync_events` log is replaced by the typed common-history records above.

## [0.3.0] — 2026-08-24

A minor release rather than a patch: the public switching API changed, and two
defects in shipped behaviour were fixed.

### Added

- **Declarative region switching.** `MultiComponent.set_switch_regions()` maps a
  scalar signal onto ordered model regions and is now the only public
  model-selection API. One private bidirectional event is generated per physical
  boundary, armed at the far edge of its hysteresis band, so every runtime
  transition originates from a localized crossing rather than the macro grid.
  (MC-09)
- **Authoritative region identity.** `active_region_index` drives `active_mode`
  and `active_comp`, so a model may be assigned to several disconnected regions,
  such as `A -> B -> A -> C`. (MC-06)
- **A public checkpoint and trial contract.** `component.checkpoint()`,
  `restore_checkpoint()`, and `trial_context()` recursively suppress
  observational effects — history, monitoring, visualization, switching — for
  every nested model, so speculative work leaves nothing behind. (MC-03)
- **An explicit state-transfer contract.** Transfers are atomic and validated
  before backend identity is committed, and the preserved, reconstructed, and
  lost state of every directed transfer is declared and measured. (MC-10)
- **A static FMU release policy.** `resolve_release_policy()` decides from the
  archive alone whether a native instance may be terminated and freed, exposed
  as `FMUComponent.release_policy`. Six of the thirteen checked-in archives are
  released rather than retained, including four of the six FMUs in the
  quantization system. (HARD-05 step 1)
- **An FMU extraction cache.** `extract_cached()` unpacks each archive once and
  shares the directory with every consumer; `clear_extraction_cache()` provides
  teardown. Repeated `reset()`/`initialize()` cycles now strand zero extraction
  directories, against one whole directory per cycle before. (HARD-07 step 1)
- **A guard against silently missed events.** `HybridAlgorithm` re-checks every
  accepted advance that detection called event-free, collecting anything that
  slipped through in `missed_events` and logging it;
  `raise_on_missed_event` makes the mismatch fatal. Costs 1.8–11.3 µs per macro
  step and no model advance. (HYB-01)
- **A notebook execution gate in CI.** The backend-free switching notebooks are
  executed with `pytest --nbmake`, so an API change can no longer break a
  published tutorial silently. (HARD-06)

### Changed

- **`FMUComponent.reset()` and `reinitialize_instance()` release when safe.**
  They terminate and free the native instance where the release policy allows
  and retain it where it does not, instead of retaining unconditionally.
  (HARD-05)
- **`soft_reset()` refuses on an archive that cannot survive `fmi2Reset`,** but
  only on the platform where that fault is recorded. Retention stays
  conservative everywhere because it costs only memory; refusing a reset would
  remove working functionality, so it is scoped to the recorded evidence.
  (HARD-05)
- **Region bands are mandatory and validated.** A configuration with `N` region
  assignments requires exactly `N - 1` strictly ordered boundaries, each with a
  finite nonzero band, and neighbouring bands may not overlap or touch.
  (MC-05)
- **Rollback capability is validated for every reachable mode,** not only the
  active one. (MC-08)
- **`MultiComponent.initialize()` owns region reconciliation,** so subclasses no
  longer bypass shared post-initialization logic. (MC-02)
- **`reset()` restores the full switching lifecycle,** making a reset component
  equivalent to a fresh instance. (MC-04)
- Every published notebook carries outputs produced by a recorded environment.
  (HARD-06)

### Fixed

- **`HybridAlgorithm` could locate an event and dispatch nothing.** When a
  component's internal micro-step hint and the macro endpoints both saw the same
  crossing, the hint was discarded as a duplicate; the surviving macro-wide
  bracket was then filtered out by the hint short-circuit, which returns only
  brackets strictly narrower than the macro interval. A crossing seen *only* by
  the hint dispatched correctly, so detection was strongest exactly where the
  event vanished. Unreachable at the default `tol_time = 1e-8`, which is why no
  test saw it; the contact benchmark, which sets `1.5e-4` deliberately, lost
  three of its five wall contacts. (HYB-06)
- **Native FMU instances corrupted the heap on teardown.** Freeing any
  OpenModelica CVODE export with at least one continuous state raises Windows
  exception `0xC0000374` and takes the process down. Isolated to
  `fmi2FreeInstance` and `fmi2Reset`, and now avoided by the release policy
  rather than by retaining every instance. (HARD-05)
- **Speculative advances had externally visible effects.** Event detection and
  bisection no longer disturb histories, monitors, scenes, switch logs, or
  callbacks, and trial rollback restores cached output ports rather than leaving
  them at `t + dt` for downstream consumers to read. (MC-03)
- **Published notebooks leaked machine-specific absolute paths** into committed
  outputs. No tracked notebook carries one. (HARD-06)
- Nine tracked notebooks carried no outputs at all while every CI job stayed
  green, because `nb_execution_mode = "off"` publishes whatever a notebook
  already holds. (HARD-06)

### Removed

- **The legacy switching mechanisms.** The selector callback, the fixed-target
  map, and minimum-dwell timing are gone; `set_switch_regions()` replaces all
  three. Dwell timing duplicated and weakened the band hysteresis it sat beside.
  (MC-07, MC-09)

### Known limitations

- Detection advances event sources with the inputs cached at the left edge of
  the macro step, while the accepted advance re-reads them after the upstream
  generation has stepped. The two trajectories differ. A crossing on the
  accepted one is now reported rather than silently dropped, but it is still not
  localized. (HYB-01, HYB-02)
- Roughly half of all model time is computed and rolled back, measured across
  two notebooks with and without contact and with and without switching. The
  waste belongs to the detection scheme rather than to `MultiComponent`.
  (EVID-01, HYB-03)
- Native instances of the defective CVODE exports are still retained for the
  lifetime of the process, and `freeLibrary` is never called for any archive, so
  resident memory grows by roughly 0.11 MB per initialization cycle.
  (HARD-05, HARD-07)
- Whether the CVODE teardown also faults on Linux is unresolved. `fmi2Reset` is
  known to work there on one affected export; `fmi2FreeInstance` is untested.
  (HARD-05)

## [0.2.0] — 2026-07-18

Runtime model switching through `MultiComponent`, the hybrid master algorithm
with superdense-time event handling, and the controlled-pendulum case study
across FMU, OpenSim, and FEM backends.

## [0.1.7] and earlier

Initial public releases. See the git history for details.

[Unreleased]: https://github.com/FlorianFrech/SystemSimulation/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/FlorianFrech/SystemSimulation/releases/tag/v0.4.0
[0.3.0]: https://github.com/FlorianFrech/SystemSimulation/releases/tag/v0.3.0
[0.2.0]: https://github.com/FlorianFrech/SystemSimulation/releases/tag/v0.2.0
