# Defense Presentation — SysSimX

Master's thesis defense slides. Built on the TU Wien Beamer theme (`Wien`).

- **Talk length:** 20 min + Q&A
- **Master file:** `slides.tex` (preamble + `\input{chapters/...}` only)
- **Sections:** one file per chapter under `chapters/`, mirroring the thesis structure
- **Figures:** reused from `../figures/` via `\graphicspath` — do not copy

## Build

```powershell
latexmk -pdf -output-directory=build slides.tex
```

The Lorentz-force template artefacts (`build/`, old `img/*.png` from the Lorentz
project) can stay or be cleaned up — they are not referenced by the new slides.

## Time budget

| # | Block                        | Min | Slides | File                              |
|---|------------------------------|----:|-------:|-----------------------------------|
|   | Title + outline              |   1 |      2 | `slides.tex`                      |
| 1 | Introduction                 |   3 |      4 | `chapters/01_introduction.tex`    |
| 2 | Background *(optional)*      |   0 |    0–1 | `chapters/02_background.tex`      |
| 3 | Requirements                 |   1 |      1 | `chapters/03_requirements.tex`    |
| 4 | Architecture                 | 3.5 |      3 | `chapters/04_architecture.tex`    |
| 5 | Implementation               | 1.5 |      2 | `chapters/05_implementation.tex`  |
| 6 | Case study *(centerpiece)*   |   8 |      5 | `chapters/06_case_study.tex`      |
| 7 | Discussion & Conclusion      |   2 |      2 | `chapters/07_conclusion.tex`      |
|   | Thank you                    |  <1 |      1 | `slides.tex`                      |
|   | **Total**                    |  20 |    ~19 |                                   |

Backup slides in `chapters/99_backup.tex` (numbered separately via
`appendixnumberbeamer`) — only shown if asked.

## Per-slide intent

Each slide should communicate **one** thing. Notes below are the *single point*
the slide must land — refine wording during drafting, but do not let a slide
drift past one main message.

### Title + outline
- **S0 Title** — title, author, supervisor, date.
- **S1 Outline** — one line per section; no sub-bullets.

### 1. Introduction (3 min, 4 slides ≈ 45 s each)
- **S2 Heterogeneous simulation need** - active prostheses and exoskeletons
  form one coupled dynamic system with the human body. Biomechanics,
  structural mechanics, and control/electronics are naturally modeled in
  different domain tools. One figure should carry both the physical coupling
  and the tool fragmentation.
- **S3 Orchestration is nontrivial** - coupled simulation units may have
  direct-feedthrough dependencies, algebraic loops, and hybrid events. The
  slide motivates why structural analysis, loop handling, and event handling
  are needed before introducing implementation details.
- **S4 Multi-fidelity and runtime switching** - one subsystem may need
  different model fidelities in different phases. Runtime switching with state
  transfer is introduced as a generic concept (M_L / M_H, no tool names).
- **S5 Research gap and contribution** - capability comparison table (4 rows
  × 6 columns) showing that no evaluated FMI-based framework combines all six
  capabilities introduced in S2–S4; SysSimX row tick-marks all and is named
  in one contribution block beneath. RQ chip strip (RQ1–RQ5 keywords) at the
  bottom. Full RQ wording spoken-only or in backup B-RQs.

### 3. Requirements (1 min)
- **S6 Requirements** — 4 categories (general modeling, heterogeneous
  integration, simulation, interaction) shown as a compact 2×2 table; one row
  beneath shows the traceability (SR → implementation features, UR →
  case-study validation). No derivation methodology on the slide — only what
  was required and how it traces. Backups B1–B4 cover full UR/SR lists,
  traceability matrix, and tool comparison.
  (Skip ch2 unless rehearsal proves it is needed.)

### 4. Architecture (3.5 min)
- **S7 Overview** — the SysSimX block diagram. One sentence per layer.
- **S8 Core abstractions** — Component / Port / System; unit-aware coupling.
- **S9 Algorithms** — when to use Gauss-Seidel, Jacobi, Hybrid, IJCSA.

### 5. Implementation (1.5 min)
- **S10 Wrappers + units** — three tool wrappers behind one Component
  interface; Pint at the port boundary.
- **S11 Loops + switching** — algebraic-loop detection (SCC) and runtime
  MultiComponent switching used in the case study.

