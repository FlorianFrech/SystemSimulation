# Thesis Audit Prompts

Target reviewer prompts for the structured thesis audit. Each prompt is a
self-contained reviewer brief. Use them with an external model on the final PDF
(see `review_plan.md` for the tool split) or run them in-session against the
LaTeX source.

The thesis-review package described in `review_plan.md` is this `guideline/`
directory. The guideline documents are the **ground truth**. A reviewer must
treat them as authoritative and flag any thesis text that conflicts with them,
rather than inventing its own style or terminology rules.

---

## How to use these prompts

1. Pick the audit. Each one is narrow on purpose. Do not merge them into a
   single "review my thesis" pass.
2. Give the reviewer the **inputs** listed in the prompt (the PDF or the named
   source files, plus the named ground-truth guideline docs).
3. Require the **output format** below for every audit.
4. Collect all findings in one `audit_log.md` and triage by severity.

### Shared output format

Every audit returns one Markdown table:

```markdown
| ID | Severity | Page/Section | Category | Issue | Why it matters | Proposed fix |
|---|---|---|---|---|---|---|
```

- One row per issue. No prose essays. No rewriting whole sections.
- `ID` uses the audit's prefix (e.g. `CN-01` for Contribution/Novelty).
- Quote the offending sentence when the issue is wording.

### Severity scale (from `review_plan.md` §6)

| Severity | Meaning |
|---|---|
| Blocking | Must fix before submission |
| High | Likely affects grade or understanding |
| Medium | Should fix if time permits |
| Low | Polishing |
| Ignore | Not worth changing |

### Ground-truth documents (authority order)

`README.md` > `thesis_concept.md` > `golden_rules_writing_summary.md` >
`writing_style.md` > `glossary.md` > `notation.md` > chapter guideline >
`claims_and_evidence.md` / `revision_checklist.md`.

If a reviewer is unsure whether something is a defect, it checks these docs
first. If the docs are silent, it flags the item as a question, not a defect.

---

## CN — Contribution and Novelty Audit

```markdown
You are a strict examiner for a master's thesis in Computational Science and
Engineering. The thesis develops syssimx, a Python framework for heterogeneous
hybrid co-simulation with runtime model switching.

Inputs: the final PDF (Chapters 1, 2, 7 are primary; skim 4-6 for support) and
the ground-truth docs thesis_concept.md (esp. sections 3, 4, 7) and
claims_and_evidence.md.

Check only:
- Is the framework contribution stated explicitly and early, before related work?
- Is syssimx clearly distinguished from FMI-only co-simulation tools, CoFMPy,
  OMSimulator, OpenModelica, OpenSim, NGSolve/Netgen, and PrePoMax/CalculiX?
- Does the thesis ever read like "a thin wrapper around existing tools"? The
  architecture and orchestration logic must be visible as the actual
  contribution.
- Is the framework contribution kept separate from the case-study contribution?
  (Per thesis_concept.md, the controlled pendulum is the test system, not a new
  model contribution.)
- Are the seven main claims in thesis_concept.md §7 each made somewhere, and
  none over-stated beyond what §4 "Non-goals" allows?

Flag every place the contribution is vague, buried, missing, or overclaimed.
Return the shared output table with IDs CN-01, CN-02, ...
Be critical and specific. Do not rewrite text.
```

---

## NC — Narrative Coherence and Chapter-Boundary Audit

```markdown
You review whether the thesis tells one coherent story and whether each chapter
stays in its lane.

Inputs: the final PDF (all chapters) and the ground-truth docs
thesis_concept.md (§5 narrative, §6 chapter roles) and README.md (§4 chapter
boundaries).

Check only:
- Does the argument flow as in thesis_concept.md §5: heterogeneous simulation
  need -> co-simulation basis -> architecture -> implementation+verification ->
  case study -> discussion?
- Does any chapter absorb another chapter's role? Specifically: Chapter 1
  motivation repeated later; unused theory in Chapter 2; implementation detail
  in Chapter 2; Chapter 5 drifting into API documentation; Chapter 6 becoming a
  second implementation chapter; new technical detail introduced in Chapter 7.
- Do chapter transitions connect, or do chapters read as disconnected reports?
- Is Chapter 6 substantial enough relative to Chapter 5? (A stated thesis risk.)

Return the shared output table with IDs NC-01, NC-02, ...
Report boundary violations and narrative gaps only. Do not rewrite.
```

