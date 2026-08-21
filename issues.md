# SysSimX — Open Issues and Runtime-Switching Redesign

> Repository-level source of truth for framework work, evidence generation, release hardening, and the runtime-switching redesign.

## Recorded baseline

Milestone 0 was completed on 2026-08-20 in an isolated worktree on branch
`refactor/region-switching-baseline`. The underlying source baseline is `origin/main` at
`f4895a7`; commit `b33c40f` adds only this roadmap. None of the pre-existing tracked changes in the
original `main` worktree were modified, staged, cleaned, or committed during isolation. Its
untracked `issues.md` was synchronized with this baseline record so the two working copies agree.

The earlier **645 passed, 1 skipped** result belongs to the uncommitted switching prototype and is
not the clean `origin/main` baseline. The reproducible clean-baseline result is **621 passed,
1 skipped** when every marker is enabled on Python 3.13.

### Worktree inventory and isolation

At isolation time, `main` equaled `origin/main`, the index was empty, and the original worktree had
ten modified files plus untracked `issues.md`:

- framework: `syssimx/core/multi_comp.py` and `syssimx/system/algorithms/hybrid.py`;
- case study: `demos/ControlledPendulum/src/master_pendulum/orchestration/master_pendulum.py`;
- tests: five fixture, unit, and integration files;
- notebooks/documentation: the advanced switching tutorial and `notebooks/performance.ipynb`;
- roadmap: untracked `issues.md`.

Those changes remain together only in the original dirty worktree. New switching work must use the
isolated branch/worktree or a descendant of its committed baseline; it must not be added to the
original `main` worktree.

### Baseline environment

| Item | Recorded value |
|---|---|
| Operating system | Windows 11, build 26200, x86-64 |
| Git | 2.55.0.windows.3 |
| uv | 0.11.29 |
| Python matrix | 3.11.15, 3.12.13, 3.13.5 |
| Primary full environment | Python 3.13.5, pytest 9.1.1, coverage 7.15.2 |
| Installed backends in full environment | FMPy 0.3.30, NGSolve 6.2.2606, OpenSim 4.6 |

The primary environment was created with:

```powershell
uv sync --frozen --python 3.13 --extra all
```

The Python 3.11 and 3.12 fast-CI environments were created in temporary directories with:

```powershell
uv venv "$env:TEMP\syssimx-baseline-py311" --python 3.11.15 --managed-python
uv pip install --python "$env:TEMP\syssimx-baseline-py311\Scripts\python.exe" -e ".[dev,fmu,fem]"
uv venv "$env:TEMP\syssimx-baseline-py312" --python 3.12.13 --managed-python
uv pip install --python "$env:TEMP\syssimx-baseline-py312\Scripts\python.exe" -e ".[dev,fmu]"
```

These temporary environments intentionally reproduce the CI extras, which resolve current package
versions rather than consuming `uv.lock`.

### Commands and results