### 6. Case study (8 min — centerpiece)
- **S12 System** — full control loop, one diagram.
- **S13 Three backends** — fidelity/cost trade-off in one row of figures.
- **S14 Validation** — reference model + scenarios; what is being measured.
- **S15 Results** — the single most convincing plot + headline number.
- **S16 Multi-model switching** — runtime model swap demo.

### 7. Discussion (2 min)
- **S17 Answers + limitations** — one bullet per RQ; honest single-bullet limit.
- **S18 Outlook** — 2–3 concrete next steps.

### Close
- **S19 Thanks** — supervisors, collaborators, institute.

## Introduction Storyboard

The introduction should be a motivation funnel, not a technical feature list.
Use mostly figures and make each slide answer one "why" question:

1. "Why heterogeneous co-simulation?" Active biomechatronic systems are one
   coupled physical system, but their subsystems are modeled in different
   domain tools.
2. "Why is orchestration difficult?" Coupled simulation units need a valid
   execution order, algebraic-loop handling, and hybrid event handling.
3. "Why runtime switching?" One fidelity is not useful everywhere; expensive
   high-fidelity models should be used where their detail matters.
4. "Why SysSimX?" Evaluated frameworks cover parts of the workflow, but not the
   full combination targeted here.

### S2 Heterogeneous simulation need - coupling and tool fragmentation

- **Show:** one schematic of an exoskeleton on a walking human silhouette with
  three labeled subsystem boxes: Human Biomechanics, Structural Mechanics, and
  Control/Electronics. Add tool badges or small labels for OpenSim, FEM/NGSolve,
  and Modelica/FMU. Leader lines anchor each box to its physical part, and
  arrows between the boxes show physical coupling.
- **Tell:** active devices and the human body form one coupled dynamic system.
  Performance, loads, stability, and safety depend on interactions between
  subsystems. These subsystems are not naturally modeled in one tool because
  each domain uses different abstractions and numerical methods.
- **Landing sentence:** "The central need is system-level coordination of
  specialized subsystem models."
- **Avoid:** long CPS definitions, device catalogues, FMI details, master
  algorithms, and execution-order mechanics.

### S3 Orchestration is nontrivial - dependencies, loops, and events

- **Show:** one dependency graphic with three black-box simulation units —
  each with a small internal solver icon and visible input/output ports —
  connected to form (a) a directed chain with at least one instantaneous edge,
  (b) a cycle of two units (the algebraic loop), and (c) one edge marked with
  an event symbol. Color the units that have direct feedthrough; solid edges
  for instantaneous dependencies, dashed for delayed. Three labeled callouts
  underneath: ① execution order, ② algebraic loop, ③ hybrid event.
- **Tell:** simulation units are black boxes with their own solver — only
  their ports are visible. Coupling them creates a system where outputs feed
  inputs at communication points. Three orchestration problems follow:
  execution order when outputs depend instantaneously on inputs; algebraic
  loops when those dependencies cycle; hybrid events when continuous signals
  jump mid-step.
- **Progressive reveal:** units → connections → callout ① → callout ② →
  callout ③ → landing line. Six clicks, ~10 s each.
- **Landing sentence:** "FMI standardizes the unit interface — but none of
  these is solved by FMI alone."
- **Avoid:** master-algorithm naming, DAE notation, zero-crossing terminology,
  per-port labels (u1, y1, ...) — port markers only. Show direct feedthrough
  via unit color and edge style, not by drawing internal u→y arrows. Use
  *simulation unit*, never *subsystem*, for the ported boxes. No communication-
  pattern time diagram on this slide — that belongs in backup (B-CommGrid).

### S4 Multi-fidelity and runtime model switching - concept and need

- **Title:** "Multi-Fidelity and Runtime Switching".
- **Show:** a two-row figure split by a horizontal divider, with row labels
  *Definition* and *Execution* on the left margin:
  - **Definition (top):** a "Subsystem" container wrapping two generic models
    M_L (low-fidelity, low cost, global behavior) and M_H (high-fidelity, high
    cost, local behavior), with bidirectional state-transfer arrows between
    them and a "State transfer" label in the middle.
  - **Execution (bottom):** a horizontal time axis showing the active model
    per phase as a colored bar (M_L → M_H → M_L sandwich), with dashed
    vertical lines at the two switch points and a "high-fidelity interest
    region" bracket beneath the M_H phase.
  Color-match M_L / M_H boxes to their timeline phases (carries the link
  between rows). A small legend ties the dashed switch markers to the
  state-transfer arrows. No tool names, no specific subsystem
  (pendulum/exoskeleton), no MultiComponent internals.
