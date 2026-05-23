# Thesis Audit Log

Central log for the structured thesis audit. One row per finding. Triage by
severity, then resolve. See `audit_prompts.md` for the audit definitions and
`review_plan.md` §6 for the severity scale.

Severity: Blocking > High > Medium > Low > Ignore.
Status: Open / In progress / Done / Won't fix.

---

## CN — Contribution and Novelty Audit (source: Chapters 1, 7; thesis_concept.md, claims_and_evidence.md)

Run 2026-05-21 against the LaTeX source.

| ID | Severity | Page/Section | Category | Issue | Why it matters | Proposed fix | Status |
|---|---|---|---|---|---|---|---|
| CN-01 | Medium | §1.1–§1.3 | Contribution placement | The introduction body does not state what `syssimx` is until §1.3. The reader passes the motivation (§1.1) and a five-subsection State of the Art (§1.2, ~150 lines) before the framework and the contribution list appear. The abstract states the contribution, so this is local to Ch1. | A strict examiner wants the contribution previewed before a long related-work survey, so the survey reads as gap-building rather than as the chapter's main content. | Add a 2–3 sentence contribution preview at the end of §1.1 (name `syssimx` and its role), or move a short "Contributions" teaser ahead of §1.2. | Done (2026-05-21) |
| CN-02 | High | §1.3; abstract l.5; §7.1 | Novelty not consolidated | The central novelty — that no existing approach combines FMU + OpenSim + FEM integration with dependency-aware orchestration, algebraic-loop handling, hybrid events, and runtime switching — is asserted (§1.3 l.7, abstract l.5, §7.1) but never shown side by side. The Ch3 tables (Tab 3.1–3.4) compare *backend candidates per domain*, not competitor *frameworks* on the combined feature set. | This is the thesis's #1 risk ("thin wrapper around existing tools"). An unconsolidated combination-gap argument reads as asserted, not demonstrated. | Add one framework-level comparison table: rows = OMSimulator, INTO-CPS Maestro, CoFMPy, `syssimx`; columns = FMU / OpenSim / FEM backends, algebraic loops, hybrid events, runtime model switching. Place in §1.2/§1.3 or open §7.1. Forward-reference it from the gap paragraph. | Done (2026-05-21, tab:framework_comparison §1.3) |
| CN-03 | Medium | §1.3 (itemize) | Framework vs case-study contribution | The contribution `itemize` lists four framework mechanisms and the case study as five peer items, without naming the framework as the *primary* contribution and the case study as the *evaluation* vehicle. thesis_concept.md §3 requires this separation; Ch7 conclusions (l.21–22) does it, Ch1 does not. | Listing the case study as a co-equal contribution risks the "new pendulum model" misreading the concept doc warns against. | Add a lead sentence: "The main contribution is the design, implementation, and evaluation of `syssimx`." Then list the four mechanisms. State the case study separately as the evaluation system, not as a fifth contribution. | Done (2026-05-21) |
| CN-04 | Low | abstract l.8 | Orchestration emphasis | The framework sentence leads with "couples FMUs, OpenSim models, and FEM models through a shared component abstraction," foregrounding wrapping; the orchestration contribution appears only in the following sentence. | Reinforces the wrapper reading at the first place a reviewer looks. | Lead the sentence with the orchestration layer (structural analysis, hybrid events, switching) and mention the coupled backends second. | Done (2026-05-21) |
| CN-05 | Low | §7.1 l.80 | Literature-relative claim | "The reported end-to-end speedup of 1.62× is of the same order as the runtime gains reported for that approach [Choi]." A performance comparison to cited literature; verify the cited numbers actually support "same order." | Borderline novelty-positioning claim; weakly supported comparisons invite examiner pushback. Overlaps VE/LIT audits. | Confirm the Choi 2014/2017 reported gains during the VE/LIT pass; if the comparison is loose, soften to "within the range reported for region-based switching" or drop the numeric comparison. | Resolved (VE pass 2026-05-21): Choi = 1.21×–1.25× end-to-end, syssimx = 1.62× — same order of magnitude confirmed. Replace vague "same order" with concrete figures; drop-in in VE-04. |

### CN — checks that passed

- All seven main claims in thesis_concept.md §7 are made (RQ1–RQ5 map cleanly; benchmark and OpenModelica-verification claims present).
- No non-goal is violated: no "physical validation," "general-purpose replacement," "optimal performance," or "universal convergence" claims; no "first/novel" priority claim.
- Backend tools (OpenSim, NGSolve, CalculiX/FEBio/openCFS, OMSimulator/Maestro, CoFMPy, PyFMI) are distinguished as backends/candidates in Ch3, with orchestration explicitly kept inside `syssimx`.
- Ch7 §7.1 + conclusions cleanly separate the framework contribution from the case-study evaluation and bound the speedup claim.

---

## NC — Narrative Coherence and Chapter-Boundary Audit (source: all chapters; thesis_concept.md §5/§6, README.md §4)

Run 2026-05-21 against the LaTeX source.

| ID | Severity | Page/Section | Category | Issue | Why it matters | Proposed fix | Status |
|---|---|---|---|---|---|---|---|
| NC-01 | Medium | §6.3.3 (FEM pendulum) | Ch6 absorbs Ch5 role | The FEM-pendulum model description crosses into framework-mechanism detail that is Ch5 territory: snapshot/restore wiring for event localization (l.164), internal step-size reduction near contact (l.166–169), precomputed moment arm (l.182), and event-bracket reporting to the hybrid algorithm (l.199–201). | README §4 and writing_style §8 (Ch6) forbid re-explaining Ch5 mechanisms in Ch6; this is the "Ch6 becomes a second implementation chapter" risk. The model *physics* (geometry, material, pivot, contact penalty, projection) is correct Ch6 content — only the mechanism sentences leak. | Keep the model-physics facts; compress the four mechanism sentences to one and cross-reference Ch5 §5.3.3 (FEM component) and §5.8 (hybrid). | Won't fix — by design (re-eval 2026-05-21) |
| NC-02 | Low | §2.4.3 (FEM theory) | Possibly unused theory | The FEM theory includes peripheral results not strictly needed to follow the case study: Lax–Milgram existence/uniqueness (l.245) and the Rivlin–Ericksen invariant representation (l.205). | README §4: "Do not include unused theory in Chapter 2." Borderline — the rest of §2.4.3 (kinematics, PK stress, weak form, Newmark) is all used downstream. | Optional: reduce these two to a one-line mention with citation, or leave if examiner expects continuum-mechanics rigor. Not a clear violation. | Superseded by TH-01 (2026-05-21) |
| NC-03 | Low | thesis_concept.md §5 | Guideline/thesis mismatch | The documented narrative arc (§5, 6 steps: need → co-sim → architecture → impl → case study → discussion) skips the Requirements/Tool-Selection chapter (Ch3), which the thesis places appropriately between theory and architecture. | Not a thesis defect — the thesis flow is coherent. The *guideline* is out of date, which could mislead a future audit. | Update thesis_concept.md §5 to insert a "requirements and tool selection" step between theory and architecture. (Guideline edit, not a thesis edit.) | Done (2026-05-21) |
| NC-04 | Low | §5.7 (57_master_algorithms.tex l.153–157) | Duplicated paragraph | The sentence "The Gauss–Seidel trace stays close(r) to the analytical solution…" appears twice (l.153–154 then l.156–157) — an editing artifact. | Redundancy; reads as a copy-paste slip. Properly an ST/copy-edit item, surfaced during the flow read. | Delete the second copy (l.156–157), keep one clean version. | Open |

