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
| 4 | Architecture                 |   4 |      3 | `chapters/04_architecture.tex`    |
| 5 | Implementation               |   2 |      2 | `chapters/05_implementation.tex`  |
| 6 | Case study *(centerpiece)*   |   7 |      5 | `chapters/06_case_study.tex`      |
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
- **S2 Motivation** — device performance for prosthetics/exoskeletons depends on
  device–human interaction; single-tool simulation cannot capture both sides.
- **S3 Gap & RQs** — existing tools handle one domain well; the three RQs ask
  *what does a heterogeneous co-simulation framework need to do?*
- **S4 Objectives** — SysSimX + the controlled-pendulum case study as proof.

### 3. Requirements (1 min)
- **S5 Requirements** — compact table; no prose. (Skip ch2 unless rehearsal
  proves it is needed.)

### 4. Architecture (4 min)
- **S6 Overview** — the SysSimX block diagram. One sentence per layer.
- **S7 Core abstractions** — Component / Port / System; unit-aware coupling.
- **S8 Algorithms** — when to use Gauss-Seidel, Jacobi, Hybrid, IJCSA.

### 5. Implementation (2 min)
- **S9 Wrappers + units** — three tool wrappers behind one Component interface;
  Pint at the port boundary.
- **S10 Loops + switching** — algebraic-loop detection (SCC) and runtime
  MultiComponent switching used in the case study.

### 6. Case study (7 min — centerpiece)
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

## Q&A — likely questions and backup-slide pointers

Fill in as you draft. Format: *expected question → which backup slide answers it*.

- "Why this algorithm choice in the case study?" → backup: algorithm comparison
- "How does loop detection scale with system size?" → backup: SCC details
- "Why FMI/Modelica wasn't enough?" → backup: tool comparison
- "How much wall-clock per macro step?" → backup: performance numbers

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