- **Tell:** different simulation phases need different fidelity. The detailed
  model is only required in a region of interest (e.g., contact, local
  deformation). Runtime switching uses the cheap model elsewhere and the
  detailed one only when needed --- reducing cost without losing resolution
  where it matters. Switching requires a stable shared interface and
  consistent state transfer.
- **Landing sentence:** "Multi-fidelity simulation must work at runtime --- not
  only at design time. The framework provides a multi-model component with a
  shared interface and state transfer, used in the case study to swap pendulum
  representations on the fly."
- **Avoid:** any tool names (OpenSim, FEM, Modelica/FMU); the pendulum or
  exoskeleton as the concrete subsystem (case study territory); three
  alternative lenses (the case-study layout); the MultiComponent block
  diagram (architecture territory). Use M_L / M_H or M_1 / M_2 --- generic
  labels only.

### S5 Research gap and contribution - capability table + SysSimX claim

- **Title:** "Research Gap and Contribution".
- **Show:** the chapter-1.3 capability comparison table, four rows × six
  columns. Rows: OMSimulator, INTO-CPS Maestro, CoFMPy, **SysSimX** (bold,
  separated by an extra `\midrule`). Columns map directly to the capabilities
  introduced in S2–S4: *FMU · MBD · FEM · Loops · Hybrid · Switching*. A
  one-line legend beneath the table explains `\checkmark` native / `(\checkmark)`
  partial / `---` none. Below the legend, a Beamer block titled
  *"Contribution"* names SysSimX in one sentence. At the bottom, a `\scriptsize`
  RQ chip strip: `RQ1 interface · RQ2 dependencies · RQ3 events ·
  RQ4 switching · RQ5 evaluation`.
- **Tell:** the columns of the table are the capabilities just introduced —
  heterogeneous tools (S2), orchestration challenges (S3), runtime switching
  (S4). Each existing framework is missing two or more. SysSimX combines all
  six in one Python-native framework, evaluated on the controlled-pendulum
  case study.
- **Progressive reveal:** table visible → contribution block (`<2->`) →
  RQ chip strip (`<3->`). Three clicks, ~15 s each.
- **Landing sentence:** "The next sections describe its architecture,
  implementation, and case-study evaluation."
- **Avoid:** full RQ sentences on the slide (chips only); citations in row
  labels (defense slide, not paper); a separate contribution slide (one slide
  carries gap + claim together). The `(\checkmark)` notation requires the
  legend — never omit it.

### Division of labor across slides (no overlap)

Multi-fidelity content is split across three slides at three abstraction levels:

| Slide | Level | What it shows | What it avoids |
|---|---|---|---|
| **S4 (Intro)** | Concept | Generic M_L / M_H, timeline, region of interest, switch points | Tool names, pendulum, architecture |
| **Architecture (S7 or S8)** | Mechanism | MultiComponent block: shared interface, switch criterion, state translator, hysteresis | Concrete models, results |
| **Case study (S12, S15)** | Realization | Three pendulum backends (FMU rigid / OpenSim musculoskeletal / FEM deformable) + runtime swap demo | Generic multi-fidelity arguments |

This guarantees tool labels appear on **one** slide (case study) and the
MultiComponent diagram appears on **one** slide (architecture).

## Architecture vs Implementation: editorial discipline

In a software-framework defense, Architecture and Implementation overlap by
nature --- the "what" (abstraction) and the "how" (realization) are not
physically separated as they are in hardware. With 20 min total, redrawing
the same picture twice is the most common time leak.

The working principle:

> **Architecture slide --- present the abstraction (the WHAT).**
> **Implementation slide --- present ONE non-obvious insight that the
> abstraction alone does not reveal (the HOW).**

If an implementation slide redraws the architectural picture or restates the
contract, it adds nothing --- cut it. If it shows a *sequence*, a *guard*, a
*complexity claim*, or a *verification number* that the abstraction cannot
show, it earns its place.

### The "one new insight" test

Before committing any implementation slide, ask:

> *"If the audience already understands the architecture slide, does this
> slide tell them something new?"*

- **Yes** → slide earns its place
- **No** → cut it, or replace its content with something that does