**NC-01 re-evaluation (2026-05-21).** Withdrawn after reading §5.3.3 and §5.3. The FEM wrapper is intentionally thin: §5.3.3 explicitly states the concrete component owns the port interface, discretization, time advancement, output projection, state transfer, and rollback, and forward-references the numerical formulation/verification to Ch6. The §6.3.3 mechanism sentences therefore describe the `FEMPendulum` (a Ch6 object), not a Ch5 mechanism; references to "the hybrid algorithm" are consumer-context, not re-explanation. Keep §6.3.3 as is. Optional polish only: a single cross-reference to §5.3.3/§5.8 at the FEM time-integration paragraph would make the Ch5↔Ch6 division explicit to the reader.

### NC — checks that passed

- Narrative scaffolding is strong: every chapter wrapper (Ch4–Ch7) opens by referencing the prior chapter and closes by pointing forward; transitions connect rather than read as disconnected reports.
- Claim discipline in transitions is correct: Ch3 wrapper states SRs are *verified* in Ch5 and mandatory URs *validated* in Ch6 (matches the V&V boundary).
- No Chapter 1 motivation repeated in later chapters (Ch6 §6.1 and Ch7 use brief callbacks, not re-motivation).
- Chapter 2 is well-bounded: a single pendulum example threads continuous → hybrid → co-sim → FMI → three modeling approaches; each theory block is used downstream; code/FMI names appear only for terminology orientation, not as implementation detail.
- Chapter 5 stays in implementation+verification (design rationale, requirement traces, analytical verification), not API documentation.
- No new results or implementation detail introduced in Chapter 7 (multi-fidelity taxonomy and outlook items are discussion/positioning, which is in-scope).
- Chapter 6 is substantial relative to Chapter 5 (closed-loop system, four model variants, reference models, three full scenarios with figures/tables, discussion). Final page balance should still be eyeballed in the compiled PDF (defer to PDF audit).

---

## VE — Validation and Evidence Audit (source: Ch5 verification sections, all of Ch6, Ch7 §7.1; claims_and_evidence.md, README.md §5, thesis_concept.md §8)

Run 2026-05-21 against the LaTeX source.

| ID | Severity | Page/Section | Category | Issue | Why it matters | Proposed fix | Status |
|---|---|---|---|---|---|---|---|
| VE-01 | Medium | §6.4 (reference model) | Reference reproducibility | The stated reference horizons are mutually inconsistent. §6.4 prose says the baseline reference stops at 2 s and the contact reference at 1 s (l.22–23), but the Solver-Configuration block says the exported reference trajectories use `stopTime=0.4` (l.48), and the contact/performance scenarios use `t_end=0.4 s` (§6.5.2 l.65, §6.5.3 l.159). | The reference description is the reproducibility contract; contradictory horizons make it impossible to tell which export a reader should regenerate. | Reconcile: state the actual exported horizon per reference and ensure it matches the scenario horizons. Confirmed by author + figures: baseline stopTime = 1 s, contact stopTime = 0.4 s (f_ref = 3 Hz, so 0.4 s spans the full contact phase). Fix §6.4 l.22–23 (2 s→1 s, 1 s→0.4 s) and remove the stray `stopTime=0.4` from l.48 so horizons are owned once. | Fix drafted (2026-05-21) |
| VE-02 | Low | §6.5 heading; §6.1; §6 wrapper l.8 | V/V/B umbrella wording | "Validation Scenarios" (§6.5) and "validation strategy" (§6.1, §6 wrapper) are used as an umbrella over three scenarios that are, respectively, numerical *verification* (baseline), *validation*+verification (contact), and a *benchmark* (performance). | The thesis maintains the verification/validation/benchmark distinction carefully at sentence level; an umbrella heading that says "validation" mildly dilutes it. Cross-ref TN audit. | Consider "Evaluation Scenarios" or "Case-Study Scenarios" for the §6.5 heading and "evaluation strategy" where the set spans all three evidence types. Keep "validation" for the contact-workflow scenario specifically. | Fix drafted (2026-05-21): §6.5 → "Evaluation Scenarios", §6.1 → "…Evaluation Strategy", §6 wrapper l.8 → "evaluation strategy" |
| VE-03 | Low | §6.5.1 l.45 | Claim precision | "This verifies numerical convergence … toward the monolithic OpenModelica reference" is stated from monotonic decrease of E∞/E2 over four step sizes, without a fitted convergence order. | Already hedged in §6.6 l.15 and §7.1, so defensible — but a strict examiner may distinguish "convergence behavior" from a proven order. | Optional: phrase as "confirms the expected convergence behavior" once, or add one sentence noting no order is estimated. Low priority. | Fix drafted (2026-05-21): §6.5.1 l.45 → "verifies the expected convergence behavior of…" |
| VE-04 | Low | §7.1 l.80 | Literature-relative claim (resolves CN-05) | "speedup of 1.62× is of the same order as the runtime gains reported for that approach [Choi]." Verified: Choi 2014/2017 report ~1.21×–1.25× end-to-end. Same order of magnitude holds, but "same order" is vague and understates the 1.62× result. | Vague comparisons invite examiner pushback; the thesis style prefers concrete figures (writing_style §5). | Replace with concrete figures (drop-in provided to user 2026-05-21): "…is comparable to the 1.21×–1.25× end-to-end speedups reported by Choi et al., and the benefit is similarly bounded by orchestration overhead and switching frequency." | Fix drafted (2026-05-21) |

### VE — checks that passed

- Each scenario has a clear, stated purpose (baseline = numerical verification; contact = workflow validation + numerical verification; performance = benchmark).
- V/V/B sentence-level wording is correct and disciplined: §6.5.2 "verifies numerical consistency … and validates the heterogeneous switched workflow … does not provide physical validation"; §6.5.3 "reports a benchmark of computational cost … does not establish correctness on its own."
- Benchmark results are never used as correctness evidence (§6.5.3, §6.6, §7.1).
- Numerical results are stated with concrete values and the tested scenario (Δt set, k_n, E, ν, ρ, horizons, 1.62×, 2.06×, E∞/E2 with units, 3.729·10⁻⁴ s event-time error, 8.33·10⁻¹⁷ rad switch jump).
- No single case-study result is generalized to all hybrid co-simulation (§6.6 l.15, l.57; §7.1 l.74).
- Limitations are explicit: state-projection deviation at the FMU→FEM switch (§6.6 l.39–44, §7.2) and contact-model mismatch (§6.5.2 l.62–63, §6.6 l.23–29, §7.2).
- All ten rows of claims_and_evidence.md §2 are supported and none exceeds its evidence level. Ch5 verification sections (52, 55, 58, 59) use analytical references with concrete errors (machine precision, 2.6·10⁻⁷ s, 3.3·10⁻¹⁶); the SCC-local algebraic-loop verification is cross-referenced to §5.6 (chain present; §5.6 not deep-read this pass).
- References are described for reproducibility (OpenModelica 1.26.3, DASSL/CVODE config, named models, scenario notebooks) — apart from the horizon inconsistency in VE-01.

