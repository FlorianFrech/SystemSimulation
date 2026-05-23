# Thesis Review Plan for the Final PDF

Once you have the final PDF, do **not** ask one model to “review my thesis” in one pass. Use a structured audit workflow with several narrowly scoped reviews. This gives much better results and makes the feedback actionable.

## 1. Prepare the Review Package

Create a folder with:

```text
thesis_review/
├── thesis_final.pdf
├── thesis_source.zip          # optional but useful: LaTeX source, figures, bib files
├── bibliography.bib
├── thesis_requirements.md     # your own goals / examiner expectations
├── audit_log.md
└── audit_prompts.md
```

Also include a short “review brief”:

```markdown
# Review Brief

Thesis topic:
Development of a Python framework for heterogeneous hybrid co-simulation with runtime model switching.

Main contribution:
- syssimx framework architecture
- heterogeneous components: FMU, OpenSim, FEM/NGSolve
- algebraic-loop handling
- hybrid event localization
- runtime model switching
- controlled pendulum with wall contact case study

Expected review style:
Critical, technical, specific, page-referenced.
Do not rewrite large sections unless asked.
Return issues with severity, page/section, reason, and concrete fix.
```

---

# 2. Recommended Audit Types

## A. Global Thesis Audit

**Purpose:** Check whether the whole thesis tells a coherent story.

Questions:

* Is the problem clearly motivated?
* Is the research gap explicit?
* Is the contribution distinguishable from existing tools?
* Are the theory, implementation, and validation chapters aligned?
* Does the conclusion follow from the evidence?

**Output format:**

```markdown
| Issue | Severity | Page/Section | Problem | Suggested Fix |
|---|---|---|---|---|
```

---

## B. Contribution and Novelty Audit

**Purpose:** Check whether the thesis clearly explains what `syssimx` contributes.

Focus points:

* Difference to FMI-only co-simulation frameworks
* Difference to PrePoMax/CalculiX, OpenSim, Modelica, CoFmuPy
* Why not just use an existing tool as backend
* Why heterogeneous wrappers are needed
* What is framework contribution vs. case-study contribution

This is important because your thesis must avoid sounding like “I built a small wrapper around existing tools.” The architecture and orchestration logic must be visible as the actual contribution.

---

## C. Theory-Chapter Audit

**Purpose:** Check whether Chapter 2 introduces only the theory needed to understand the implementation.

Focus points:

* No excessive repetition of motivation from Chapter 1
* Correct ordering: dynamical systems → co-simulation → FMI/OpenSim/FEM → hybrid systems → multi-fidelity/model switching
* Consistent notation
* No implementation details that belong in Chapter 5
* Clear distinction between background theory and thesis-specific algorithms

---

## D. Implementation-Consistency Audit

**Purpose:** Check whether implementation claims match the architecture and code.

Focus points:

* Component abstraction
* Port system
* unit handling
* direct feedthrough metadata
* dependency graph
* strongly connected components
* algebraic-loop solver
* event indicators
* rollback and bisection
* `MultiModelComponent`
* FEM/OpenSim/FMU wrappers

The reviewer should check whether terms are used consistently across chapters.

---

## E. Validation and Evidence Audit

**Purpose:** Check whether the validation claims are justified.

Focus points:

* What is verified on feature level?
* What is validated in the controlled-pendulum case study?
* Is “validation” used too strongly?
* Are reference models described sufficiently?
* Are numerical errors and runtime results interpreted correctly?
* Are limitations explicitly stated?

Use this audit to prevent overclaiming.

For example, the safe wording is:

```latex
The results provide numerical verification against model-based references and workflow validation through the controlled-pendulum case study.
```

Avoid:

```latex
The framework is validated for general heterogeneous biomechanical systems.
```

---

## F. Figure, Table, and Caption Audit

**Purpose:** Check whether all visual material is useful and self-contained.

Checklist:

* Every figure is referenced before or near its appearance.
* Every caption explains what the reader should see.
* Diagrams use consistent terminology.
* Ports, components, solvers, and signals use the same names as in the text.
* Plots include units, legends, and readable labels.
* Architecture diagrams distinguish framework layers from external tools.

---

## G. Notation and Terminology Audit

**Purpose:** Avoid a fragmented technical vocabulary.

Check consistency for terms such as:

| Preferred Term           | Avoid Mixing With                                             |
| ------------------------ | ------------------------------------------------------------- |
| component                | block, module, subsystem, unit — unless clearly distinguished |
| subsystem model          | model, simulator, component — if not defined                  |
| input port / output port | input variable / signal, if not consistently mapped           |
| communication step       | macro step, global step — define equivalence                  |
| local integration step   | micro step, solver step                                       |
| runtime model switching  | model exchange, fidelity switching, mode switching            |
| direct feedthrough       | feed-through, feedthrough, instantaneous dependency           |
| algebraic loop           | cyclic dependency, SCC — define relation                      |

