# Documentation Update Plan — Tutorials, Tool Integration, Case Study

Status of the scan: 2026-07-19. Covers `03_core_tutorials/`, `04_tool_integration/`, `05_case_study/` (23 notebooks).
Reference for the target style: `01_getting_started/02_quickstart.ipynb` and `03_core_tutorials/02_intermediate/04_declarative_systems.ipynb` (already modernized).

## What Is Good (Keep)

- Consistent pedagogical skeleton in most notebooks: Overview → Learning Goals → Prerequisites → build → run → plot → Conclusion.
- Physics content, analytical reference solutions, and plot quality are strong throughout.
- Tool-integration notebooks correctly start with the standalone tool (raw fmpy / OpenSim Manager / NGSolve) before wrapping in SysSimX — good didactics, keep this structure.
- Hybrid/advanced tutorials have valuable zoomed event-locality plots and superdense-time explanations.
- Case study notebooks map cleanly onto the thesis benchmark scenarios.

## Cross-Cutting Issues (Apply to Every Notebook)

1. **Legacy results access.** `system.run(...)` return value is ignored everywhere; results are pulled via `system.get_history()` or per-component `get_history_arrays()`. Migrate to `result = system.run(...)` + `result["Comp"]` / `result.to_dataframe()`. Mention `result.events` where events are involved (hybrid/advanced/case-study).
2. **No structural inspection.** No notebook uses `system.describe()`. Add one `print(system.describe())` after assembly where it adds value (esp. algebraic-loop and multi-generation systems).
3. **Missing outputs.** Many code cells have no stored outputs; docs build has `nb_execution_mode = "off"`, so readers see empty cells. Re-execute each batch after editing and commit with outputs.
4. **Debug-logging boilerplate.** Repeated "Enable debug output for the syssimx package" cells (8 notebooks). Keep at most one short logging cell where the log output is actually discussed; delete elsewhere.
5. **Cross-links.** Add/refresh `{doc}` next-step links between related notebooks (e.g. algorithms ↔ algebraic loop ↔ IJCSA case study; hybrid tutorials → contact case studies; declarative tutorial from fundamentals).
6. **Housekeeping.** Normalize headings (some numbered comment-headings like `# 8) ...` inside code cells should become markdown), remove stale `execution_count` noise by re-running top-to-bottom, keep generated files (`*.svg`, CSVs) out of git.

## Per-Notebook Findings and Actions

### 03_core_tutorials / 01_fundamentals

| Notebook | Findings | Actions |
|---|---|---|
| 01_simple_pendulum | Solid unit-handling intro; `get_history`; option-comments as code headings | Migrate results API; tidy option cells into markdown; link to declarative tutorial |
| 02_importing_fmus | `get_history`; platform-selection cell is comment-driven | Migrate results API; clean platform selection; show `describe()` |
| 03_first_system | Feedback system; `get_history` | Migrate results API; add `describe()`; add next-step links |

### 03_core_tutorials / 02_intermediate

| Notebook | Findings | Actions |
|---|---|---|
| 01_comparing_algorithms | `get_history` in comparison loops | Migrate to `SimulationResult`; consider `to_dataframe()` for the error table |
| 02_algebraic_loop | `get_history`; debug-logging cell | Migrate results API; `describe()` is a natural fit (shows detected SCC); trim logging |
| 03_simple_hybrid_system | `get_history`; debug-logging cell | Migrate results API; use `result.events` for event table; trim logging |
| 04_declarative_systems | New, already modern | No action |

### 03_core_tutorials / 03_advanced

| Notebook | Findings | Actions |
|---|---|---|
| 01_hybrid_event_chain | Per-component `get_history_arrays()`; debug logging; heavy masking code for zoom plots | Migrate to `result[...]` + `result.events` (event times replace manual masks); trim logging |
| 02_hybrid_strong_simultaneity | Same pattern | Same migration |
| 03_hybrid_internal_reporting | Same pattern; numbered `# n)` code-comment headings | Same migration; convert numbered comments to markdown steps |

### 04_tool_integration / 01_modelica

| Notebook | Findings | Actions |
|---|---|---|
| 01_modelica_pendulum_basics | Raw-fmpy intro OK; `get_history` in SysSimX part | Migrate results API; keep raw-fmpy section as-is |
| 02_modelica_pendulum_contact | `get_history`; good plots | Migrate results API; `result.events` for contact instants |
| 03_fmu_rollback_mechanism | Clean, component-level; no legacy API | Light pass only (links, prose) |
| 04_fmu_hybrid_pendulum | `get_history`; debug logging | Migrate results API + `result.events`; trim logging |