---

## TH — Theory Scope Audit (Chapter 2) (source: §2.0–§2.4; ch2_theory.md, README.md §4, glossary.md, notation.md)

Run 2026-05-21 against the LaTeX source.

| ID | Severity | Page/Section | Category | Issue | Why it matters | Proposed fix | Status |
|---|---|---|---|---|---|---|---|
| TH-01 | Low | §2.4.3 (FEM theory) | Unused theory (supersedes NC-02) | Two FEM results have no downstream use: Lax–Milgram existence/uniqueness (l.245) is stated for the *linear* static case, but the case study uses a *nonlinear dynamic* SVK model; the Rivlin–Ericksen invariant representation (l.205) is background not applied later. The rest of §2.4.3 (kinematics, PK stress, weak form, semi-discretization, Newmark) is all used. | ch2_theory.md "Equation Rules": avoid derivations that do not support later implementation/case-study interpretation. | Optional: reduce both to a one-line mention with citation, or keep if the examiner expects continuum-mechanics rigor. Not a clear violation. | Open |
| TH-02 | Low | §2.4.2 (OpenSim Runtime Architecture) | Tool-runtime detail beyond prescribed bridge | The "Runtime Architecture" paragraph (Model/State/Manager; staged realization Position→Velocity→Dynamics→Acceleration) is OpenSim software-runtime detail. ch2_theory.md l.160/l.208–211 assigns "stages realization" and Model/State/Manager to the Ch5 wrapper; Ch2 should keep only the conceptual consequence (the "Interface Consequence" paragraph already does). | Keeps Ch2 a modeling-approach chapter, not a tool-integration chapter. Mild — the content is conceptual, not syssimx code. | Optional: trim to "OpenSim computes derived quantities in stages, and selected realized quantities become the simulation-unit outputs," and defer Model/State/Manager specifics to Ch5. | Fix drafted (2026-05-21): §2.4.2 "Runtime Architecture" block → 3-sentence "Staged computation" paragraph; Model/State/Manager deferred to §5.3.2. REQUIRED follow-up: §5.3.2 l.9 back-reference "As described in §2.4.2, an OpenSim model advances a State through a Manager" is stale after the drop — drop-in provided to introduce Model/State/Manager in §5.3.2 and reference §2.4.2 only for the multibody system. Verified §5.3.2 already covers the lifecycle roles (l.43,72–86,94). |
| TH-03 | Low | §2.1.2 (DAE index example) | Derivation depth (borderline) | The Cartesian-pendulum differentiation-index worked example carries the full hidden-constraint chain to index 3 (eq. dae_index2→dae_index0, explicit constraint force F). The differentiation-index *concept* is used (§2.4.1 index reduction), but the full chain is deeper than ch2_theory.md's "keep derivation depth below a numerical-methods thesis." | Defensible as pedagogy (grounds DAE vs ODE on the running pendulum) and likely fine for a CSE/TU Wien examiner. | Flag only if trimming for length: keep the index-3 result and drop one or two intermediate differentiation lines. No change needed otherwise. | Open |

### TH — checks that passed

- **Ordering follows ch2_theory.md** (§2.1 continuous → §2.2 hybrid → §2.3 co-simulation → §2.4 modeling approaches). This is *more* coherent than the generic order in the audit prompt: §2.3.6 (hybrid co-simulation) builds directly on §2.2 (hybrid-system theory, superdense time), so hybrid must precede co-simulation. FMI sits at the end of §2.3 (after the general simulation-unit/co-sim concepts), and OpenSim/FEM sit in §2.4 — all correct. Deferred to the guideline over the generic review_plan order by design.
- **Theory ↔ thesis-algorithm boundary is clear.** §2.3.4 (Jacobi/Gauss–Seidel) and §2.3.5 (algebraic loops) state the *principle* and explicitly defer the syssimx realization (SCC-local IJCSA, numerical Jacobian, convergence handling) to Ch5; §2.3.3 uses conceptual graph terms with no syssimx metadata field names. The interface-Newton equation is the general Sicklinger method, not a syssimx-specific algorithm.
- **No Chapter 1 motivation repeated** — §2.x openings are short callbacks to §1.2, not re-motivation.
- **No implementation/case-study leakage** beyond TH-02: no syssimx class/method/field names except the sanctioned `CoSimComponent` terminology bridge (the glossary "Canonical Thesis Sentence"); FMI-standard names (`modelDescription.xml`, `ModelStructure`, capability flags) are standard-level, not wrapper detail, and §2.3.7 defers the concrete wrapper to Ch5. No case-study parameter values (contact stiffness, gains, tolerances) appear in Ch2 — all deferred to Ch6.
- **Glossary + notation discipline holds:** subsystem / simulation unit / component used per the hierarchy; FMI introduced before FMU; symbols match notation.md. The Modelica listing in §2.4.1 is sanctioned by ch2_theory.md l.161.

---

## IC — Implementation Consistency Audit (Chapters 4 and 5) (source: §4.1–§4.2, §5.1–§5.9; ch4_architecture.md, ch5_implementation.md, glossary.md, notation.md)

Run 2026-05-21 against the LaTeX source. Class-name ground truth taken from `syssimx/core/multi_comp.py:161`.