| Gate | Command | Result |
|---|---|---|
| Lock validation | `uv lock --check` | **Failed:** `uv.lock` needs updating |
| Ruff | `.\.venv\Scripts\ruff.exe check syssimx\ tests\` | Passed |
| MyPy | `.\.venv\Scripts\mypy.exe syssimx\ --ignore-missing-imports --python-version 3.13` | Passed, 27 files |
| Full suite | `.\.venv\Scripts\pytest.exe tests\ --cov=syssimx --cov-report=term-missing -v` | 621 passed, 1 skipped; 79% coverage |
| Fast CI, Python 3.11 | `pytest tests\unit\ tests\integration\ -m "not fem and not slow" --cov=syssimx -v` | 568 passed, 1 skipped, 53 deselected; 75% coverage |
| Fast CI, Python 3.12 | same command in the Python 3.12 environment | 568 passed, 6 skipped; 75% coverage |
| Fast CI, Python 3.13 | same command in the Python 3.13 environment | 568 passed, 1 skipped, 53 deselected; 76% coverage |
| FEM CI, Python 3.11 | `pytest -m fem -v` | 53 passed, 1 skipped, 568 deselected |
| Strict documentation | `$env:SYSSIMX_DOCS_OFFLINE = '1'`; `sphinx-build -b html -W --keep-going docs docs\_build\html` | Passed without warnings |
| Locked package build | `uv build --no-sources` | Passed |
| CI-equivalent package build | `python -m build` under Python 3.11 | Passed |

MyPy emitted informational notes that untyped bodies in `HybridAlgorithm` are not checked and that
the `OMPython.*` override is unused. These are not type errors, but the baseline must not be
described as full type coverage.

### Skips, gaps, and artifacts

- The FMU fixture test is skipped on Windows because the checked-in artifact has `c-code` and
  `linux64`, but no `win64` binary.
- The Python 3.12 fast environment intentionally omits the FEM extra, producing five additional
  NGSolve-dependent module skips. The dedicated Python 3.11 FEM job passed all 53 selected tests.
- OpenSim 4.6 is installed in the full environment, but the current suite still lacks a meaningful
  OpenSim backend assertion; a green gate does not close HARD-01.
- The stale lockfile means the dependency state is not yet reproducible. `uv sync --frozen`
  succeeds by accepting the existing lock without validating it against `pyproject.toml`.

The package build produced:

- `syssimx-0.2.0.tar.gz` — SHA-256
  `3AC1E6B68501A062FBFD99D06CC9B95010660219F50FE200E7E183BA4A22D13C`;
- `syssimx-0.2.0-py3-none-any.whl` — SHA-256
  `332D084DEF2945E74E900DCA5B9ADD3DE59EBB259B109640C136928F8A7FCC91`.

## Milestone 1 implementation record

Milestone 1 was implemented on 2026-08-20 in the protected
`SystemSimulation-region-switching` worktree. The implementation establishes the canonical region
mechanism without yet deleting the legacy selector and fixed-target APIs; those remain temporarily
for the explicit example migration and removal work in Stage 2.

Implemented behavior:

- `SwitchRegions` and `RegionBoundary` are immutable validated domain objects. A configuration with
  `N` region assignments requires exactly `N - 1` strictly ordered boundaries, a finite nonzero band
  per boundary, non-overlapping bands, known model keys, and rollback support in every reachable
  model.
- `active_region_index` is the authoritative runtime identity. `active_mode` and `active_comp` are
  derived from it after initialization, so disconnected regions may reuse a model key, such as
  `A -> B -> A -> C`. Missing or out-of-range runtime identity raises instead of falling back to
  region zero.
- Each physical boundary is registered once as a private bidirectional event. Its active threshold
  is the upper band edge while the active region is below the boundary and the lower band edge while
  the active region is above it.
- `EventBracket` carries the final sign-change interval through bisection and dispatch. The target is
  resolved from the crossed boundary plus the bracket's direction; event acceptance no longer
  depends on the localized endpoint also satisfying `tol_value`.
- Minimum dwell timing and every notebook/test reference to it were removed. A full-band recrossing
  is never suppressed based on elapsed time, including an opposite-direction crossing of the same
  boundary inside one macro step.
- Region reconciliation runs once during initialization. Accepted steps do not poll the region map,
  and there is no pending/deferred repair state.
- The hybrid loop localizes the earliest boundary, commits one adjacent transition, and continues the
  unused part of the macro step so additional boundaries are processed chronologically.

Regression coverage now pins one transition per crossing, no return switch inside a band, rapid
full-band recrossing, repeated model assignments, chronological multi-boundary processing,
macro-step-independent placement, one-time initialization reconciliation, and hard failure for an
invalid runtime region.

Current verification on Python 3.13.5:

- Ruff: passed for `syssimx/` and `tests/`;
- MyPy: passed for all 27 source files;
- full pytest suite: 621 passed, 1 skipped (the unchanged win64 FMU-fixture skip);
- strict offline Sphinx build: passed without warnings;
- locked `uv build --no-sources`: passed.

## Milestone 2 implementation record

Milestone 2 was implemented on 2026-08-20 in the same protected
`SystemSimulation-region-switching` worktree. Runtime switching is now a transaction over an
explicit framework checkpoint rather than a solver-only state copy plus private flag manipulation.

Implemented behavior:

- `ComponentCheckpoint` is the public opaque rollback contract. It captures backend solver state,
  time, input/output values and timestamps, component history, parameters, internal event hints,
  event-dispatch metadata, initialization state, composite metadata, and the active recursive child
  path. A checkpoint is bound to the component instance that created it.
- `trial_context()` recursively marks a composite and its children as speculative, disables history
  recording and model switching, and exposes `in_trial` to backend observer hooks. The hybrid
  algorithm now uses `checkpoint()` / `restore_checkpoint()` and this context exclusively; it no
  longer manipulates component-private flags or passes raw backend snapshots.
- Direct history writes through `_record_outputs()` are suppressed during trials. FEM substep
  observer callbacks are not invoked speculatively, and the master-pendulum monitoring, scene
  updates, FEM monitor state, and known FEM/OpenSim event logs honor `in_trial`. FMU restores that
  call `_record_outputs()` are therefore also non-recording inside rollback.
- Every model reachable from `SwitchRegions` is validated for rollback before the region map is
  accepted. A `MultiComponent` checkpoint recursively captures the active backend, while trial
  suppression reaches every registered backend; an inactive switch target receives its own
  checkpoint during transfer preparation.
- State transfer is prepare--validate--commit. The wrapper and source are checkpointed, the target
  is checkpointed, current inputs are replayed, adapted state is imported, the target is read back
  for validation, and target outputs are refreshed under trial suppression. Only then is the mode
  shadow updated and `active_region_index` committed. Any preparation exception restores target,
  source, wrapper ports, histories, time, region identity, and switch records before propagating the
  original exception.
- `reset()` now resets port values and timestamps, trial/event runtime state, the original model,
  region identity, cached inputs, synchronization records, and all children. `MasterPendulum` and
  its FEM backend also recreate monitoring state and close stale observer panels. A subsequent
  `initialize(t0)` is covered against a freshly constructed equivalent region component.

Regression coverage pins full checkpoint restoration, direct trial-history suppression, recursive
trial state, FEM observer suppression, reachable-model rollback validation, target-import failure
atomicity, and reset/reinitialize equivalence. The failed-import test intentionally corrupts target
time, physical state, output ports, and history before raising and verifies that all source, target,
and wrapper observables are unchanged.

Current verification on Python 3.13.5:

- Ruff: passed for `syssimx/` and `tests/` with `--no-cache` because the isolated worktree's cache
  directory is read-only in the managed runner;
- MyPy: passed for all 27 source files using a dedicated temporary cache;
- focused core/hybrid integration gate: 151 passed;
- full backend-enabled suite with coverage: **627 passed, 1 skipped**, 81% coverage; the unchanged
  skip is the FMU fixture without a win64 binary;
- the first full run reached 614 passes but 12 file-I/O tests could not create Pytest's default temp
  directory; all 91 affected history/loader/result tests passed with a dedicated `--basetemp`, and
  the complete corrected run then passed; the final post-review run completed in 192.55 seconds;
- strict offline Sphinx documentation: passed without warnings from dedicated temporary doctree and
  output directories;
- locked `uv build --no-sources`: passed offline from the populated cache, with artifacts written
  to a dedicated temporary directory.

The final commands were:

```powershell
.\.venv\Scripts\ruff.exe check --no-cache syssimx tests
.\.venv\Scripts\mypy.exe syssimx --ignore-missing-imports --python-version 3.13 --cache-dir "$env:TEMP\syssimx-milestone2-mypy"
$env:COVERAGE_FILE = "$env:TEMP\syssimx-milestone2-final.coverage"
.\.venv\Scripts\pytest.exe -p no:cacheprovider --basetemp "$env:TEMP\syssimx-milestone2-final-pytest" tests --cov=syssimx --cov-report=term-missing -q
$env:SYSSIMX_DOCS_OFFLINE = "1"
.\.venv\Scripts\sphinx-build.exe -b html -W --keep-going -d "$env:TEMP\syssimx-milestone2-doctrees" docs "$env:TEMP\syssimx-milestone2-docs"
uv build --no-sources --out-dir "$env:TEMP\syssimx-milestone2-dist"
```

This closes the transactional portions of MC-03, MC-04, and MC-08. MC-10 remains open for the
separate physical-fidelity work: canonical/pairwise adapters, conservation tolerances, and transfer
diagnostics are not part of Milestone 2. HARD-01 also remains open because the Windows FMU binary
and a meaningful OpenSim backend assertion are still absent.

## Milestone 3 implementation record

Milestone 3 was implemented on 2026-08-20 on branch `breaking/region-switching-only`, after all
consumer changes were separated from the API removal:

- `61c53c8` migrates the default `MasterPendulum`, notebooks 5 and 6, the performance and
  verification notebooks, tutorials, documentation, and unit/integration tests;
- `16ea316` makes demonstrations that intentionally use one fixed model explicit with
  `switch_config=None`;
- `c306370` is the dedicated breaking-change commit that removes the legacy APIs.

`MasterPendulumSwitchConfig` is now the immutable reusable angle-region policy. Its default maps
FEM, OpenSim, and FMU to three ordered `abs(theta)` regions with two nonzero hysteresis bands.
Passing `None` opts out of runtime switching. The old production time cycle was moved to an
external signal-driven integration harness, which covers `A -> B -> C -> A` without putting a
schedule-driven policy back into `MultiComponent`.

After consumer migration, the breaking commit removed `mode_selector`, `_select_target_mode()`,
public `add_switch_indicator()`, `_switch_targets`, `_resolve_switch_target()`, fixed-target
registration-order behavior, and the obsolete MasterPendulum time/gap selector methods. Event
evaluation, port preservation, self-subscription, and dispatch now recognize generated region
boundaries only. `_switch_mode()` remains private solely as a direct transactional transfer
primitive; it is not an automatic switching mechanism.

Repository-wide searches over `syssimx`, `demos`, `tests`, `docs`, and `notebooks` return no matches
for the deleted symbols. Historical references remain in this roadmap only so the rationale and
completed findings are auditable.

Current verification on Python 3.13.5:

- Ruff: passed for `syssimx/` and `tests/`;
- MyPy: passed for all 27 source files;
- focused core/hybrid/MasterPendulum gate: 86 passed;
- full backend-enabled suite with coverage: **626 passed, 1 skipped**, 84% coverage, in 175.86 s;
- strict offline Sphinx documentation: passed without warnings;
- locked `uv build --no-sources`: passed using the populated local cache;
- the generic switching tutorial and `notebooks/03_multi_comp_verification.ipynb` executed
  successfully; expensive case-study notebook outputs were cleared rather than retaining stale
  results.

The final commands were:

```powershell
.\.venv\Scripts\python.exe -m ruff check syssimx tests
.\.venv\Scripts\python.exe -m mypy syssimx --ignore-missing-imports --python-version 3.13
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp "$env:TEMP\syssimx-m3-final2-pytest" tests --cov=syssimx --cov-report=term-missing -q
$env:SYSSIMX_DOCS_OFFLINE = "1"
.\.venv\Scripts\python.exe -m sphinx -b html -W --keep-going -d "$env:TEMP\syssimx-m3-doctrees-final" docs "$env:TEMP\syssimx-m3-docs-final"
uv build --no-sources --out-dir "$env:TEMP\syssimx-m3-dist"
rg -n "mode_selector|_select_target_mode|add_switch_indicator|_switch_targets|_resolve_switch_target|_time_based_mode_selector|_gap_based_mode_selector|_pending_region_repair" syssimx demos tests docs notebooks
```

The first build attempt deliberately used a new empty temporary uv cache and failed because the
managed runner cannot reach PyPI. Repeating the same locked build against the populated local cache
passed; no dependency or lockfile was changed.

The unchanged skip is the FMU fixture without a win64 binary. Real three-backend switching and
fresh performance/convergence evidence remain tracked by HARD-01 and EVID-01 through EVID-03; they
are not blockers to the mechanism migration itself.

## Milestone 4 implementation record

Milestone 4 was implemented on 2026-08-20 on the stacked branch
`validation/real-backend-switching`. It adds physical acceptance evidence and a lightweight real
FEM/FMU/OpenSim gate without changing the public region-switching API.

- `9b43a2f` adds canonical transfer validation and transactional diagnostics;
- `5671999` adds the real-backend trajectory and its CI integration.

Implemented behavior:

- `MultiComponent` now invokes a side-effect-free `_build_transfer_report()` hook after target
  import, read-back validation, and output refresh, but before committing active identity. A hook
  failure uses the existing transaction rollback and leaves the source, target, wrapper, ports,
  histories, time, region, and switch log unchanged. A successful immutable report is attached to
  the accepted switch event.
- `MasterPendulum` defines immutable `PendulumState`, `PendulumTransferTolerances`, and
  `PendulumTransferReport` domain types. Backend values are normalized to radians, radians per
  second, and N*m; every switch rejects non-finite state or angle, angular-velocity, or torque
  discontinuity beyond configurable absolute tolerances.
- The master declares its common direct-feedthrough contract before backend initialization. This
  removes the former need for consumers to patch wrapper feedthrough metadata before placing a
  real `MasterPendulum` in a `System`.
- One module-scoped integration fixture initializes a coarse first-order FEM mesh once and executes
  a 0.7 ms torque-free trajectory through
  `FEM -> OpenSim -> FEM -> FMU -> OpenSim -> FMU -> FEM`. This covers all six directed backend
  pairs with one macro step and asserts chronological switch placement, canonical continuity, and
  the final free-motion state.
- The fixture deliberately disables wall contact, gravity, and animation and uses the checked-in
  Euler pendulum FMU. The scheduled time signal exists only in the external test harness; it is not
  another production switching mechanism. The existing deterministic tests remain authoritative
  for sub-microsecond localization semantics.
- The existing `test-fem` CI job now installs the FEM, FMU, and OpenSim extras and runs the real
  switching test as part of `pytest -m fem`; the job identifier is unchanged.

Measured verification on Python 3.13.5:

- changed-file Ruff formatting and repository-wide Ruff checks: passed;
- MyPy: passed for all 27 source files;
- focused core/MasterPendulum/real-backend gate: **57 passed in 3.25 s**;
- full backend-enabled suite with coverage: **636 passed, 1 skipped**, 89% coverage, in 168.83 s;
- strict offline Sphinx documentation: passed without warnings;
- locked `uv build --no-sources`: passed.

The final commands were:

```powershell
.\.venv\Scripts\python.exe -m ruff check --no-cache syssimx tests
.\.venv\Scripts\python.exe -m mypy syssimx --ignore-missing-imports --python-version 3.13 --cache-dir "$env:TEMP\syssimx-real-backend-mypy"
$env:COVERAGE_FILE = "$env:TEMP\syssimx-real-backend.coverage"
.\.venv\Scripts\pytest.exe -p no:cacheprovider --basetemp "$env:TEMP\syssimx-real-backend-full-pytest" tests --cov=syssimx --cov-report=term-missing -q
$env:SYSSIMX_DOCS_OFFLINE = "1"
.\.venv\Scripts\python.exe -m sphinx -b html -W --keep-going -d "$env:TEMP\syssimx-real-backend-doctrees" docs "$env:TEMP\syssimx-real-backend-docs"
uv build --no-sources --out-dir "$env:TEMP\syssimx-real-backend-dist"
```

The unchanged skip is the separate generic FMU fixture without a win64 binary. This milestone
proves canonical angle, angular-velocity, and torque continuity for every real backend pair. It
does not claim preservation of FEM deformation/stress/elastic energy, contact state, acceleration,
or backend solver history; those fidelity questions remain open in MC-10. Broader backend contract
coverage and a second structural FEM example also remain in HARD-01.

## Milestone 5 implementation record

Milestone 5 was implemented on 2026-08-20 on the stacked branch
`validation/real-backend-lifecycle`. It closes the real-backend lifecycle and transactional
side-effect gaps without adding wall contact or another switching mechanism.

- `ca7f339` makes FMU ownership, backend reset, and nonzero initialization time deterministic;
- `e1c4211` adds lightweight real FEM/FMU/OpenSim lifecycle and rollback tests;
- `b090a62` releases all demo-owned OpenSim runtime references on reset and verifies replacement.

Implemented behavior and evidence:

- A reset and reinitialize of the same `System` at a nonzero `t0` is compared with a newly
  constructed system. Active region, active model, wrapper and child clocks, ports, histories,
  monitoring state, switch log, and canonical state agree for every backend.
- `System.initialize(t0)` now performs its output-refresh zero step at `t0`, rather than resetting
  component clocks to literal zero.
- A real FEM-to-FMU transaction is rejected after target import. Rollback restores source and target
  canonical state, FEM vectors, ports, histories, monitoring state, time, active identity, and switch
  log. The abandoned FMU instance is terminated and freed exactly once; rollback uses a newly
  initialized native instance instead of illegally instantiating the old wrapper twice.
- Trial advances are executed once with each of FEM, OpenSim, and FMU active. Wrapper and child
  histories, FEM multidimensional histories, monitoring, visualization, callbacks, logs, ports,
  time, region, and switch records remain observationally unchanged.
- FMU reset now terminates and frees the native instance, removes its extracted directory, and still
  clears framework state if native cleanup reports an error. Reinitialization creates one fresh
  instance from the existing extraction during rollback and re-extracts after a full reset.
- The checked-in Euler and CVODE FMUs declare neither `canGetAndSetFMUstate` nor
  `canSerializeFMUstate`. Checkpoints therefore reconstruct their documented physical state and
  deliberately discard solver-internal history; unsupported FMI state functions are not called.
- The OpenSim pendulum releases its model, state, manager, coordinate, and actuator references on
  reset; reinitialization constructs a different native object graph. FEM and OpenSim reset are also
  safe before backend initialization.

The real tests reuse a coarse first-order FEM mesh and disable contact, gravity, and animation. No
wall-contact solve was added to the fast gate.

Measured verification on Windows, Python 3.13.5, Pytest 9.1.1:

- repository/source Ruff checks: passed;
- MyPy: passed for all 27 source files;
- final lifecycle slice: **89 passed in 6.39 s**;
- final exact-tip real-backend cleanup slice: **15 passed in 6.14 s**;
- full backend-enabled suite with coverage: **640 passed, 1 skipped**, 89% coverage, in 168.76 s;
- strict offline Sphinx documentation: passed without warnings;
- locked `uv build --no-sources`: passed.

The final commands were:

```powershell
.\.venv\Scripts\python.exe -m ruff check --no-cache syssimx tests demos/ControlledPendulum/src/master_pendulum/components/fem/fem_pendulum.py demos/ControlledPendulum/src/master_pendulum/components/fmu/fmu_pendulum.py
.\.venv\Scripts\python.exe -m ruff check --no-cache demos/ControlledPendulum/src/master_pendulum/components/opensim/opensim_pendulum.py tests/integration/demos/controlled_pendulum/test_master_pendulum_backends.py
.\.venv\Scripts\python.exe -m mypy syssimx --ignore-missing-imports --python-version 3.13 --cache-dir "$env:TEMP\syssimx-m5-final-mypy"
.\.venv\Scripts\pytest.exe -p no:cacheprovider --basetemp "$env:TEMP\syssimx-m5-final2-pytest" tests/integration/demos/controlled_pendulum/test_master_pendulum_backends.py tests/unit/demos/controlled_pendulum/test_master_pendulum_switching.py tests/unit/system/test_system.py -q
.\.venv\Scripts\pytest.exe -p no:cacheprovider --basetemp "$env:TEMP\syssimx-m5-opensim-cleanup-pytest" tests/integration/demos/controlled_pendulum/test_master_pendulum_backends.py tests/unit/demos/controlled_pendulum/test_master_pendulum_switching.py -q
$env:COVERAGE_FILE = "$env:TEMP\syssimx-m5-tip.coverage"
.\.venv\Scripts\pytest.exe -p no:cacheprovider --basetemp "$env:TEMP\syssimx-m5-tip-full-pytest" tests --cov=syssimx --cov-report=term-missing -q
$env:SYSSIMX_DOCS_OFFLINE = "1"
.\.venv\Scripts\python.exe -m sphinx -q -b html -W --keep-going -d "$env:TEMP\syssimx-m5-final2-doctrees" docs "$env:TEMP\syssimx-m5-final2-docs"
uv build --no-sources --out-dir "$env:TEMP\syssimx-m5-final-dist"
```

The unchanged skip is the generic FMU fixture whose archive contains `linux64` and C sources but no
`win64` binary. The native OpenSim library also prints a non-fatal warning when it cannot create
`opensim.log` in the managed runner; application and framework logging remains silent during trial
advances. Acceleration, energy, flexible/contact state, and backend solver-history fidelity remain
open in MC-10. Real angle-policy macro-step evidence remains open in MC-14.

## Milestone 6 implementation record

Milestone 6 was implemented on 2026-08-21 on the same stacked branch
`validation/real-backend-lifecycle`. It characterizes what a runtime switch actually preserves and
loses for the real backends, and it closes the remaining macro-step case of MC-14. The public
switching API is unchanged: `set_switch_regions()` is still the only model-selection mechanism and
the transfer is still the Milestone 2 transaction.

- `a4fe054` measures acceleration and energy in the transfer report and declares state semantics;
- `cf1e597` extracts the shared real-backend harness;
- `5ceff86` adds the driven six-pair fidelity characterization;
- `d80c6f6` adds the real angle-region macro-step placement study;
- `110d24f` applies Ruff formatting to the master-pendulum unit tests.

### Measured quantities

`PendulumState` now carries the angular acceleration alongside angle, angular velocity, and torque.
Unit normalization goes through the framework parser, so the three backend spellings of the
acceleration unit (`rad/s**2` for FEM, `rad/s^2` for OpenSim, `rad/s2` for the FMU) all resolve.

`RigidPendulumProperties` records the mass, equivalent length, pivot inertia, and gravity that the
FEM geometry synchronizes to every backend during initialization. One energy definition therefore
applies to all three modes, with the pivot as the potential-energy datum:

```
E_kin = 0.5 * J * omega^2
E_pot = m * g * L * (1 - cos(theta))
```

`PendulumEnergy` keeps that rigid mechanical energy separate from the elastic strain energy, which
only FEM can supply. `FEMPendulum.strain_energy()` exposes the side-effect-free elastic integral
that `calculate_energy()` already computed, so the report can read it inside the transfer
transaction and inside a speculative advance.

Every accepted transfer report now exposes `alpha_error`, `energy_error`, `elastic_energy_lost`,
`total_energy_error`, and a `discontinuities` mapping. `PendulumTransferTolerances` gains `alpha`
and `energy` limits that default to `None`, meaning measured but not enforced. Angle, angular
velocity, and torque keep their Milestone 4 acceptance role unchanged.

### Preserved and lost state

`BACKEND_STATE_SEMANTICS` declares, per backend, the canonical quantities it exports on exit, the
canonical quantities it accepts on entry, the internal state it reconstructs, and the internal state
it discards. `transfer_state_semantics(source, target)` resolves one directed pair, and every report
carries it.

| Backend | Accepted on entry | Reconstructed on entry | Discarded on exit |
|---|---|---|---|
| FEM | theta, omega, tau | rigid displacement, velocity, and acceleration fields; Newmark previous-step vectors set equal to the current step | elastic deformation, elastic strain energy, Cauchy stress field, von Mises stress field, Newmark step history, contact gap history |
| OpenSim | theta, omega, tau | SimTK system state, integration manager | integrator step-size and error history |
| FMU | theta, omega, tau | native instance created from `theta_start` and `omega_start` | solver-internal history; the checked-in FMUs declare neither `canGetAndSetFMUstate` nor `canSerializeFMUstate` |

For every directed pair the preserved set is therefore exactly `(theta, omega, tau)`. Angular
acceleration is exported by all three backends but accepted by none, so it is always in the lost
set: each target recomputes it from the torque and its own dynamics.

### Measured transfer discontinuities

One coarse, contact-free, gravity-free plant was driven by a constant 50 N*m torque through
`FEM -> OpenSim -> FEM -> FMU -> OpenSim -> FMU -> FEM`, covering all six directed pairs in one
0.7 ms simulation. A drive is what makes the FEM backend deform; without it there is no elastic
state for a transfer to lose. Rigid properties for this configuration are `m = 1.0912847 kg`,
`L = 0.18165069 m`, `J = 0.044510365 kg*m^2`, `g = 0`.

| Transfer | t [s] | d_theta [rad] | d_omega [rad/s] | d_tau [N*m] | d_alpha [rad/s^2] | alpha [rad/s^2] | d_E_mech [J] | E_elastic lost [J] | E_mech [J] |
|---|---|---|---|---|---|---|---|---|---|
| FEM -> OpenSim | 1.107e-04 | 0.00e+00 | 0.00e+00 | 0.00e+00 | 2.47e-05 | 1.1233e+03 | 0.00e+00 | 2.12e-04 | 1.601e-03 |
| OpenSim -> FEM | 2.109e-04 | 5.55e-17 | 7.22e-16 | 0.00e+00 | 2.27e-13 | 1.1233e+03 | 1.17e-17 | -4.95e-20 | 3.226e-03 |
| FEM -> FMU | 3.102e-04 | 0.00e+00 | 0.00e+00 | 0.00e+00 | 2.37e-05 | 1.1233e+03 | 0.00e+00 | 1.70e-04 | 5.394e-03 |
| FMU -> OpenSim | 4.107e-04 | 0.00e+00 | 0.00e+00 | 0.00e+00 | 2.27e-13 | 1.1233e+03 | 0.00e+00 | 0.00e+00 | 8.151e-03 |
| OpenSim -> FMU | 5.102e-04 | 0.00e+00 | 0.00e+00 | 0.00e+00 | 2.27e-13 | 1.1233e+03 | 0.00e+00 | 0.00e+00 | 1.144e-02 |
| FMU -> FEM | 6.103e-04 | 1.67e-16 | 4.44e-16 | 0.00e+00 | 0.00e+00 | 1.1233e+03 | 1.73e-17 | -3.79e-20 | 1.531e-02 |

Four results follow, and each one is now a regression assertion:

- Angle, angular velocity, torque, and rigid mechanical energy are continuous to round-off across
  every directed pair. The canonical interface carries them exactly.
- Leaving FEM drops the entire elastic strain energy. At 50 N*m that is 2.12e-04 J against a rigid
  mechanical energy of 1.60e-03 J, so roughly 13 percent of the instantaneous mechanical energy
  disappears from the accounting at the first switch. The loss scales quadratically with the drive:
  at 5 N*m it is 2.12e-06 J.
- Re-entering FEM starts from a strain-free rigid configuration. The target strain energy is
  approximately 5e-20 J, which is the quadrature floor rather than a physically recovered field. The
  small negative `elastic_energy_lost` for a rigid-to-FEM transfer is that floor.
- Angular acceleration is discontinuous only when the FEM state is left behind: 2.4e-05 rad/s^2 on
  an acceleration of 1.12e+03 rad/s^2, a relative jump near 2e-08. It scales with the elastic
  content for the same reason. Rigid-to-rigid and rigid-to-FEM transfers agree to 2.3e-13 rad/s^2
  because both sides recompute the acceleration from the same torque and inertia.

The honest summary is that the canonical rigid state is conserved exactly, while the flexible state
is not transported at all: it is dropped on FEM exit and rebuilt as a rigid configuration on FEM
entry. Frequent FEM switching therefore removes elastic energy from the system monotonically.

### Real angle-region macro-step study

The production `MasterPendulumSwitchConfig` was exercised on `abs(theta)` with real backends, for
one descending and one ascending boundary crossing, at macro steps of 1e-4 s, 1.5e-4 s, and
2.5e-4 s. Without gravity, contact, or drive torque the angle is exactly linear in time, so the
band-edge crossing has a closed form to compare against.

| Boundary | Macro step [s] | Switch time [s] | Closed form [s] | Deviation [s] | abs(theta) [rad] | Band edge [rad] | Distance to grid [s] |
|---|---|---|---|---|---|---|---|
| descending-into-FEM | 1.00e-04 | 4.270019531e-04 | 4.269908170e-04 | +1.11e-08 | 0.069999777 | 0.070000000 | 2.70e-05 |
| descending-into-FEM | 1.50e-04 | 4.270019531e-04 | 4.269908170e-04 | +1.11e-08 | 0.069999777 | 0.070000000 | 2.30e-05 |
| descending-into-FEM | 2.50e-04 | 4.270019531e-04 | 4.269908170e-04 | +1.11e-08 | 0.069999777 | 0.070000000 | 7.30e-05 |
| ascending-into-FMU | 1.00e-04 | 9.599609375e-04 | 9.599310886e-04 | +2.98e-08 | 0.279253277 | 0.279252680 | 4.00e-05 |
| ascending-into-FMU | 1.50e-04 | 9.599487305e-04 | 9.599310886e-04 | +1.76e-08 | 0.279253033 | 0.279252680 | 5.99e-05 |
| ascending-into-FMU | 2.50e-04 | 9.599609375e-04 | 9.599310886e-04 | +2.98e-08 | 0.279253277 | 0.279252680 | 4.00e-05 |

The descending case starts at 4.5 degrees with `omega = -20 rad/s` in the OpenSim region and enters
FEM at the lower band edge `0.075 - 0.005`. The ascending case starts at 14.9 degrees with
`omega = +20 rad/s` and enters FMU at the upper band edge `deg2rad(15) + deg2rad(1)`. Both confirm
the hysteresis contract: the switch lands on the armed band edge, not on the breakpoint.

Placement deviates from the closed form by at most 3.0e-08 s and spreads by at most 1.2e-08 s
across macro steps that differ by a factor of 2.5. Both bounds are more than three orders of
magnitude below the smallest macro step. No switch lands on a communication point; the closest
approach is 2.3e-05 s.

### Test layout

The three real-backend suites now share one harness in
`tests/integration/demos/controlled_pendulum/real_backend_support.py`. It builds the coarse
first-order mesh with contact, gravity, and animation disabled, and it offers both the undriven
system and the constant-torque system. Each suite keeps its own `importorskip` guards and calls
`require_euler_pendulum_fmu()` at module level.

- `test_master_pendulum_backends.py` keeps the Milestone 4 and 5 transaction, lifecycle, rollback,
  and trial-purity coverage.
- `test_master_pendulum_transfer_fidelity.py` is the driven six-pair characterization.
- `test_master_pendulum_switch_placement.py` is the real angle-region macro-step study.

No wall contact, gravity, or animation was added to the fast gate. The whole real-backend switching
slice, including the master-pendulum unit tests, runs in 18.29 s.

### Measured verification on Windows, Python 3.13.5, Pytest 9.1.1

- repository and demo Ruff checks: passed;
- Ruff formatting of every file changed by this milestone: passed;
- MyPy: passed for all 27 source files;
- fast real-backend switching slice: **64 passed in 18.29 s**;
- full backend-enabled suite with coverage: **689 passed, 1 skipped**, 89% coverage, in 195.56 s;
- strict offline Sphinx documentation: passed without warnings;
- locked `uv build --no-sources`: passed.

The final commands were:

```powershell
.\.venv\Scripts\python.exe -m ruff check --no-cache syssimx tests demos/ControlledPendulum/src
.\.venv\Scripts\python.exe -m mypy syssimx --ignore-missing-imports --python-version 3.13 --cache-dir "$env:TEMP\syssimx-m6-mypy"
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp "$env:TEMP\syssimx-m6-fast" tests/integration/demos/controlled_pendulum/test_master_pendulum_backends.py tests/integration/demos/controlled_pendulum/test_master_pendulum_transfer_fidelity.py tests/integration/demos/controlled_pendulum/test_master_pendulum_switch_placement.py tests/unit/demos/controlled_pendulum/test_master_pendulum_switching.py -q
$env:COVERAGE_FILE = "$env:TEMP\syssimx-m6.coverage"
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp "$env:TEMP\syssimx-m6-full-pytest" tests --cov=syssimx --cov-report=term-missing -q
$env:SYSSIMX_DOCS_OFFLINE = "1"
.\.venv\Scripts\python.exe -m sphinx -q -b html -W --keep-going -d "$env:TEMP\syssimx-m6-doctrees" docs "$env:TEMP\syssimx-m6-docs"
uv build --no-sources --out-dir "$env:TEMP\syssimx-m6-dist"
```

The unchanged skip is the generic FMU fixture whose archive contains `linux64` and C sources but no
`win64` binary. `ruff format --check` still reports pre-existing deviations in files this milestone
did not touch, including the aligned assignment blocks in `fem_pendulum.py`; reformatting them
belongs to a separate cleanup.

### First CI run of the stack

The branch reached GitHub Actions for the first time in pull request #6. The `test-fem` job passed
on ubuntu with `[dev,fmu,fem,opensim]`, so all three real-backend suites, the linux FMUs, and the
Milestone 6 fidelity and placement studies reproduce off Windows. The `docs` job passed.

The three `test` matrix jobs failed to collect
`tests/unit/demos/controlled_pendulum/test_master_pendulum_switching.py`. That module guarded only
on the demo orchestration module, but `master_pendulum.py` imports the backend classes
unconditionally while `demos/.../components/__init__.py` exports only the models whose backend is
installed. Without NGSolve the failure is an `ImportError`, not a `ModuleNotFoundError`, so
`pytest.importorskip` re-raised it instead of skipping.

`3e62c07` guards the module on ngsolve, fmpy, and opensim and marks it `fem`, `fmu`, and `opensim`,
matching every sibling suite. The module is now skipped in the main matrix job and runs in the
backend job, where it previously ran in neither: `pytest -m fem` collects 118 tests instead of 87.
The defect was latent from `61c53c8` in Milestone 3, because the stack had never been pushed.

This is a standing lesson for the remaining milestones. Local verification on Windows with every
backend installed does not exercise the partial-install path that the main CI matrix uses, so a
branch should reach CI before its milestone is declared closed.

### Limitations

- The characterization covers the torque-driven, contact-free, gravity-free regime on one coarse
  first-order mesh. It does not cover wall contact, gravity, a refined mesh, or the CVODE FMU.
- The elastic loss is quantified but not compensated. No projection, energy-matching, or
  pair-specific adapter was added; MC-10's optional adapter items stay open by design.
- Only the two boundaries of the production policy that the free-motion trajectory can reach in a
  fast test were studied. A crossing under load, where the FEM elastic content changes the indicator
  signal itself, is not covered.
- The strain energy read at a FEM exit is the value at the localized switch time. Elastic energy the
  FEM had already exchanged with the rigid motion before that instant is not attributed.
- The reported `alpha` jump is the difference between the FEM rigid proxy and the rigid torque
  balance. It is not an independent error estimate of either.

### Next steps

1. **EVID-01:** re-run the migrated performance notebook and separate accepted from trial work now
   that speculative effects are isolated.
2. **EVID-02 and EVID-03:** the convergence and switch-placement ranking study on the smooth
   pendulum, reporting error, work, and configuration together.
3. **HARD-01 and HARD-02:** standalone OpenSim contract tests, a platform-complete generic FMU
   fixture, and a scheduled slow contact/FEM physics gate that can carry the contact-state
   fidelity question this milestone deliberately kept out of the fast tests.
4. **MC-10 remainder:** decide whether the flexible state deserves transport at all. The measured
   loss is now quantified, so the choice between accepting it, warning on it through an enforced
   `energy` tolerance, or adding a pair-specific adapter can be made on evidence.

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

The switching mechanism has now been consolidated. `MultiComponent` exposes one public automatic
switching API, `set_switch_regions()`, and resolves transitions only from localized generated
boundaries. Transactional transfer and checkpoint/trial behavior remain explicit internal
contracts, and every accepted transfer now declares and measures what it preserves and loses.
Remaining work concerns backend coverage, performance evidence, and cleanup outside the decision
mechanism.

The design decision is to expose exactly one public runtime-switching mechanism:
generalized, event-localized region switching through `set_switch_regions()`. It is the only
mechanism that combines declarative configuration, support for three or more models,
direction-aware transitions, event-time localization, and signal hysteresis. Grid-polled selectors
and user-managed fixed-target indicators were removed after all examples and tests migrated.

The recommended direction is an incremental consolidation rather than a rewrite:

1. Fix the concrete correctness and lifecycle defects.
2. [x] Generalize `set_switch_regions()` as the sole public switching API.
3. [x] Remove `mode_selector`, public `add_switch_indicator()`, dwell timing, pending repair, and
   the arbitration concepts needed only when multiple mechanisms coexist.
4. Keep state transfer and checkpoint/trial behavior as explicit internal contracts.
5. [x] Complete the consumer migration before deleting the legacy paths; retain real cross-backend
   integration coverage as HARD-01.

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

## Findings and proposed solutions

### MC-01 — The case-study migration to localized switching is incomplete

**Priority:** High

**Status:** Resolved by Milestone 3 for mechanism and consumer migration. Fresh performance and
convergence measurements remain EVID-01 through EVID-03.

The default `MasterPendulum`, notebooks 5 and 6, the performance and verification notebooks,
tutorials, documentation, and tests now use generated regions. `MasterPendulumSwitchConfig`
defines the canonical radians-based `abs(theta)` breakpoints and bands once. Fixed-model examples
opt out explicitly with `switch_config=None`; no selector fallback or time hold remains.

**Suggested solution**

- [x] Migrate every selector/fixed-indicator consumer to `set_switch_regions()`.
- [x] Configure one canonical radians-based `abs(theta)` policy for the default MasterPendulum.
- [x] Use explicit, nonzero bands and remove time holds from runtime switching.
- [ ] Re-run the expensive performance study and record occupancy and speculative-work results
  under EVID-01.
- [ ] If actual contact distance becomes the intended signal, first expose a shared
  `contact_distance` or `contact_proxy` output across all three models.

**Acceptance criteria**

- [x] State-dependent switches are localized independently of macro-step size.
- [x] Switch times converge according to `tol_time`/`tol_value`, not `dt`.
- [x] Configuration and documentation describe the `abs(theta)` signal actually used.
- [ ] The performance notebook contains fresh executed results for occupancy, switch count, and
  speculative work; tracked separately as evidence rather than migration work.

### MC-02 — MasterPendulum bypasses base-class region initialization

**Priority:** High

**Status:** Resolved by Milestone 1. `MultiComponent.initialize()` owns the shared reconciliation
invariant even when a subclass customizes model initialization order.

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

**Status:** Resolved by Milestone 2 for framework history, recursive trial state, and the existing
FEM/master-pendulum observer hooks. Real FMU/OpenSim backend execution remains part of HARD-01.

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

**Status:** Resolved by Milestone 2.

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

**Status:** Resolved by Milestone 1. Bands are positive, each boundary is represented once, and the
localized bracket carries its crossing direction through dispatch.

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

**Status:** Resolved by Milestone 1 with authoritative `active_region_index`.

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

**Status:** Resolved by Milestone 1. Dwell and pending-repair state were removed.

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

**Status:** Resolved for `SwitchRegions` by Milestones 1 and 2.

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

**Status:** Resolved by Milestone 3.

The former selector, fixed-target indicator dictionary, target resolver, polling, and
registration-order behavior have been deleted. Generated region boundaries are the only automatic
decision source.

**Suggested solution**

- [x] Make `set_switch_regions()` the only public runtime-switching configuration method.
- [x] Remove selector polling and public fixed-target indicator registration after migration.
- [x] Keep generated boundary indicators private and direction-aware.
- [x] Keep one private transactional operation for region transition and state transfer.

**Acceptance criteria**

- [x] It is impossible to configure two competing automatic model-selection paths.
- [x] Every automatic runtime transition originates from a localized region crossing.
- [x] The implementation contains no registration-order or policy-precedence behavior.

### MC-10 — State transfer has no explicit fidelity or conservation contract

**Priority:** Low

**Status:** Resolved for the declaration and measurement work by Milestone 6. Transfers are atomic,
have a canonical unit-normalized acceptance contract for angle, angular velocity, and torque, and
now declare and measure what they lose. Whether the lost flexible state should be transported at all
is an open design decision, not a missing contract.

The transfer interface preserves a small human-readable state. Its meaning and its losses are now
declared per backend in `BACKEND_STATE_SEMANTICS` and resolved per directed pair by
`transfer_state_semantics()`:

- FEM exports a rigid proxy for a deformable field and discards elastic deformation, elastic strain
  energy, Cauchy and von Mises stress fields, Newmark step history, and contact gap history.
- Re-entering FEM reconstructs rigid displacement, velocity, and acceleration fields and sets the
  Newmark previous-step vectors equal to the current step.
- OpenSim recreates its SimTK state and integration manager and discards integrator step-size and
  error history.
- Both checked-in FMUs are reconstructed from physical variables rather than complete solver state;
  their FMI capability metadata explicitly declares native state get/set and serialization
  unavailable.

Angular acceleration is exported by every backend and accepted by none, so each target recomputes it
from the torque and its own dynamics.

The measured behavior on the driven six-direction trajectory is recorded under Milestone 6. Angle,
angular velocity, torque, and rigid mechanical energy are continuous to round-off. The whole elastic
strain energy is dropped on every FEM exit, roughly 13 percent of the instantaneous mechanical
energy at 50 N*m, and is never restored on FEM entry. Frequent FEM switching therefore removes
elastic energy monotonically, which is now a quantified property rather than an unknown.

**Suggested solution**

- [x] Define a canonical `PendulumState` with explicit units.
- [x] Add optional fidelity-specific fields only when a backend can supply them consistently; the
  FEM strain energy is carried as an optional term of `PendulumEnergy`.
- [ ] Support adapters keyed by `(source_mode, target_mode)` if pair-specific projection becomes
  necessary; the current canonical mapping needs target-specific renaming only. Deliberately
  deferred until the measured loss justifies the mechanism.
- [x] Define and test preserved angle, angular-velocity, and torque invariants for every transition.
- [x] Define energy, acceleration, contact-state, and flexible-field loss semantics.
- [x] Measure acceleration and mechanical-energy discontinuities for every directed transition.
- [x] Return immutable accepted-transfer diagnostics in the switch record.
- [x] Validate canonical continuity after target import and output refresh within configurable
  tolerances.
- [x] Make switching transactional so a failed import or domain validation leaves the previous mode
  fully intact.
- [ ] Repeat the characterization with wall contact enabled, on the scheduled slow physics gate
  tracked by HARD-02.

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

### MC-14 — Tests validate generic mechanics but not the real three-backend composition

**Priority:** Low

**Status:** Resolved for the switching composition by Milestones 4 through 6. Generic localization,
hysteresis, chronological multi-boundary processing, rollback, and reset scenarios use generated
region boundaries. Fast automated tests now switch one real `MasterPendulum` through all six
directed FEM/FMU/OpenSim pairs, validate real reset/reinitialize, resource ownership,
failed-transfer rollback, and trial purity, characterize what each transfer preserves and loses,
and localize the production angle-region policy across macro-step sizes. Only the
backend-independent contract tests remain, and they belong to HARD-01.

The real trajectory detects initialization-order and canonical projection regressions.
Backend-specific speculative UI/history effects and resource lifecycle replacement have dedicated
assertions without contact, gravity, or animation work.

**Suggested solution**

Add layered tests:

1. [ ] Backend-independent contract tests for every component implementation; tracked with HARD-01.
2. [x] Pairwise transfer tests for FEM ↔ OpenSim, FEM ↔ FMU, and OpenSim ↔ FMU.
3. [x] A short three-mode trajectory test with switch-time and continuity assertions.
4. [x] Real-backend trial-step purity tests for history, monitoring, visualization, and logs;
   generic transactional coverage already exists.
5. [x] Real-backend reset/reinitialize tests covering active region, active mode, switch history,
   and resource cleanup; generic lifecycle coverage already exists.
6. [x] Macro-step-independence tests for the real angle-region configuration; deterministic region
   localization coverage already exists.
7. [x] Transfer-fidelity tests that measure the acceleration and energy a switch does not carry.

Tests dedicated only to the deleted mechanisms were removed. Their useful localization and rollback
assertions were retained against generated region boundaries.

The three real-backend suites are marked `fem`, `fmu`, and `opensim` and run in the existing backend
CI job. They stay fast by sharing one coarse mesh through
`tests/integration/demos/controlled_pendulum/real_backend_support.py` and by excluding contact,
gravity, and animation. Contract tests remain runnable with lightweight fakes.

## Existing work to retain during consolidation

### Region-map switching provides the canonical foundation

`MultiComponent.set_switch_regions()` closes three earlier problems in hand-registered switching:

- the target is derived from the crossed boundary and direction instead of registration order;
- one declaration generates and validates all boundary indicators and their bands.
- a nonzero band separates entry and exit thresholds to prevent threshold chatter.

This behavior is covered by `TestGeneratedRegionEventRegistration`,
`TestGeneratedRegionEventEvaluation`, `TestSwitchRegions`, and
`TestRegionSwitchingInvariants`. Preserve the region mapping, directional target resolution, and
true event localization.

Removing dwell makes pending repair unnecessary. Do not replace it with unconditional polling of
the region map: during development, polling read a speculative output and placed every switch on a
communication point at 0.054 s instead of the 0.055 s band edge. Reconcile the initial region once
at initialization; after that, transitions must come only from localized boundary crossings. Keep
regression tolerances much smaller than the macro step and use an incommensurate macro grid to
distinguish localization from grid placement.

### Trial rollback now restores wrapper output ports

Hybrid trial steps previously restored solver state but left cached output ports at `t + dt`.
Downstream Gauss-Seidel consumers could therefore read a future value while the component state had
returned to `t`.

`HybridAlgorithm` now captures state, inputs, output values, and output timestamps in one rollback
record and restores them together. The recursive trial context now suppresses framework history and
the known MasterPendulum/FEM observer effects as recorded under Milestone 2.

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

The report half of this design is implemented in the domain layer rather than as a separate
service: `MultiComponent._build_transfer_report()` is the hook, and `PendulumTransferReport`
carries preserved invariants, measured acceleration and energy discontinuities, and the declared
state semantics of the directed pair. Extracting a standalone `StateTransfer` object is only worth
doing if a second composite needs the same machinery.

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
config = MasterPendulumSwitchConfig(
    breakpoints=(0.075, np.deg2rad(15.0)),
    modes=("FEM", "OpenSim", "FMU"),
    bands=(0.005, np.deg2rad(1.0)),
)
plant = MasterPendulum(switch_config=config)
```

