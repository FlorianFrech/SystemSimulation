# Evidence notebooks

Six notebooks: five produce claim evidence and one qualifies the FEM threading
policy. Each declares one `Scenario`, produces focused figures or tables, and
emits its numbers through `record()` so nothing reaches the manuscript by being
read off a plot.

| Notebook | Claim | Register IDs | Backends needed |
|---|---|---|---|
| `01_mechanism.ipynb` | Switch placement and state handover against an analytic reference | `V1` | none — pure Python |
| `02_baseline.ipynb` | Convergence of the co-simulated loop to the monolithic reference | `V2` | FMI, OpenModelica |
| `03_switching.ipynb` | RQ2 handover cost: per-switch transfer report, boundary localization | `T1`, `F3` | FMI, OpenSim, FEM, OpenModelica |
| `04_performance.ipynb` | RQ3 runtime trade-off, both contact regimes (`CONTACT` toggle) | `T2_*`, `F5_*` | FMI, FEM |
| `05_placement.ipynb` | RQ1 Campaign A: placement error and observed order | `F1`, `F2` | FMI, FEM |
| `06_determinism.ipynb` | Reproducibility qualification for FEM-backed evidence | `DET_threads` | FEM |

`V1` and `V2` are **not** register entries. `guideline/planning/evidence_plan.md`
section 3 owns `F1`–`F7` and `T1`–`T4`, and nothing enters the manuscript that is
not on that list. The two `V` files exist so the supporting numbers quoted in
that plan's section 1 are machine-readable; adding register rows for them is an
author decision.

## Shared code

`evidence/` holds everything more than one notebook needs: the switching plant,
the control loop, the phase instrumentation, and the analysis helpers. Before it
existed, notebooks 6 and 7 alone shared 25 definitions by copy, and a fix applied
to one did not reach the other.

```python
from evidence import repo_root
REPO = repo_root()        # puts the repo and notebooks/ on sys.path
import evidence as ev     # heavy submodules resolve lazily from here on
```

Attribute access is lazy on purpose: `repo_root` has to be importable before
`sys.path` points at the repository, and `01_mechanism.ipynb` must not be made to
import the FEM backend it does not use.

| Module | Holds |
|---|---|
| `scenario.py` | `Scenario`, and the two declared configurations |
| `plant.py` | `SwitchingPendulum`, `FemToFemPendulum`, the region keys |
| `loop.py` | FMU discovery, the closed control loop, `assemble_system` |
| `instrument.py` | Phase attribution: accepted, trial, bisection, events |
| `analysis.py` | Mode timelines, error metrics, `run_measured_case` |

## Where numbers go

`record()` writes one JSON file per register entry into the **paper** repository's
`results/`, with provenance: producing notebook, interpreter, machine, SysSimX
version and `git describe`, and the full `Scenario`.

Set `SYSSIMX_PAPER_RESULTS` to that directory. Unset, `paper_results_dir()` falls
back to a sibling `SysSimX-Framework-Paper` checkout, which is a convenience for
the usual layout and not a contract.

A run with `SMOKE = True` is written to `<ID>.smoke.json` and is **not a result**.
Never quote it.

## Toolchain

`02_baseline.ipynb` and `03_switching.ipynb` build an OpenModelica reference and
pin the compiler to 1.26.3, matching the paper's frozen comparison environment.
Override with `SYSSIMX_OM_HOME`. They fail loudly on a version mismatch: the
reference is only comparable within one toolchain.

## Running

Only `01_mechanism.ipynb` is gated in CI — it is the one notebook with no FMU or
FEM dependency. The rest need the demo artifacts under
`demos/ControlledPendulum/artifacts/` and the ngsolve/opensim environment.

`demos/diagnostics/fmu_memory.ipynb` measures the FMU memory footprint for
`issues.md` HARD-07. It is engineering evidence, not paper evidence, which is why
it does not live here.