| ID | Severity | Page/Section | Category | Issue | Why it matters | Proposed fix | Status |
|---|---|---|---|---|---|---|---|
| IC-01 | Medium | glossary.md l.79 | Class named differently | The glossary defines the multi-model abstraction as **`MultiComponentModel`**, but the actual class is **`MultiComponent`** (`syssimx/core/multi_comp.py:161`), and Ch4 §4.2.4, Ch5 §5.9, and Ch6 §6.3.4 all use `MultiComponent`. The glossary is the outlier. | The glossary is the authoritative terminology source; a wrong core-abstraction name there can propagate into future drafting. | Rename the glossary entry and its prose to `MultiComponent` (guideline edit). Also update the auto-memory note, which carries the same stale name. | Done (2026-05-21): glossary.md l.79 → `MultiComponent` (+ note `MasterPendulum` subclass); MEMORY.md updated |
| IC-02 | Medium | §5.6 (l.16–97) | Notation conflict / reserved symbol reused | §5.6 denotes the algebraic-loop SCC by `\(\mathcal{L}\)` and writes `\(U_{\mathcal{L}}\)`, `\(\widehat U_{\mathcal{L}}\)`, `\(\mathcal{R}_{\mathcal{L}}\)`. But Ch2 §2.3.5 and notation.md denote the loop unit set by `\(A \subseteq I\)` (with `\(U_A\)`, `\(Y_A(U_A)\)`, `\(\mathcal{R}(U_A)\)`), and notation.md reserves `\(\mathcal{L}\)` for the **global connection set** `\(\mathcal{L}\subseteq\mathcal{Y}\times\mathcal{U}\)` (§2.3.2). | Violates README §7 ("do not redefine global symbols locally") and breaks Ch2↔Ch5 consistency: a reader who learned `\(\mathcal{L}\)=connections` in Ch2 meets `\(\mathcal{L}\)=one SCC` in Ch5. | In §5.6 rename the loop set `\(\mathcal{L}\to A\)` throughout, with `\(U_A\)`, `\(\widehat U_A\)`, `\(\mathcal{R}_A\)` (or `\(\mathcal{R}(U_A)\)` to match notation.md §3.8), and the prose/listing `\(\mathcal{L}=\{\texttt{Inner}\}\)` → `\(A=\{\texttt{Inner}\}\)`. §5.5 (which uses prose "loop block"/member set) needs no change. | Fix drafted (2026-05-21): global `\mathcal{L}`→`A` in 56_algebraic_loops.tex |
| IC-03 | Low | §4.2.2 l.28 / §4.2.1 l.50 vs §5.4 l.54,71 / §5.8 l.16,78 | Term named differently | The event-receiving component is called an **"event receiver"** in Ch4 §4.2.2 (and "must receive an event" in §4.2.1), but a **"target component"** (§5.4 l.54) and an **"event listener" / "subscribed listeners"** (§5.4 l.71, §5.8) in Ch5. The glossary defines neither role term. | Cross-chapter term drift for one role; the thesis is otherwise strict on terminology. ch4_architecture.md itself chose "event receiver" for Ch4, conflicting with Ch5's "listener". | Pick one term (recommend "event listener", matching the `Event` subscription stored on the listener and the §5.4 component classification) and use it in Ch4 §4.2.1/§4.2.2; add a one-line glossary entry to lock it. Cross-ref TN. | Fix drafted (2026-05-21): glossary "Event source"/"Event listener" entries added (Done); Ch4 §4.2.2 + Ch5 §5.4 drop-ins to "event listener" |
| IC-04 | Low | §4.2.3 l.16 vs §5.4 l.71–73 | Architecture/impl tension | Ch4 §4.2.3 states "the user can change the execution strategy without changing the component implementations," but Ch5 §5.4 replaces the chosen algorithm with `HybridAlgorithm` "irrespective of whether the user has set a different algorithm explicitly" when event sources are present. | Not a hard contradiction (continuous algorithms remain interchangeable; Hybrid is forced for correctness), but a strict reader may read free user choice (Ch4) against the override (Ch5). | Add a half-sentence to Ch4 §4.2.3 noting that the system activates the hybrid algorithm automatically when a component can produce state events, while continuous strategies remain user-selectable. | Fix drafted (2026-05-21): §4.2.3 l.15–16 split into continuous-interchange + hybrid auto-activation sentences |

### IC — known carryover (already tracked, not re-counted here)

- Macro-step notation `\(H_k\)` (Ch2/notation.md) vs `\(\Delta t\)` (Ch4 §4.2.3 l.9; Ch5 §5.3.1, §5.7, §5.8) — the dual-usage note is already an open task in ch2_theory.md, ch4_architecture.md, and ch5_implementation.md. IC confirms it spans Ch4↔Ch5; resolve via the single dual-usage sentence rather than four renames.
- `IJCSA` not using `\ac{}` macro in Ch5 — already an open task in ch5_implementation.md (acronym pass; belongs to LIT/style).

### IC — checks that passed

- **Component abstraction / shared interface:** Ch4 §4.2.1 (typed ports, common lifecycle + inversion of control, structural+hybrid metadata, *physical state transfer* vs *rollback state transfer*, opt-in capabilities) maps cleanly to Ch5 §5.2 (template method + primitive/hook ops; `get_state`/`set_state` = physical, `snapshot_state`/`restore_state` = rollback; `evaluate_outputs`; `reset`). No contradiction.
- **Typed, unit-aware ports:** Ch4 §4.2.1 ↔ Ch5 §5.1 (`PortSpec`/`PortState`, `PortType` enum, Pint registry, `PortSpec.compatible()`, validation in `System._validate_connection()`). Consistent, including the "validate at connection time" claim.
- **Direct-feedthrough metadata:** Ch4 §4.2.1 (declaration consumed by `System` + connection structure) ↔ Ch5 §5.2 (`direct_feedthrough`), §5.5 (consumer), §5.3.1 (`ModelStructure`→`direct_feedthrough`, perturbation fallback), §5.3.2 (perturbation detector). Consistent.
- **Dependency graph & execution ordering:** Ch4 §4.2.2/§4.2.3 correctly defer derivation to Ch5 §5.5 (`build_graphs`, `_dag`, condensation, `execution_order`, delayed-producer). No architecture-level leakage of derived results.
- **SCC & algebraic-loop resolution (IJCSA):** Ch4 §4.2.3 (generic "algebraic-loop algorithms") ↔ Ch5 §5.5 (SCC detection), §5.6 (`solve_algebraic_scc_ijcsa`), §5.7 (`IJCSAAlgorithm`). Consistent apart from the IC-02 symbol.
- **Event indicators / rollback / bisection / superdense time:** Ch4 §4.2.1–§4.2.2 ↔ Ch5 §5.2, §5.4 (`EventConnection`, `Event`), §5.8 (`HybridAlgorithm`: trial step, `snapshot_state`/`restore_state`, bisection localization, `DenseTime`, commutativity). Superdense time `(t,ν)` ↔ `DenseTime` per notation.md. Consistent apart from the IC-03 role term.
- **Multi-model component & Master Pendulum:** Ch4 §4.2.4 (`MultiComponent`: registry, single active model, mode selector, hysteresis, state adapter, fixed external interface) ↔ Ch5 §5.9 (`models`, `active_mode`/`active_comp`, `mode_selector`, `hysteresis`, `_adapt_state`, `_unify_ports`, `sync_events`) ↔ Ch6 §6.3.4 (`MasterPendulum` subclass). Consistent apart from IC-01 glossary name. `MasterPendulum` is correctly Ch6-only (concrete subclass).
- **FMU / OpenSim / FEM wrappers:** Ch4 §4.1 backend asymmetry (FMU generic; OpenSim/NGSolve model-specific) ↔ Ch5 §5.3 (`FMUComponent` generic via model description; `OpenSimComponent`/`FEMComponent` model-specific). Consistent.

---

## LIT — Citation and Literature Audit (source: all chapters + thesis/other, references.bib; thesis_concept.md, claims_and_evidence.md)

Run 2026-05-21 against the LaTeX source. Cited-key set extracted from `\cite` across chapters/other; bib-key set from `references.bib` headers. No `\nocite{*}` is used anywhere.

