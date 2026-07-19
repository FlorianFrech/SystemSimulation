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

Each batch: edit → execute top-to-bottom (`nbconvert --execute`) → docs build warning check → one commit.

1. **Batch 1 — Fundamentals** (3 notebooks): results-API migration pattern established here. ✅ Done (2026-07-19). Note: 01 and 02 are deliberately component-level; instead of a mechanical migration they each gained a "Running in a System" bridge section with `SimulationResult`. Unconnected inputs default to zero inside a `System` — no pre-seeding needed.
2. **Batch 2 — Intermediate** (01–03): includes `describe()`/SCC and `result.events` patterns. ✅ Done (2026-07-19). The algebraic-loop notebook keeps its (well-documented) logging section as the canonical logging reference; the hybrid notebook's logging was trimmed to `INFO` and cross-links to it. 01 gained an RMSE comparison table.
3. **Batch 3 — Advanced hybrid** (3): event-log-driven plotting.
4. **Batch 4 — Modelica + Master Pendulum** (4 + 2): FMU-based, same migration. Requires Windows FMUs present.
5. **Batch 5 — OpenSim + FEM** (3 + 3): light passes; needs `opensim`/`ngsolve` installed to re-execute.
6. **Batch 6 — Case study** (6): heaviest runtime; do last with the patterns settled.

## Definition of Done (per notebook)

- [ ] `result = system.run(...)`; no `system.get_history()` / ad-hoc `get_history_arrays()`
- [ ] `describe()` and/or `result.events` where meaningful
- [ ] At most one logging cell, only if its output is discussed
- [ ] Executes top-to-bottom without errors; outputs committed
- [ ] Next-step `{doc}` links valid; no new Sphinx warnings