---

## TH — Theory Scope Audit (Chapter 2)

```markdown
You review Chapter 2 for scope discipline.

Inputs: the final PDF Chapter 2, and the ground-truth docs ch2_theory.md,
README.md §4, glossary.md, and notation.md.

Check only:
- Does Chapter 2 introduce only theory that is later used in the implementation
  or case study? Flag any theory block with no downstream use.
- Is the ordering coherent (dynamical systems -> co-simulation -> FMI / OpenSim
  / FEM -> hybrid systems -> multi-fidelity / model switching)?
- Does Chapter 2 leak implementation details that belong in Chapter 5?
- Does it repeat Chapter 1 motivation?
- Is the boundary between general background theory and thesis-specific
  algorithms clear (the thesis-specific master algorithms belong to Chapter 5,
  not here)?

Return the shared output table with IDs TH-01, TH-02, ...
```

---

## IC — Implementation Consistency Audit (Chapters 4 and 5)

```markdown
You are a technical reviewer for a thesis on heterogeneous hybrid co-simulation.

Inputs: the final PDF Chapters 4 and 5, and the ground-truth docs
ch4_architecture.md, ch5_implementation.md, glossary.md, and notation.md.

Audit consistency of the following concepts across architecture (Ch4) and
implementation (Ch5):
- component abstraction and the shared component interface,
- typed and unit-aware ports,
- direct-feedthrough metadata,
- dependency graph and execution ordering,
- strongly connected components and algebraic-loop resolution (IJCSA),
- event indicators, rollback, bisection, superdense time,
- the multi-model component (fixed external interface, switchable internal
  model) and the Master Pendulum,
- the FMU, OpenSim, and FEM backend wrappers.

Flag: contradictions between Ch4 and Ch5, a class/method named differently in
two places, missing definitions, and implementation claims not backed by the
described design. Verify each term matches glossary.md (subsystem vs simulation
unit vs component vs System are distinct - do not accept them as synonyms).

Return the shared output table with IDs IC-01, IC-02, ...
Page-specific. Do not rewrite.
```

---

## VE — Validation and Evidence Audit (Chapters 5, 6, 7)

```markdown
You review whether every claim is backed by the right kind of evidence and
whether verification / validation / benchmark wording is used correctly.

Inputs: the final PDF (Chapter 5 verification sections, all of Chapter 6, the
results discussion in Chapter 7) and the ground-truth docs claims_and_evidence.md,
README.md §5 (claim boundaries), and thesis_concept.md §8 (evidence strategy).

Check only:
- Each experiment has a clear, stated purpose.
- Reference models / baselines are described well enough to be reproducible.
- "Validation" is not used where the work is numerical verification against the
  OpenModelica reference. "Physical validation" appears only if experimental
  data are used (they are not).
- Benchmark / runtime results are not used as correctness evidence.
- Numerical results (convergence, deviation, speedup) are stated with concrete
  values and the tested scenario.
- No single case-study result is generalized to all hybrid co-simulation.
- Limitations are explicit, especially the state-projection deviation at the
  FMU-to-FEM switch and the contact-model mismatch.
- Every row of claims_and_evidence.md §2 is supported in the text, and no claim
  exceeds its evidence level.

Flag all unsupported or over-strong claims. Return the table with IDs VE-01, ...
```

---

## TN — Terminology and Notation Audit

```markdown
You enforce consistent vocabulary and notation across the whole thesis.

Inputs: the final PDF (all chapters) and the ground-truth docs glossary.md and
notation.md. THESE TWO DOCS ARE BINDING. Do not apply any external style guide's
terminology table - use only glossary.md and notation.md.

Terminology checks (per glossary.md):
- subsystem (physical/theoretical), simulation unit (tool-neutral executable),
  component (concrete syssimx implementation) are a deliberate hierarchy and are
  NOT interchangeable. Flag any place they are mixed or swapped.
- System (the syssimx class) vs system (physical/mathematical) used correctly.
- master algorithm, communication step, local integration step, direct
  feedthrough, algebraic loop, runtime model switching - each used in its
  glossary sense, spelled consistently.
- verification / validation / benchmark used per the glossary definitions.

Notation checks (per notation.md):
- No global symbol redefined locally.
- Time, communication-point, event-time, and superdense-time notation
  consistent throughout.
- The macro/communication step symbol is used consistently (watch for H_k vs
  Delta t drift); flag any unreconciled dual usage.
- The thesis notation table matches notation.md.

Return the shared output table with IDs TN-01, TN-02, ...
For each issue give the exact term/symbol, the two conflicting uses, and the
glossary/notation entry that resolves it.
```