| ID | Severity | Page/Section | Category | Issue | Why it matters | Proposed fix | Status |
|---|---|---|---|---|---|---|---|
| LIT-01 | Medium | §6.4 l.46–47, l.52–53 (also §6.3 l.58) | Missing citation | The solver-behavior statements "OpenModelica describes DASSL as …" and "OpenModelica describes CVODE as a SUNDIALS solver …" carry no citation. The audit explicitly requires CVODE/SUNDIALS to be cited where solver behavior is discussed. The ch6_case_study.md guideline intended `\cite{openmodelica_users_guide_2026}`, but that key is absent from the bib. | Tool-documentation claims stated as fact need a reference; "OpenModelica describes" is attribution without a citation. | Cite `open_source_modelica_consortium_openmodelica_2026` (an OpenModelica-documentation entry that is currently **uncited** in the bib) on the DASSL and CVODE/SUNDIALS sentences in §6.4. This both fixes LIT-01 and consumes one unused entry. | Open |
| LIT-02 | Low | references.bib | Unused references | ~33 bib entries are never cited. Because no `\nocite{*}` is used, biblatex excludes them from the printed bibliography, so this is source-file clutter, **not** a printed-thesis defect. Notable unused: `michalski_prepomax_2026` (PrePoMax — never discussed), `blochwitz_fmi_2012`, `gomes_semantics_2019`, `gomes_generation_2020`, `schweizer_implicit_2016`, `bonet_nonlinear_2008`, `fitzgerald_formal_2013`, `fitzgerald_multi-modelling_2019`, `vaandrager_overview_1999`, `gu_co-simulation_2001`, `al-hammouri_comprehensive_2012`, `karsai_model-integrated_2008`, `mosshammer_loose_2013`, `schmoll_co-simulation_2015`, `sajjadinia_multi-fidelity_2022`, `ascher_computer_1998`, `barton_modelling_1992`, `ModelicaSpecification2002`, `branicky_studies_1995`, `branicky_simulation_2006`, `xie_integrated_2024`, `leobner_energy_2011`, `braun_numerically_2022`, `gunther_beitrag_2017`, `oks_cyber-physical_2019`, `kalmar-nagy_can_2014`, `halloran_concurrent_2010`, `arnold_simulation_2004`, `putnik_what_2019`, `lee_introduction_2017`, `noauthor_modelicamechanics…`. | Harmless to the PDF but a strict submission audit (review_plan §H) flags "all references are used." | Either prune the genuinely irrelevant entries before submission, or cite the relevant ones (several co-sim/CPS surveys could strengthen §1.2/§2.3). No urgency — confirm `\nocite{*}` stays absent. | Open |
| LIT-03 | Low | references.bib `frech_syssimx_2026` | Missing (own-software) citation | The SysSimX software self-citation `frech_syssimx_2026` is defined but never cited. | A software/repository citation is expected for a framework thesis (availability statement). | Cite it where the framework or repository is introduced (e.g., a software-availability note in Ch1/Ch5 or the conclusion), or remove. Citing it also consumes an unused entry. | Open |

### LIT — checks that passed

- **FMI** cited where introduced: §1.1 l.26, §1.2 l.28/l.73, §2.3.7, §7.1 (`modelica_association_project_fmi_functional_2014/2024`).
- **OpenSim / Simbody** cited: §1.1, §1.2, §2.4.2 (`OpenSim_Delp`, `seth_opensim_2018`, `sherman_simbody_2011`), §3.2.
- **NGSolve / Netgen** cited at FEM tool selection §3.2 (`schoberl_c11_2014`, `schoberl_netgen_1997`); FEM theory refs in §2.4.3 (`knothe_finite_2017`, `braess_finite_2007`, `kruzik_mathematical_2019`, `kochmann_introduction_2025`, `newmark_method_1959`).
- **Co-simulation / algebraic-loop** papers cited in the right places: `gomes_co-simulation_2019`, `kubler_two_2000`, `sicklinger_interface_2014`, `hansen_verification_2021`, `petridis_test_2015`, `gomes_co-simulation_2018`, `andersson_methods_2016`, `schierz_co-simulation_2012`, `arnold_error_2013` (§2.3, §5.6, §7.1).
- **Multi-fidelity / switched-fidelity** cited near runtime switching across Ch1/Ch6/Ch7: `peherstorfer_survey_2018`, `fernandez-godino_review_2023`, `Choi2014`, `Choi2017`, `williams_switched-fidelity_2014`, `williams_variable_2014` (§1.2, §6.1, §7.1). `williams_variable_2014` key exists (bib l.602) — the §6.1 citation is valid.
- **PrePoMax / CalculiX:** CalculiX is discussed only as a *rejected* FEM alternative (§3.2, `dhondt_calculix_2023`), not as a used backend; PrePoMax is not used (its bib entry is unused — see LIT-02). Correct per the audit.
- **No missing citations:** every `\cite` key in the chapters resolves to an existing bib entry.
- **No citations in the abstract or Kurzfassung** (grep of thesis/other returns none) — matches writing_style §13.
- **No citation dumping:** the largest groupings are 2–3 topical references; no undifferentiated long lists.
- **Prior bib issues resolved:** `VirtualEngineeringSystems`, `gomes_co-simulation_2019-1`, the duplicate `FMI2.0`, and `friedrich_cofmpy_2025-1` are no longer cited or present — the earlier bibliography cleanup took effect.

---

## ST — Language and Style Audit (source: all chapters; writing_style.md, golden_rules_writing_summary.md)

Run 2026-05-21 against the LaTeX source. Best finalized on the compiled PDF (audit_prompts.md: "run late"); this pass covers prose only — visual issues (overflow, hyphenation, widows) belong to FIG/PDF.

| ID | Severity | Page/Section | Category | Issue | Suggested edit | Status |
|---|---|---|---|---|---|---|
| ST-01 | Low | §2.4.2 l.148 | Semicolon-joined sentence | "This model-specific interface selection is the main consequence for co-simulation; the concrete wrapper mapping is described in Section~\ref{sec:impl_opensim}." writing_style §2 splits semicolon sentences. | Split at the semicolon into two sentences. | Open (drop-in provided 2026-05-21) |
| ST-02 | Low | §2.3.1 l.26 & l.32 | Repeated statement | Both sentences assert "co-simulation enables tool-independent coupling but introduces a coupling error" (l.26 closes the co-sim definition; l.32 closes the three-approaches comparison). l.32 adds only the error source. | Keep l.26; rewrite l.32 to state only the new point: "The coupling error in co-simulation arises from the discrete data exchange at communication points." | Open (drop-in provided 2026-05-21) |
| ST-03 | Low | Ch5 (§5.2,§5.4,§5.5,§5.7,§5.8) | Long sentences + repeated definitions | Already enumerated in ch5_implementation.md "Current Open Tasks → Medium": long/comma-chained sentences (52 l.129, 54 l.31, 54 l.63–64, 55 l.144, 57 l.67, 57 l.86, 58 l.60–62, 58 l.144) and repeated definitions (54 l.78–85, 57 l.21–24, 58 l.20–26), plus caption polish (5.5/5.7/5.8/5.9). | Run the ch5 medium-priority style pass. No new long-sentence targets found outside Ch5 — the rest of the thesis is short-sentence style. | Open (tracked in ch5_implementation.md) |
| ST-04 | Low | §5.7 l.153–157 | Duplicated paragraph | Same item as NC-04 (the "Gauss–Seidel trace stays close(r)…" sentence appears twice). | Apply the NC-04 drop-in (delete the second copy). | = NC-04 (drop-in provided) |

