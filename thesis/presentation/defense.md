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
| 1 | Introduction                 |   3 |      3 | `chapters/01_introduction.tex`    |
| 2 | Background *(optional)*      |   0 |    0–1 | `chapters/02_background.tex`      |
| 3 | Requirements                 |   1 |      1 | `chapters/03_requirements.tex`    |
| 4 | Architecture                 | 3.5 |      3 | `chapters/04_architecture.tex`    |
| 5 | Implementation               | 1.5 |      2 | `chapters/05_implementation.tex`  |
| 6 | Case study *(centerpiece)*   |   8 |      5 | `chapters/06_case_study.tex`      |
| 7 | Discussion & Conclusion      |   2 |      2 | `chapters/07_conclusion.tex`      |
|   | Thank you                    |  <1 |      1 | `slides.tex`                      |
|   | **Total**                    |  20 |    ~18 |                                   |

Backup slides in `chapters/99_backup.tex` (numbered separately via
`appendixnumberbeamer`) — only shown if asked.

## Per-slide intent

Each slide should communicate **one** thing. Notes below are the *single point*
the slide must land — refine wording during drafting, but do not let a slide
drift past one main message.

### Title + outline
- **S0 Title** — title, author, supervisor, date.
- **S1 Outline** — one line per section; no sub-bullets.

### 1. Introduction (3 min)
- **S2 Heterogeneous simulation need** - active prostheses and exoskeletons
  form one coupled dynamic system with the human body. Biomechanics,
  structural mechanics, and control/electronics are naturally modeled in
  different domain tools. One figure should carry both the physical coupling
  and the tool fragmentation.
- **S3 Orchestration is nontrivial** - coupled simulation units may have
  direct-feedthrough dependencies, algebraic loops, and hybrid events. The
  slide motivates why structural analysis, loop handling, and event handling
  are needed before introducing implementation details.
- **S4 Runtime switching and gap** - one subsystem may need different model
  fidelities in different phases. Runtime switching motivates selective use of
  high-fidelity models, and the gap statement explains why SysSimX is needed as
  one Python-based orchestration workflow.

### 3. Requirements (1 min)
- **S5 Requirements** — 4 categories (general modeling, heterogeneous
  integration, simulation, interaction) shown as a compact 2×2 table; one row
  beneath shows the traceability (SR → implementation features, UR →
  case-study validation). No derivation methodology on the slide — only what
  was required and how it traces. Backups B1–B4 cover full UR/SR lists,
  traceability matrix, and tool comparison.
  (Skip ch2 unless rehearsal proves it is needed.)

### 4. Architecture (3.5 min)
- **S6 Overview** — the SysSimX block diagram. One sentence per layer.
- **S7 Core abstractions** — Component / Port / System; unit-aware coupling.
- **S8 Algorithms** — when to use Gauss-Seidel, Jacobi, Hybrid, IJCSA.

### 5. Implementation (1.5 min)
- **S9 Wrappers + units** — three tool wrappers behind one Component interface;
  Pint at the port boundary.
- **S10 Loops + switching** — algebraic-loop detection (SCC) and runtime
  MultiComponent switching used in the case study.

### 6. Case study (8 min — centerpiece)
- **S11 System** — full control loop, one diagram.
- **S12 Three backends** — fidelity/cost trade-off in one row of figures.
- **S13 Validation** — reference model + scenarios; what is being measured.
- **S14 Results** — the single most convincing plot + headline number.
- **S15 Multi-model switching** — runtime model swap demo.

### 7. Discussion (2 min)
- **S16 Answers + limitations** — one bullet per RQ; honest single-bullet limit.
- **S17 Outlook** — 2–3 concrete next steps.

### Close
- **S18 Thanks** — supervisors, collaborators, institute.

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

### S4 Runtime switching and framework gap - why SysSimX exists

- **Show:** one subsystem with alternative representations along a fidelity/cost
  axis: `rigid / FMU`, `musculoskeletal / OpenSim`, and `deformable / FEM`.
  Add a short time strip below it that shows when different models are active.
  End the slide with a small `needs -> SysSimX -> evaluation` graphic.
- **Tell:** low-fidelity models are useful for global motion and controller
  behavior. High-fidelity models are useful for local effects such as
  deformation, stress, or contact. Runtime switching targets the useful
  fidelity/cost compromise, but it also requires consistent state transfer and
  a stable shared interface.
- **Gap statement:** "Existing FMI-centered frameworks support important parts
  of co-simulation, but the evaluated alternatives did not provide the complete
  combination of Python-side heterogeneous wrappers, structural dependency
  analysis, algebraic-loop handling, hybrid events, and runtime model switching
  required for this workflow."
- **Landing sentence:** "SysSimX is the implemented orchestration layer for this
  combined workflow, evaluated on the controlled-pendulum case study."
- **Avoid:** full research-question text on the slide. Use short chips such as
  `heterogeneous tools`, `dependencies`, `events`, `loops`, and `switching`.

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