This audit is especially important for your thesis.

---

## H. Citation and Literature Audit

**Purpose:** Check whether claims are properly supported.

Focus points:

* FMI standard cited where FMI concepts are introduced
* CVODE/SUNDIALS cited where solver behavior is discussed
* OpenSim/Simbody cited where musculoskeletal simulation is introduced
* NGSolve/FEM references cited where FEM backend is introduced
* Co-simulation and algebraic-loop papers cited in the correct places
* Multi-fidelity papers cited near runtime model switching
* PrePoMax/CalculiX discussion cited as tool comparison, not as used backend

Also check:

* no uncited “state-of-the-art” claims,
* no citation dumping,
* no citations in abstract,
* BibTeX keys compile,
* all references are used.

---

## I. Language and Style Audit

**Purpose:** Improve readability without making the thesis sound AI-generated.

Ask for:

* overly long sentences,
* repeated phrases,
* vague claims,
* passive constructions that hide the contribution,
* German-English interference if writing in English,
* inconsistent tense,
* too much “framework enables…” repetition.

Do this late, after content is stable.

---

## J. Final PDF Integrity Audit

**Purpose:** Catch technical PDF problems.

Checklist:

* Page numbers correct
* TOC entries correct
* List of figures/tables complete
* No overfull boxes visible
* No missing references: `??`
* No missing citations: `[?]`
* Equations numbered only when referenced
* Captions do not overflow
* Figures are not blurry
* Hyperlinks work
* Bibliography formatting acceptable
* Appendix references work
* Abstract/Kurzfassung no citations

---

# 3. Suggested Review Schedule

## Round 1 — Structural Review

**Input:** final PDF
**Goal:** large-scale issues only
**Do not:** fix grammar yet

Audits:

1. Global thesis audit
2. Contribution audit
3. Chapter flow audit

Output: 10–25 high-level issues.

---

## Round 2 — Technical Review

**Input:** final PDF + selected source chapters
**Goal:** correctness and consistency

Audits:

1. Theory audit
2. Implementation-consistency audit
3. Validation/evidence audit
4. Terminology/notation audit

Output: page-specific technical issue list.

---

## Round 3 — Literature and Citation Review

**Input:** final PDF + `.bib` file
**Goal:** check citations and references

Audits:

1. Citation adequacy
2. Tool comparison support
3. Related-work positioning
4. Missing or weak references

Output: missing citation list and misplaced citation list.

---

## Round 4 — Presentation Review

**Input:** final PDF
**Goal:** readability and examiner experience

Audits:

1. Figure/table audit
2. Language/style audit
3. Abstract and conclusion audit

Output: final polishing list.

---

## Round 5 — Submission Audit

**Input:** final compiled PDF
**Goal:** technical correctness before submission

Audits:

1. PDF integrity
2. formatting
3. references
4. lists
5. page layout

Output: only blocking/minor submission issues.

---

# 4. Which AI Tools to Use

## Best Setup

Use **several models as independent reviewers**, not one model repeatedly.

| Tool                             | Best Use                                                                                     |
| -------------------------------- | -------------------------------------------------------------------------------------------- |
| **ChatGPT**                      | project continuity, technical reasoning, architecture consistency, LaTeX/source-aware review |
| **Claude**                       | prose, argumentation, long-form critique, readability, reviewer-style feedback               |
| **Gemini**                       | very long-context full-document scans, cross-chapter consistency, large PDF inspection       |
| **Human supervisor / colleague** | final judgment, scientific correctness, grading expectations                                 |

ChatGPT is suitable if you keep the thesis, prompts, prior summaries, tool comparisons, and thesis requirements in one Project. OpenAI describes Projects as workspaces for long-running work where chats, uploaded files, and custom instructions can be grouped together. ChatGPT file uploads can also be used to search a PDF, extract information, and find references to topics inside documents. ([OpenAI Help Center][1])

Claude is useful for PDF-based document critique because Anthropic documents that Claude can answer questions about text, pictures, charts, and tables in PDFs. That makes it suitable for readability, argumentative flow, and figure/table interpretation. ([platform.claude.com][2])

Gemini is useful for whole-document scans because Google emphasizes long-context processing and file analysis. Google states that Gemini can upload and analyze documents and that Gemini 2.5 Pro uses a 1-million-token context window; its API documentation also states PDF support up to 50 MB or 1000 pages. ([Google Hilfe][3])

---

# 5. Recommended Agent Roles

## Agent 1 — Examiner Reviewer

Prompt:

```markdown
You are a strict examiner for a master's thesis in Computational Science and Engineering.

Review the uploaded thesis PDF. Focus only on:
- clarity of research problem,
- contribution,
- structure,
- scientific argument,
- whether the conclusions are supported by evidence.

Return a table with:
Severity | Page/Section | Issue | Why it matters | Concrete fix.

Do not rewrite text unless necessary.
Be critical and specific.
```

---

## Agent 2 — Technical Consistency Reviewer

```markdown
You are a technical reviewer for a thesis on heterogeneous hybrid co-simulation.

Audit the thesis for consistency of:
- component abstraction,
- ports,
- units,
- direct feedthrough,
- dependency graph,
- algebraic loops,
- event handling,
- rollback,
- runtime model switching,
- FEM/OpenSim/FMU wrappers.

Identify contradictions, ambiguous terminology, missing definitions, and claims that are not sufficiently justified.
Return page-specific issues.
```

---

## Agent 3 — Literature Positioning Reviewer

```markdown
Review the related work and tool-comparison parts of the thesis.

Check whether the thesis clearly distinguishes syssimx from:
- FMI/FMU-based co-simulation tools,
- CoFmuPy,
- OMSimulator,
- OpenModelica,
- OpenSim,
- NGSolve/Netgen,
- PrePoMax/CalculiX,
- multi-fidelity and switched-fidelity approaches.

Identify missing comparisons, overclaims, and places where citations are needed.
```

---

## Agent 4 — Validation Reviewer

```markdown
Review only the validation, verification, case-study, and results chapters.

Check:
- whether each experiment has a clear purpose,
- whether references/baselines are appropriate,
- whether runtime results are interpreted correctly,
- whether the terms verification and validation are used carefully,
- whether limitations are explicit.

Flag all unsupported claims.
```

---

## Agent 5 — Final Copyeditor

```markdown
Act as a technical copyeditor.

Focus on:
- sentence clarity,
- repeated phrases,
- overly long sentences,
- inconsistent tense,
- awkward wording,
- unclear references such as "this", "it", "the system",
- captions and section transitions.

Do not change technical meaning.
Return concise edits with page/paragraph references.
```

---

# 6. Audit Log Template

Use one central `audit_log.md`:

```markdown
# Thesis Audit Log

| ID | Severity | Source | Page/Section | Category | Issue | Proposed Fix | Status |
|---|---|---|---|---|---|---|---|
| A001 | High | ChatGPT structural audit | Ch. 1 | Contribution | Contribution not explicit enough before related work | Add a paragraph listing thesis contributions | Open |
| A002 | Medium | Claude style audit | Ch. 2 | Style | Long paragraph with repeated motivation | Split and remove duplicated sentence | Open |
| A003 | Low | Gemini PDF audit | Fig. 5.3 | Figure | Caption does not explain dashed red arrows | Extend caption | Done |
```

Use severity levels:

| Severity     | Meaning                               |
| ------------ | ------------------------------------- |
| **Blocking** | Must fix before submission            |
| **High**     | Likely affects grade or understanding |
| **Medium**   | Should fix if time permits            |
| **Low**      | Polishing                             |
| **Ignore**   | Not worth changing                    |

---

# 7. Best Practical Strategy

Use this division:

```text
ChatGPT:
- thesis-specific technical coherence
- syssimx architecture
- LaTeX-aware edits
- audit log synthesis

Claude:
- readability
- argument flow
- examiner-style critique
- concise rewriting

Gemini:
- full-PDF consistency scan
- repeated terminology
- cross-chapter contradictions
- missing references to figures/tables

Human:
- final scientific judgment
- supervisor expectations
- whether the contribution is convincing
```

Do not let any model directly rewrite the whole thesis. Use them to produce **issues**, then decide manually what to change.

---

# 8. Minimal Plan if Time Is Short

If you only have 2–3 days:

1. **Day 1:** Global thesis audit + contribution audit
2. **Day 2:** Validation/evidence audit + citation audit
3. **Day 3:** Language/style audit + final PDF integrity audit

The highest-value audits for your thesis are:

1. **Contribution clarity**
2. **Validation claims**
3. **Terminology consistency**
4. **Tool-comparison justification**
5. **Final PDF integrity**

[1]: https://help.openai.com/en/articles/10169521-projects-in-chatgpt?utm_source=chatgpt.com "Projects in ChatGPT"
[2]: https://platform.claude.com/docs/en/build-with-claude/pdf-support?utm_source=chatgpt.com "PDF support - Claude API Docs"
[3]: https://support.google.com/gemini/answer/14903178?co=GENIE.Platform%3DAndroid&hl=en&utm_source=chatgpt.com "Upload & analyze files in Gemini Apps - Android"