### ST — checks that passed

- **Zero §18/§4 filler or inflated phrasing:** grep found no `facilitate`, `methodology`, `utilize`, `leverage`, "it can be observed", "it should be noted", "due to the fact", "in order to", "clearly shows", "seamless", or "cutting-edge". The prose already follows the writing-style anti-pattern list.
- **No vague pronoun-start references:** no "This/It is/provides/makes…" with a missing antecedent; the prose consistently writes "This <noun>" (e.g., "This metadata", "This projection", "This inversion of control").
- **No prose colon-lists:** the only colons introduce panel labels in figure captions ("(a) Dependency graph: …"), which is standard caption formatting.
- **Semicolons:** only one prose semicolon (ST-01); every other `;` is a table-cell separator in the §3.2 comparison tables (acceptable).
- **"enables" used concretely** (with an object, e.g., "enables tool-independent coupling"); the only issue is the §2.3 duplication (ST-02). No "the framework enables…" mantra repetition; the abstract's wrapping emphasis was already fixed (CN-04).
- **Tense consistent** in the sampled chapters: present for theory/implementation, past for reported results (writing_style §7).
- **German–English interference:** none observed in the chapters read. Best re-confirmed on a full proof-read of the compiled PDF (deferred to the PDF pass).

---

## TN - Terminology and Notation Audit (source: all chapters; glossary.md, notation.md)

Run 2026-05-21 against the LaTeX source. `glossary.md` and `notation.md` are binding for this pass.

| ID | Severity | Page/Section | Category | Issue | Why it matters | Proposed fix | Status |
|---|---|---|---|---|---|---|---|
| TN-01 | Medium | glossary.md; notation.md; Ch2 hybrid notation | Superdense-time notation | The glossary defines superdense time as `$(t,k)$`, but `notation.md` reserves `k` for the communication-point index and defines superdense time as `$(t,\nu)$`. The chapters and notation table use `$(t,\nu)$`. | The glossary and notation file contradict each other on a global symbol. This is high-risk because `k` is already used throughout the co-simulation notation for communication points. | Update `glossary.md` to define superdense time as `$(t,\nu)$` and state that `\nu` is the superdense microstep index. Keep the chapter notation unchanged. | Done (2026-05-21) |
| TN-02 | High | Ch4-Ch6; notation.md | Macro-step notation | `notation.md` defines the macro step size as `H_k = T_{k+1}-T_k` and the generic requested step duration as `H`. Chapters 4-6 often use scalar `\Delta t` for the macro communication step, for example Ch4 `423_algorithms.tex` l.9, Ch5 `531_fmu_component.tex` l.82, Ch5 `57_master_algorithms.tex` l.23/l.147, Ch5 `58_hybrid.tex` l.53/l.238, and Ch6 `65_validation_scenarios.tex` l.24/l.65. The thesis notation table adds a local exception for `\Delta t`, but `notation.md` does not. | This is the main notation drift in the thesis. The binding notation reserves `\Delta t_{i,r}` for internal local step sizes, so using `\Delta t` for macro steps can blur macro communication steps and local integration steps. | Decide one convention. Either update `notation.md` explicitly to permit scalar `\Delta t` as a chapter 5-6 macro-step abbreviation, or replace macro-step prose with `H`/`H_k` and keep `dt` only for code/API names. | Done (2026-05-21; notation.md permits scalar `\Delta t` in Chapters 5--6) |
| TN-03 | Medium | Ch2 `24_modeling_approaches.tex` l.303/l.315 | Local FEM time-step notation | The Newmark update uses `\Delta t` for the finite-element time increment. Elsewhere in Ch4-Ch6 `\Delta t` is used for the macro communication step. | This creates a local-step/macro-step ambiguity exactly in the area where the glossary distinguishes communication step and local integration step. | Define a local FEM step symbol, for example `\Delta t_{\mathrm{FE}}`, or align the derivation with `\Delta t_{i,r}` from `notation.md`. | Fix drafted (2026-05-21; use `\Delta t_{i,r}` in the Newmark paragraph) |
| TN-04 | Medium | Ch5 `58_hybrid.tex` l.237 | Event-time notation | The hybrid verification scenario uses roots `T_1` and `T_2` for event times. `notation.md` uses `T_k` for communication points and `t_e` for event times. | Reusing capital `T` for event roots weakens the distinction between communication points and localized event times. | Rename the roots to `t_{e,1}` and `t_{e,2}` or define them explicitly as event times. | Fix drafted (2026-05-21) |
| TN-05 | Medium | Ch6 `64_reference_model.tex` l.93 | Error-metric interval notation | The integrated error metric uses `\Delta t_j` as a comparison-grid interval. `notation.md` reserves `\Delta t_{i,r}` for internal subsystem solver steps. | The symbol is close enough to the reserved local-step notation to cause confusion, especially in a chapter that also reports macro communication-step refinements. | Define a separate quadrature weight, for example `w_j = t_{j+1}-t_j`, and write `\sum_j e_{\theta,j}^2 w_j`. | Fix drafted (2026-05-21) |
| TN-06 | Medium | Ch5 `57_master_algorithms.tex` l.128/l.136 | Reserved symbol reused | The algorithm-verification example defines the scalar ODE `\dot{y}=k r-y` and sets `k=2`. `notation.md` reserves `k` for the communication-point index. | This is a direct local redefinition of a global reserved symbol. | Rename the gain to `K`, `K_{\mathrm{g}}`, or another non-reserved symbol. | Done (2026-05-21; gain renamed to `K`) |
| TN-07 | Low | Ch2 notation table | Notation-table completeness | `notation.md` defines `j \rightarrow i` as a dependency edge and `A \subseteq I` as the set of simulation units in one algebraic loop. The thesis notation table includes `G=(V,E)` but omits both symbols, while Ch2/Ch5 use the algebraic-loop set `A`. | The prompt requires that the thesis notation table matches `notation.md`. The missing rows are small but easy to fix. | Add rows for `j \rightarrow i` and `A \subseteq I` to `20_notation_and_conventions.tex`. | Done (2026-05-21) |
| TN-08 | Medium | Ch5 `54_system.tex` l.134; Ch5 `58_hybrid.tex` l.45 | Event-listener terminology | The glossary requires `event listener` for the component that receives a routed event. Ch5 still contains `target component` in the system verification table and `event-target map` in the hybrid section. | The glossary explicitly says not to use event receiver or event target for the component role. This is also related to IC-03. | Replace `target component` with `event listener`. Replace `event-target map` with `source-to-listener map` or `event-listener map`. If the code field `_event_targets_by_source` is mentioned, introduce it after the glossary term. | Done (2026-05-21) |
| TN-09 | Medium | Ch4-Ch5 implementation prose | `System` vs `system` | Several implementation passages refer to the syssimx software object as lowercase `system`, for example Ch5 `54_system.tex` l.71/l.78/l.100-l.102/l.140-l.150 and Ch5 `58_hybrid.tex` l.16. The glossary reserves lowercase `system` for physical or mathematical systems and recommends `\texttt{System}` for the syssimx class/object. | The distinction is important because the thesis also discusses physical systems, system models, and the `System` class. | Use `\texttt{System}` instance/class/object when the software abstraction is meant. Keep lowercase `system` for physical or mathematical systems. | Done (2026-05-21) |
| TN-10 | Low | Ch5 `59_multi_component.tex` l.2/l.83/l.171; Ch5 `58_hybrid.tex` l.280 | Runtime model switching term | The canonical thesis term is `runtime model switching`. Ch5 section titles and captions still use `mode switching`, and one transition says `component-level mode switching`. | `mode` is valid as an implementation concept (`active_mode`, `mode_selector`), but prose should use the glossary-level mechanism name. | Use `runtime model switching` in prose headings and captions. Keep `mode` only for implementation identifiers and local mode keys. | Done (2026-05-21) |
| TN-11 | Low | Ch5 `533_fem_component.tex` l.5; Ch3 `312_heterogeneous.tex` l.49 | Simulation unit vs component | The glossary defines `simulation unit` as tool-neutral and `component` as the concrete syssimx implementation. The text says the `FEMComponent` class provides an entry point for `spatially discretized simulation units`, and SR-07-01 uses the same wording. | This slightly mixes the hierarchy: a syssimx class should normally provide an entry point for components or for subsystem models implemented as components. | Prefer `finite-element components` or `finite-element subsystem models implemented as syssimx components`. For the requirement row, decide whether the user-facing level should stay tool-neutral or whether the system requirement should use `component`. | Done (2026-05-21) |
| TN-12 | Medium | glossary.md; Ch6 evaluation wording | Verification / validation / benchmark definitions | The prompt requires verification, validation, and benchmark to be enforced per glossary definitions, but `glossary.md` currently has no entries for these terms. Ch6 defines the distinction locally and mostly uses it consistently, but `61_objective_validation_strategy.tex` l.11 still says `compact validation object` as an umbrella for verification, validation, and benchmark scenarios. | Without glossary entries, the requested rule cannot be enforced as binding terminology. The remaining umbrella use of validation weakens the distinction. | Add glossary entries for verification, validation, and benchmark based on Ch6 Section 6.1. Replace `compact validation object` with `compact evaluation object`. Cross-ref VE-02. | Done (2026-05-21) |