### What belongs where, per topic

| Topic | Architecture slide owns | Implementation slide owns |
|---|---|---|
| **CoSimComponent** | The contract (ports, lifecycle, state, hybrid hooks) | (no separate impl slide --- covered by tool wrappers) |
| **System Assembly** | The structural model + dependency-graph concept | (covered by structural-analysis half of S13) |
| **MultiComponent** | The 3-layer wrapper diagram (public / internal / switching support) | The trial-step guard + switching sequence (cached inputs → adapt → delegate) |
| **Master Algorithms** | Pluggable algorithm interface + decision table | (no separate impl slide --- choice is the point) |
| **Tool Wrappers** | (covered abstractly in adapter layer of S7) | The three concrete wrappers + Pint at the port boundary |
| **Algebraic Loops** | Named on the algorithms slide as "IJCSA needs interface Jacobian" | Interface-Jacobian Newton step + SCC condensation |
| **Hybrid Events** | Named on the algorithms slide as "Hybrid algorithm handles events" | Three event cases (single / simultaneous / cascaded) |

Implementation slides become **insight slides**, not redundant restatements.

### Implications for slide count

This discipline reduces Implementation to the irreducibly interesting bits.
Two slides suffice:

- **S12 Tool Wrappers + Units** --- three concrete wrappers + Pint at the port boundary
- **S13 Loops & Switching** --- two halves on one slide:
  - *Top:* SCC condensation + interface-Jacobian Newton step (one formula)
  - *Bottom:* switching-sequence pseudocode with the trial-step guard highlighted

The other implementation chapters (Component, System Assembly, Algorithms)
do not get dedicated slides --- their architecture slide is sufficient and
their realization details live in the wrapper / loop slides above.

### Verbal cross-reference (not visual)

On implementation slides, refer back to architecture verbally rather than
redrawing:

> *"As shown in the architecture, the MultiComponent has a state adapter
> and a mode selector. The interesting realization detail is the trial-step
> guard: ..."*

This keeps the visual on the new insight while honoring the audience's
prior knowledge.

## Visual Drafting Rules

- Prefer one full-slide figure plus a short title over text-heavy frames.
- Use progressive disclosure only when it clarifies a process: first show the
  physical system, then tools, then orchestration, then switching.
- Keep slide text to labels, axis names, and one optional takeaway line.
- Use PowerPoint or Inkscape for application schematics; use TikZ for diagrams
  that benefit from precise alignment, reusable styles, or LaTeX symbols.
- Keep notation consistent with the thesis: *subsystem* for the physical part,
  *simulation unit* for tool-neutral executable models, and *component* only for
  SysSimX objects.

## Q&A — likely questions and backup-slide pointers

Fill in as you draft. Format: *expected question → which backup slide answers it*.

- "Why this algorithm choice in the case study?" → backup: algorithm comparison
- "How does loop detection scale with system size?" → backup: SCC details
- "Why FMI/Modelica wasn't enough?" → backup: tool comparison (B4)
- "How much wall-clock per macro step?" → backup: performance numbers
- "What exactly does UR-XX / SR-XX say?" → backup: full UR/SR tables (B1, B2)
- "How do you know all requirements are met?" → backup: traceability matrix (B3)
- "Why these specific tools and not alternatives?" → backup: tool comparison (B4)
- "What does Heterogeneous Integration actually require?"
  → backup: three-tool integration diagram (B-Het, covers UR-05..08; UR-09 runtime switching shown on S4)
- "What is the exact wording of RQ-X?" → backup: research-question table (B-RQs)

## Drafting workflow

1. Replace TODOs in each chapter file with content.
2. Reuse thesis figures via `\graphicspath` — do not duplicate.
3. Rehearse with a timer; if a block runs long, **cut the slide** rather than
   speak faster.
4. Compile with `latexmk -pdf` after each chapter to catch errors early.
5. Final pass: produce a `handout` build by adding the `handout` option to
   `\documentclass` for a printable version without overlays.

## Conventions

- **Terminology** follows `thesis/guideline/glossary.md`: *subsystem* (physical),
  *simulation unit* (framework-neutral), *component* (SysSimX only) — never
  interchangeably.
- **Notation** follows `thesis/guideline/notation.md`.
- **Style:** one message per slide; avoid colon-then-list sentences in spoken
  prose; prefer figures and tables over walls of text.