### 04_tool_integration / 02_opensim

| Notebook | Findings | Actions |
|---|---|---|
| 01_opensim_pendulum_basics | Standalone OpenSim (Manager), no SysSimX run — intentional | Light pass: prose, links to 02/03 |
| 02_opensim_pendulum_torque | Component-level, no legacy API | Light pass; ensure outputs stored |
| 03_opensim_pendulum_contact | Component-level | Light pass; link to case-study contact |

### 04_tool_integration / 03_fem

| Notebook | Findings | Actions |
|---|---|---|
| 01_fem_pendulum_basics | Standalone NGSolve; heavy math content | Light pass; outputs; links |
| 02_fem_pendulum_torque | Same | Light pass |
| 03_fem_pendulum_contact | Largest notebook (26 code cells); many code-comment headings | Light pass + restructure comment headings into markdown |

### 04_tool_integration / 04_master_pendulum

| Notebook | Findings | Actions |
|---|---|---|
| 01_master_pendulum_basics | `get_history` | Migrate results API; `describe()` for the multi-component system |
| 02_master_pendulum_switching | `get_history`; debug logging; manual event-time extraction | Migrate to `result` + `result.events`; trim logging |

### 05_case_study

| Notebook | Findings | Actions |
|---|---|---|
| 00_overview | Markdown only | Add scenario ↔ notebook ↔ feature table incl. links; mention declarative/CLI option |
| 01_baseline | `get_history` | Migrate results API; `describe()` once |
| 02_quantization | `get_history`; case-runner function | Migrate; `to_dataframe()` fits the case comparison |
| 03_algebraic_loop | `get_history`; debug logging; PID study | Migrate; `describe()` showing the detected loop; trim logging |
| 04_rigid_contact | `get_history` | Migrate; `result.events` for impact times |
| 05_multi_model_switching | `get_history`; manual run loop | Migrate where the System API is used; keep manual loop where switching requires it |

## Batches

Each batch: edit, validate notebook structure and syntax, execute where the
installed optional backends make that practical, and run the strict docs build.

1. **Batch 1 - Fundamentals** (3 notebooks): done (2026-07-19). The two deliberately component-level tutorials include a "Running in a System" bridge using `SimulationResult`.
2. **Batch 2 - Intermediate** (3 notebooks): done (2026-07-19). Includes the `describe()`/SCC, RMSE comparison, and `result.events` patterns.
3. **Batch 3 - Advanced hybrid** (3 notebooks): done (2026-07-19). Event-driven plots use the result event log, and debug logging remains only where the output is discussed.
4. **Batch 4 - Modelica and Master Pendulum** (6 notebooks): content pass done (2026-08-12). System runs now retain `SimulationResult`; the switching tutorial uses `describe()` and `result.events`. Direct backend histories remain only for inactive models internal to `MasterPendulum`.
5. **Batch 5 - OpenSim and FEM** (6 notebooks): content pass done (2026-08-12). Standalone backend tutorials are explicitly identified as such, cross-links are current, and the FEM section now shows how to implement a structural-dynamics `FEMComponent` subclass. OpenSim 4.6 property setters and state realization were corrected during execution checks.
6. **Batch 6 - Case study** (6 notebooks): content pass done (2026-08-12). The overview maps scenarios to notebooks and capabilities; all `System.run()` calls retain their result, and structural/event inspection is shown where useful.

## Validation Status

- All 31 documentation notebooks pass `nbformat` validation, contain cell IDs, and pass a Ruff Python-syntax scan.
- All six case-study notebooks and the Master Pendulum switching tutorial execute top-to-bottom under Python 3.13. The two switching notebooks each take about six minutes locally.
- The OpenSim contact component initializes and advances with contact under OpenSim 4.6.
- The standalone OpenSim contact parameter sweeps remain a heavyweight manual validation; a bounded local run reached the simulation but exceeded the normal documentation-gate runtime.
- The offline Sphinx build passes with warnings treated as errors.
- CI now tests Python 3.11, 3.12, and 3.13, makes MyPy blocking on Python 3.13, and requires the strict documentation job before package build.

## Definition of Done

- [x] Every `System.run(...)` result is retained; direct component histories are used only for standalone examples or internal-model diagnostics.
- [x] `describe()` and/or `result.events` is shown where meaningful.
- [x] Logging cells remain only where their output is discussed.
- [x] Notebook structure and Python syntax validate; representative executable batches pass.
- [x] Next-step links resolve and the strict Sphinx build has no warnings.