### TN - checks that passed

- The deliberate hierarchy `subsystem` -> `simulation unit` -> `component` is mostly stable. The only relevant drift is TN-11.
- `direct feedthrough`, `algebraic loop`, `master algorithm`, `communication step`, and `local integration step` are spelled and used consistently apart from the macro-step symbol drift in TN-02/TN-03.
- The earlier algebraic-loop notation conflict where `\mathcal{L}` denoted a loop set in Ch5 appears fixed. Ch5 now uses `A`, `U_A`, and `\mathcal{R}_A`, consistent with `notation.md`.
- Event-time notation is generally consistent with `t_e`; TN-04 is a local naming exception in one verification scenario.
- The case-study distinction between numerical verification, workflow validation, and performance benchmark is mostly clear at prose level. The missing glossary entries and the Ch6 umbrella phrase remain tracked in TN-12.

---

## Programme Summary (2026-05-21)

All eight source-runnable audits are complete: **CN, NC, VE, TH, IC, LIT, ST, TN**. The PDF-dependent audits (**FIG** visual half, **PDF** integrity) still require a compiled PDF and are not yet run.

### Counts by audit

| Audit | Findings | High | Medium | Low | Closed (Done / Resolved / Won't fix) | Outstanding |
|---|---|---|---|---|---|---|
| CN | 5 | 1 | 2 | 2 | 5 | 0 |
| NC | 4 | 0 | 1 | 3 | 3 | 1 (NC-04) |
| VE | 4 | 0 | 1 | 3 | 0 | 4 (all drafted) |
| TH | 3 | 0 | 0 | 3 | 0 | 3 (TH-02 drafted; TH-01/03 optional) |
| IC | 4 | 0 | 2 | 2 | 1 | 3 (drafted) |
| LIT | 3 | 0 | 1 | 2 | 0 | 3 (LIT-01 Medium, Open) |
| ST | 4 | 0 | 0 | 4 | 0 | 4 (drop-ins / tracked) |
| TN | 12 | 1 | 8 | 3 | 9 | 3 (TN-03/04/05 drafted) |
| **Total** | **39** | **2** | **15** | **22** | **18** | **21** |

### Severity headline

- **High (2): both closed.** CN-02 (novelty table) — Done. TN-02 (macro-step `\Delta t` vs `H_k`) — Done (notation.md now permits scalar `\Delta t` in Ch5–6).
- **Medium (15): 9 closed, 5 drafted, 1 open.** Only **LIT-01** (cite the OpenModelica docs for the §6.4 DASSL/CVODE descriptions) is still Open with no drop-in drafted.
- **No design, evidence, or boundary inconsistencies** were found in any audit. Findings were notation/naming/citation/wording hygiene.

### Outstanding thesis-`.tex` drop-ins to paste (all provided in chat)

- NC-04 / ST-04 — §5.7 l.153–157 delete duplicated paragraph.
- VE-01 — §6.4 l.22–23 horizons (1 s / 0.4 s) + remove stray `stopTime=0.4` (l.48).
- VE-02 — §6.5 / §6.1 / §6 wrapper headings → "Evaluation".
- VE-03 — §6.5.1 l.45 → "verifies the expected convergence behavior…".
- VE-04 — §7.1 l.80 → concrete Choi 1.21×–1.25× figures.
- TH-02 — §2.4.2 "Staged computation" trim **+ §5.3.2 l.9 follow-up** (introduce Model/State/Manager there).
- IC-02 — §5.6 global `\mathcal{L}`→`A`.
- IC-03 — Ch4 §4.2.2 + Ch5 §5.4 → "event listener" (glossary already Done).
- IC-04 — §4.2.3 l.15–16 split (continuous-interchange + hybrid auto-activation).
- ST-01 — §2.4.2 l.148 semicolon split.
- ST-02 — §2.3.1 l.32 rewrite (remove repeated tradeoff).
- TN-03 — §2.4 Newmark `\Delta t` → `\Delta t_{i,r}`.
- TN-04 — §5.8 l.237 `T_1`/`T_2` → `t_{e,1}`/`t_{e,2}`.
- TN-05 — §6.4 l.93 `\Delta t_j` → quadrature weight `w_j`.

### Open (no drop-in yet)

- **LIT-01 (Medium):** add `\cite{open_source_modelica_consortium_openmodelica_2026}` to the §6.4 solver-description sentences — drop-in not yet drafted.
- **TH-01, TH-03 (Low, optional):** trim peripheral FEM theory / DAE index depth in Ch2.
- **LIT-02, LIT-03 (Low, optional):** prune ~33 unused bib entries; cite or remove `frech_syssimx_2026`.

### Guideline/memory edits already applied (not awaiting paste)

- NC-03 (thesis_concept.md §5), IC-01 (glossary.md `MultiComponent` + MEMORY.md), IC-03 glossary entries, and the TN guideline/glossary/notation fixes (TN-01/02/06/07/08/09/10/11/12).

### Remaining (needs compiled PDF — Phase 3)

- **FIG** (figure/caption/visual: referenced-before-appearance, units/legends, short captions, overflow/blur) and **PDF** (TOC, LoF/LoT, `??`/`[?]`, overfull boxes, acronym first-use, hyperlinks). Run after applying the drop-ins and compiling twice.

---

## FIG — Figure, Table and Caption Audit (source: compiled main.pdf; writing_style.md, README.md §8, glossary.md)

Run 2026-05-21 against the compiled PDF.

| ID | Severity | Item | Issue | Proposed fix | Status |
|---|---|---|---|---|---|
| FIG-01 | Medium | Fig 6.6(c) (p111) | The bar-chart annotation reads **"speedup = 1.61×"**, but the text reports **1.62×** everywhere else (abstract, Kurzfassung "1,62", §6.5.3, §6.6, Tab 6.5, §7.1, §7.3). From the reported medians 467.6/289.6 = 1.6147 ≈ **1.61**, so the figure is arithmetically right and the prose is the outlier. | Recompute the ratio from the raw medians and make figure + all prose/table occurrences agree (one value). If 1.61 is correct, update ~8 locations incl. abstract and Kurzfassung. | Open |
| FIG-02 | Medium | Fig 5.9 (p79) | The figure graphic still labels the loop block **"SCC 𝓛"**, but the caption and §5.6 prose were updated to **"A = {Inner}"** (IC-02 rename). The vector graphic was not regenerated. | Regenerate Fig 5.9 with the rectangle labelled "SCC A" (or "A = {Inner}"). | Open |
| FIG-03 | Low | Fig 6.1 (p97) | The full-page landscape signal-flow diagram is very dense; some block-internal equations/labels may be small at print size. | Verify legibility on printed/100% PDF; enlarge sub-labels if needed. Not a content defect. | Open |

### FIG — checks that passed

- Every figure and table is referenced in the text before or near its appearance.
- Short-form captions present throughout; LoF/LoT/LoL entries are clean noun phrases (no math/`\texttt` in the short forms, e.g. Tab 1.1 → "Co-simulation framework capability comparison.").
- Fig 4.1 distinguishes framework layers from external tools (the "External Simulation Tools … not part of the framework" band is visually separated).
- Plots carry units, legends, and readable axis labels (rad, s, m, MPa, N·m⁻¹); reported values trace to §6 tables.
- Diagram labels match the glossary/prose: `MasterPendulum`, "event listener", "direct feedthrough", `CoSimComponent`, `MultiComponent`, Model/State/Manager.
- The A/B/C/D scenario stays consistent across the Ch2 conceptual (Fig 2.5), Ch4 architecture (Fig 4.3), and Ch5 implementation (Fig 5.8) figures, refining rather than repeating.
- No table is in method-list style; the requirement (3.1–3.4), comparison (1.1, 3.5–3.9), and mapping (5.5, 5.7) tables are appropriate.

---

## PDF — Final PDF Integrity / Submission Audit (source: compiled main.pdf only)

Run 2026-05-21 against the compiled PDF.

| ID | Severity | Location | Issue | Proposed fix | Status |
|---|---|---|---|---|---|
| PDF-01 | Medium | Abstract (p. III) | The abstract no longer names the framework before "The framework provides an orchestration layer…". The naming sentence ("This thesis develops … SysSimX, a Python framework for heterogeneous hybrid co-simulation with runtime model switching.") was dropped during the CN-04 reorder, so "The framework" is dangling and `SysSimX` is first named only in the final paragraph. The Kurzfassung still has the naming sentence, so the two diverge. | Restore the naming sentence as the first sentence of abstract paragraph 2, then keep orchestration-first (drop-in below). | Open |
| PDF-02 | Medium | Headline speedup | Same as FIG-01 — the 1.61× / 1.62× mismatch spans the abstract, Kurzfassung, §6.5.3, §6.6, Tab 6.5, §7.1, §7.3, and Fig 6.6. | Reconcile to one value across all front-matter, Ch6, Ch7, and the figure. | Open (= FIG-01) |
| PDF-03 | Low | §3 / Ch3 intro (p. 37) | Two sentences begin with lowercase: "user requirements (URs) state…" and "system requirements (SRs) state…" (acronym first-use `\ac{UR}`/`\ac{SR}` at sentence start). | Use `\Ac{UR}`/`\Ac{SR}` or reword so the sentence starts with a capital. | Open |
| PDF-04 | Low | §7.1 RQ1 (p. 114) | "FMUs, OpenSim models, FEMs models, and multi-model components" — `\acp{FEM} models` renders the awkward "FEMs models". | Use "FEM models" (drop the plural acronym before "models"). | Open |
| PDF-05 | Low | Ch2 intro (p. 10) | "Section 2 establishes the notation…" refers to the *unnumbered* Notation section as "Section 2", which is ambiguous (Section 2 = the whole chapter). | Reword to "The notation section establishes…" or give the section a number. | Open |
| PDF-06 | Low | Bibliography [34] (p. 128) | Ref [34] (Omola licentiate thesis) renders **without an author**; also "Omola :" has a stray space before the colon. | Add the author to `andersson_omola_1990` and fix the title spacing. | Done (2026-05-22) |
| PDF-07 | Medium | Front matter | No affidavit / declaration of authorship (Eidesstattliche Erklärung) is present. TU Wien theses normally require one. | Verify the faculty requirement; add the signed declaration page if required before submission. | Open |
| PDF-08 | Low | §2.4.3 (pp. 32–34) | Many display equations (≈2.42–2.56) are numbered but never referenced by number; ch2_theory.md says "label equations only if referenced later". | Optional: `\notag` the unreferenced ones, or accept as thesis convention. | Open |

### PDF — checks that passed

- TOC entries and page numbers are consistent with the body; LoF (p. 121), LoT (p. 123), LoL (p. 125), Bibliography (p. 126) all match.
- LoF/LoT/LoL are complete and use the short caption forms.
- No unresolved cross-references (`??`) and no missing citations (`[?]`) anywhere in the body.
- No citations in the Abstract or Kurzfassung.
- Acronyms are expanded on first use (CPS, CAD, FMI, FMU, FEM, API, PID, CVODE, SUNDIALS, BDF, DASSL, SCC, IJCSA, DAG); the acronym list shows only used acronyms.
- Bibliography formatting is otherwise consistent (IEEE style); Kurzfassung uses German decimal commas (467,6 s; 1,62).
- VE-01 reference horizons now consistent (baseline 1 s, contact 0.4 s; no stray `stopTime=0.4`).

### Optional (not a defect)

- Thesis title "Development of a Framework for System Simulation" is generic; a more specific title (e.g., naming heterogeneous hybrid co-simulation) would be more informative — but the registered title is usually fixed.
