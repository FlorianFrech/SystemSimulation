# SysSimX — Implementation history

Detailed records of the runtime-switching redesign and its verification. These
are historical: they record what was done, the environment it was measured in,
and the evidence collected at the time. Release-facing summaries live in
[`CHANGELOG.md`](CHANGELOG.md); work still open is in [`issues.md`](issues.md).

Nothing here should be read as a description of current behaviour. Where a
record and the code disagree, the code is right.

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
- case study: `syssimx_examples/controlled_pendulum/orchestration/master_pendulum.py`;
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
.\.venv\Scripts\python.exe -m ruff check --no-cache syssimx tests syssimx_examples/controlled_pendulum/components/fem/fem_pendulum.py syssimx_examples/controlled_pendulum/components/fmu/fmu_pendulum.py
.\.venv\Scripts\python.exe -m ruff check --no-cache syssimx_examples/controlled_pendulum/components/opensim/opensim_pendulum.py tests/integration/demos/controlled_pendulum/test_master_pendulum_backends.py
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

## Milestone 7 implementation record

Milestone 7 was implemented on 2026-08-21 on branch `docs/notebook-execution-gate`, after the
switching stack merged to `main` as `c670eb9`. It restores the backend-free switching notebooks and
closes the gap that let them reach `main` unexecuted. It also uncovered a native defect that blocks
the two master-pendulum tutorials.

- `1b3e033` re-executes the backend-free switching notebooks;
- `eca3e4c` adds the nbmake CI job and declares the dependency.

### Why the notebooks were empty

`docs/conf.py` sets `nb_execution_mode = "off"`, so Sphinx publishes whatever outputs a notebook
already carries. Milestone 3 cleared the expensive case-study notebook outputs rather than keeping
stale ones, and nothing ever re-executed them. Nine tracked notebooks therefore carried zero
outputs, four of them published pages covering the switching feature, and every CI job stayed green
because nothing executed a notebook.

| Notebook | Wave | State after this milestone |
|---|---|---|
| `docs/03_core_tutorials/03_advanced/04_multi_component_switching.ipynb` | 1 | executed, gated |
| `notebooks/03_multi_comp_verification.ipynb` | 1 | executed, gated |
| `docs/04_tool_integration/04_master_pendulum/01_master_pendulum_basics.ipynb` | 1 | blocked by HARD-05 |
| `docs/04_tool_integration/04_master_pendulum/02_master_pendulum_switching.ipynb` | 1 | blocked by HARD-05 |
| `docs/05_case_study/05_multi_model_switching.ipynb` | 2 | deferred to the evidence work |
| `notebooks/05_casestudy_model_switching.ipynb` | 2 | deferred, EVID-03 |
| `notebooks/06_casestudy_performance.ipynb` | 2 | deferred, EVID-01 and EVID-04 |
| `notebooks/performance.ipynb` | 2 | deferred, EVID-01 |
| `demos/.../master_pendulum/test_master_pendulum_hybrid.ipynb` | n/a | development scratch, not published |

Wave 2 is deliberately not executed yet. EVID-02 and EVID-03 are meant to share one refinement
study and EVID-04 needs a longer horizon with per-bucket timing and repetitions, so executing those
notebooks before the experiment design is settled would bake in the superseded 0.4 s, two-switch
experiment and spend the FEM budget twice.

### Wave 1 results

Both backend-free notebooks execute cleanly against the merged tree with no error outputs. This is
the first end-to-end confirmation that the Milestone 3 consumer migration works outside the test
suite.

The two master-pendulum tutorials did **not** execute in their published configuration at the time
of this milestone. The kernel died with Windows exception `0xc0000374`, heap corruption, inside
`fmi2FreeInstance`. A diagnostic run that forced `fmu_solver="euler"` without modifying either
notebook completed every cell of both, so the notebook content was healthy against the region API and
the sole blocker was the CVODE FMU defect recorded as HARD-05. Both tutorials execute and are
committed with outputs since that defect was worked around.

### Environment provenance

The notebooks were executed with the only registered Jupyter kernel, the Anaconda `env-312`
environment, not the project `.venv`:

| Item | Recorded value |
|---|---|
| Python | 3.12.13 |
| ngsolve | 6.2.2601 |
| fmpy | 0.3.28 |
| opensim | 4.5.2 |
| numpy / scipy / matplotlib | 2.0.2 / 1.17.1 / 3.10.8 |
| pint | 0.25.2 |

`syssimx` resolved to the working tree. Pinning this environment and recording it with the executed
outputs belongs to REPRO-01; until then, published notebook outputs and the tested environment are
not the same thing.

### The notebook execution gate

A `notebooks` CI job runs `pytest --nbmake` over the two backend-free notebooks. It installs the
LaTeX toolchain because `notebooks/plot_setup.py` renders thesis-style figures with `usetex` and
`siunitx`. `nbmake` was added to both mirrored dev dependency lists. Locally the gate completes in
9.5 s.

The two master-pendulum tutorials were not gated while HARD-05 blocked them. They execute again
since the workaround, so gating them is now a question of runner cost rather than of a crash. The
Wave 2 notebooks are not gated because they are long-running evidence runs, not tutorials; the
scheduled physics gate under HARD-02 is the right home for them.

### Output hygiene

Executing notebook 3 exposed that `set_professional_style()` returns the `pyplot` module. Called as
the last expression of a cell, it renders a repr containing the executing machine's absolute install
path into a published output. The call in notebook 3 now ends with a semicolon.

The return value is kept because several development notebooks under `demos/` use
`plt = set_professional_style()`. Five published notebooks still call it as a bare last expression
and will leak the same way when they are executed, so the semicolon has to be applied as each one is
re-run. Two published notebooks already carry leaked paths from earlier runs. Both points are
tracked as HARD-06.

### Measured verification

- `pytest --nbmake` over both Wave 1 notebooks: **2 passed in 9.5 s**;
- repository-wide scan for machine-specific absolute paths in tracked notebook outputs: two
  published notebooks affected, both pre-existing and unrelated to switching;
- workflow YAML parses and declares jobs `test`, `test-fem`, `notebooks`, `docs`, `build`.

The final commands were:

```powershell
$env:PYTHONPATH = "C:\Users\flori\source\repos\FlorianFrech\SystemSimulation"
jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=900 notebooks/03_multi_comp_verification.ipynb
jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=900 docs/03_core_tutorials/03_advanced/04_multi_component_switching.ipynb
pytest -p no:cacheprovider --nbmake --nbmake-timeout=900 docs/03_core_tutorials/03_advanced/04_multi_component_switching.ipynb notebooks/03_multi_comp_verification.ipynb
```

The LaTeX package set in the CI job (`texlive-latex-extra`, `texlive-science`, `dvipng`,
`cm-super`) could not be validated on this Windows host and is verified by the first CI run.

## Proposed target architecture

Recorded before Milestones 1 through 6, which implemented it. Kept as the design
rationale; the API reference describes what was actually built.

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