The canonical thresholds are now defined once in `MasterPendulumSwitchConfig`. If later physical
evidence favors an actual contact-distance signal, revise the typed policy and all measurements
together. Test-only forced cycling already lives in an external signal harness.

## Staged implementation plan

### Stage 1 — Correctness fixes

- [x] Preserve the final sign-change bracket during event collection instead of making event existence
  depend on `tol_value`.
- [x] Represent each boundary once with crossing direction, and require a nonzero band.
- [x] Track the active region index so repeated model assignments are unambiguous.
- [x] Remove minimum dwell timing and pending region repair.
- [x] Complete reset semantics.
- [x] Ensure `MasterPendulum` runs shared post-initialization logic.
- [x] Stop known speculative history/monitoring/visualization changes.
- [x] Validate rollback capability for all reachable modes.
- [x] Add regression tests for each fix.

### Stage 2 — Consolidate on region switching

- [x] Generalize and document `set_switch_regions()` as the sole public switching API.
- [x] Replace fixed-target/boundary dictionaries with the immutable region configuration and generated
  typed boundary records.
- [x] Migrate generic localization, rollback, and reset tests to generated region boundaries.
- [x] Migrate downstream examples before deleting selector and public fixed-indicator paths.
- [x] Remove arbitration, precedence, dwell, and deferred-request code that is no longer needed.