---

## LIT — Citation and Literature Audit

```markdown
You review whether claims are properly supported by citations and whether
related work positions syssimx correctly.

Inputs: the final PDF, references.bib, and the ground-truth docs
thesis_concept.md and claims_and_evidence.md.

Check:
- FMI standard cited where FMI concepts are introduced.
- CVODE/SUNDIALS cited where solver behavior is discussed.
- OpenSim/Simbody cited where musculoskeletal simulation is introduced.
- NGSolve/Netgen and FEM references cited where the FEM backend is introduced.
- Co-simulation and algebraic-loop papers cited in the right places.
- Multi-fidelity / switched-fidelity papers cited near runtime model switching
  (Chapters 6 and 7).
- PrePoMax/CalculiX discussed as a tool comparison, not as a used backend.

Also flag:
- uncited "state-of-the-art" or "it is well known" claims,
- citation dumping (long undifferentiated citation lists),
- any citation inside the abstract or Kurzfassung,
- references that are never cited,
- claims that need a citation and have none.

Return the shared output table with IDs LIT-01, LIT-02, ...
Separate "missing citation" rows from "misplaced citation" rows in the Category
column.
```

---

## FIG — Figure, Table, and Caption Audit

```markdown
You review all visual material for usefulness and self-containment.

Inputs: the final PDF and the ground-truth docs writing_style.md (figure/table/
caption rules), README.md §8, and glossary.md.

Check each figure and table:
- It is referenced in the text before or near where it appears.
- The caption explains what the reader should learn, and does not just repeat
  the surrounding paragraph.
- Short-form captions are used for the List of Figures/Tables (\caption[short]{long}).
- Diagram labels (ports, components, solvers, signals, layers) use the same
  names as the prose and match glossary.md.
- Architecture diagrams distinguish framework layers from external tools.
- Plots have units, legends, and readable labels; values are traceable to the
  notebooks.
- No table is in method-list style; no figure duplicates a full paragraph.

Return the shared output table with IDs FIG-01, FIG-02, ...
Identify each item as Fig. N / Tab. N.
```

---

## ST — Language and Style Audit

```markdown
You are a technical copyeditor. Improve readability without changing technical
meaning and without making the text sound generated.

Inputs: the final PDF and the ground-truth docs writing_style.md and
golden_rules_writing_summary.md.

Flag:
- overly long sentences and sentences joined by colons or semicolons (the thesis
  style splits these),
- repeated phrases, especially "the framework enables ..." style repetition,
- vague claims and inflated academic phrasing,
- passive constructions that hide the contribution,
- unclear references ("this", "it", "the system" with no clear antecedent),
- inconsistent tense,
- German-English interference,
- weak section transitions.

Run this late, after content is stable. Do not change technical meaning.
Return the shared output table with IDs ST-01, ST-02, ... with a concise
suggested edit per row.
```

---

## PDF — Final PDF Integrity and Submission Audit

```markdown
You do the final technical pass on the compiled PDF before submission.

Inputs: the final compiled PDF only.

Checklist (one row per defect found):
- Page numbers and TOC entries correct.
- List of Figures and List of Tables complete and using short captions.
- No unresolved cross-references (??) and no missing citations ([?]).
- No visible overfull/underfull boxes; captions do not overflow.
- Equations numbered only when referenced.
- Figures are sharp, not blurry or pixelated.
- Hyperlinks and appendix references work.
- Bibliography formatting is consistent.
- Abstract and Kurzfassung contain no citations.
- Acronyms expanded on first use; the acronym list shows only used acronyms.

Return the shared output table with IDs PDF-01, PDF-02, ...
Report only blocking and minor submission defects.
```