### Stage 3 — Formalize state transfer and checkpoints

- Add canonical or pairwise state adapters and `TransferReport`.
- [x] Make switches transactional.
- [x] Add the recursive checkpoint/trial protocol.
- [x] Remove direct manipulation of private component flags from `HybridAlgorithm`.

### Stage 4 — Migrate MasterPendulum

- [x] Move the localized angle policy into explicit, reusable `MasterPendulum` configuration and
  migrate notebooks 5 and 6 away from selector-only switching.
- [x] Remove the time-driven demo cycle from production switching; keep the forced-cycle experiment in
  an external test harness.
- [x] Move thresholds and signal bands into typed configuration.
- [x] Add real-backend pairwise and end-to-end switching tests.
- [x] Document which physical quantities are preserved or lost for each transition.
- [x] After all examples and tests use regions, remove `mode_selector`, public
  `add_switch_indicator()`, and their fixed-target/registration-order infrastructure.

### Stage 5 — Cleanup

- Remove dead state fields and unused adapter APIs.
- Consolidate switch logging with system history.
- Automate port unification and initialization.
- Replace backend-private accesses with public capability/metadata interfaces.
- [x] Update tutorials and notebooks to demonstrate the unified API only.

## Prioritized next steps

Milestones 1 through 6 established the release-candidate switching mechanism, its canonical
real-backend transfer gate, its lifecycle/rollback guarantees, and the measured fidelity of every
directed transfer. The remaining order focuses on paper/release evidence without reopening the
public API.

1. **Remove avoidable speculative work:** EVID-01. Re-run the migrated performance notebook and
   measure accepted versus trial work now that speculative effects are isolated.
2. **Produce numerical evidence:** EVID-02 and EVID-03 together on the smooth pendulum, followed by
   EVID-04 and EVID-05 for a representative benchmark and independent-master comparison.
3. **Strengthen the validation gate:** HARD-01 and HARD-02. Add standalone OpenSim contracts,
   platform-complete generic FMU fixtures, and a scheduled contact/FEM physics run.
4. **Simplify the remaining internals:** MC-11 and MC-12. Remove dead adapter/state fields,
   consolidate switch history, automate port lifecycle, and replace backend-private metadata
   access. Do not add another switching policy hierarchy.
5. **Improve time semantics incrementally:** finish TIME-04, then introduce integer ticks in the
   master layer. Address TIME-01 through resolution negotiation before propagating ticks through
   every component API.
6. **Archive a reproducible minor release:** HARD-03, HARD-04, and REPRO-01. Update metadata and tag
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
