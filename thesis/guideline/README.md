# Thesis Guideline Directory

This directory is the authoritative working reference for drafting, revising,
and polishing the thesis.
It is intended for the author, Codex, Claude Code, and any other writing or
review assistant used during the thesis process.

The purpose of this directory is to keep the thesis coherent across chapters.
It defines the thesis scope, chapter roles, writing style, terminology,
notation, claim boundaries, and revision rules.

All thesis drafts should follow the rules in this directory.
If a draft conflicts with these guidelines, the draft should be revised or the
conflict should be raised explicitly.

---

## 1. Authority and Reading Order

Use the documents in the following order.
Higher-ranked documents define the global rules.
Lower-ranked documents add chapter-specific detail.

1. `README.md`
   - Entry point and authority hierarchy.
   - Defines how the guideline directory is used.

2. `thesis_concept.md`
   - Global thesis objective, chapter roles, scope boundaries, and current
     thesis-level risks.

3. `golden_rules_writing_summary.md`
   - Writing principles based on Hengl and Gould.
   - Defines the expected research-writing logic.

4. `writing_style.md`
   - Concrete thesis voice, wording rules, rewrite patterns, and figure,
     table, caption, equation, and limitation style.

5. `glossary.md`
   - Single source of truth for terminology.
   - Defines terms such as subsystem, simulation unit, component, System,
     co-simulation, verification, validation, and benchmark.

6. `notation.md`
   - Single source of truth for mathematical notation.
   - Defines global symbols and their implementation mapping.

7. Chapter-specific guideline documents
   - `ch1_intro.md` for Chapter 1.
   - `ch2_theory.md` for Chapter 2.
   - `ch3_requirements.md` for Chapter 3.
   - `ch4_architecture.md` for Chapter 4.
   - `ch5_implementation.md` for Chapter 5.
   - `ch6_case_study.md` for Chapter 6.
   - `ch7_discussion.md` for Chapter 7.

8. Supporting workflow documents
   - `claims_and_evidence.md` for mapping claims to evidence.
   - `revision_checklist.md` for cleanup and final polishing tasks.

If two guideline documents conflict, use this order to resolve the conflict.
If the conflict cannot be resolved safely, raise it before drafting.

---

## 2. Mandatory Rule for Writing Assistants

Before drafting or revising thesis prose, Codex and Claude Code must read:

- this `README.md`,
- `thesis_concept.md`,
- `golden_rules_writing_summary.md`,
- `writing_style.md`,
- `glossary.md`,
- `notation.md`,
- and the chapter-specific guideline for the affected chapter.

For result, discussion, conclusion, and abstract drafting, also read
`claims_and_evidence.md`.
For cleanup or polishing tasks, also read `revision_checklist.md`.

Do not draft from local context alone if the task concerns thesis prose.
Do not introduce new terminology or notation without checking the glossary and
notation documents.
Do not introduce new claims without checking whether the claim is supported by
figures, tables, requirements, code, notebooks, or cited literature.

---

## 3. Global Writing Style

The thesis should follow a clear, direct, and technically precise style.

Use:

- short sentences,
- concrete verbs,
- explicit claim boundaries,
- consistent terminology,
- consistent notation,
- direct cross-references,
- figures and tables only when they add evidence or clarity.

Avoid:

- inflated academic phrasing,
- vague abstractions,
- repeated motivation,
- repeated theory,
- method-by-method software documentation,
- long sentences joined by colons or semicolons,
- unsupported claims,
- hiding limitations.

Preferred sentence style:

```text
The switched configuration reduced the FEM solver time by 2.03x.
The trajectory deviation was concentrated in the contact window.
This deviation follows from the state projection at the FMU-to-FEM switch.
```

Avoid sentence style:

```text
It can be observed that the proposed methodology facilitates an improvement
with respect to computational performance while maintaining acceptable
simulation quality.
```

---

## 4. Chapter Boundaries

Each chapter has one primary function.
Do not let one chapter take over the role of another chapter.

| Chapter | Function |
|---|---|
| Chapter 1 | Motivation, research gap, contributions, and related work orientation |
| Chapter 2 | Minimum theory needed for the framework, implementation, and case study |
| Chapter 3 | Requirements and tool choices |
| Chapter 4 | Framework architecture and abstractions |
| Chapter 5 | Implementation and feature-level verification |
| Chapter 6 | Controlled-pendulum case study and system-level evidence |
| Chapter 7 | Discussion, limitations, conclusions, and outlook |

Boundary rules:

- Do not repeat Chapter 1 motivation in later chapters.
- Do not include unused theory in Chapter 2.
- Do not put implementation details into Chapter 2.
- Do not turn Chapter 5 into API documentation.
- Do not turn Chapter 6 into another implementation chapter.
- Do not introduce new technical detail in Chapter 7.

---

## 5. Claim Boundaries

Use the following terms consistently.

| Term | Meaning in this thesis |
|---|---|
| Verification | Checking that an implementation or numerical result matches an expected reference, analytical result, unit test, or monolithic numerical reference |
| Validation | Showing that the framework workflow is suitable for the intended case-study purpose |
| Physical validation | Comparison against experimental physical data |
| Benchmark | Measurement of computational cost or runtime behavior |

Important boundary:

- Comparing `syssimx` with OpenModelica is numerical verification, not physical
  validation.
- Showing that heterogeneous tools, hybrid events, and model switching work
  together is framework workflow validation.
- Runtime measurements are benchmarks.
- Physical validation is only claimed if experimental data is used.

---

## 6. Terminology Rules

Use the glossary as binding.
The following hierarchy is especially important.

```text
subsystem -> simulation unit -> component
```

- Use `subsystem` for the physical or theoretical part of a system.
- Use `simulation unit` for a tool-neutral executable co-simulation participant.
- Use `component` only for the concrete `syssimx` implementation.
- Use `System` only for the concrete `syssimx` class.
- Use `system` for the physical or mathematical system.
- Use `master algorithm` for co-simulation orchestration.

Do not use these terms interchangeably.

---

## 7. Notation Rules

Use `notation.md` as binding.

Rules:

- Do not redefine global symbols locally.
- Define local symbols only when they are needed.
- Keep time notation consistent.
- Keep communication-point notation consistent.
- Keep event-time and superdense-time notation consistent.
- Update `notation.md` before changing the notation in thesis prose.

The notation table in the thesis should be derived from `notation.md`.
It should not evolve independently.

---

## 8. Figures, Tables, and Captions

Use figures and tables strategically.
They should support the argument, not repeat the prose.

Figures should:

- show architecture, data flow, control flow, or numerical evidence,
- be referenced before or near their appearance,
- have captions that explain what the reader should learn,
- avoid duplicating full paragraphs from the text.

Tables should:

- summarize comparisons,
- state requirements or verified properties compactly,
- avoid method-list style,
- avoid duplicating class diagrams.

Captions should:

- be self-contained enough to interpret the figure,
- not introduce unsupported claims,
- not repeat the surrounding paragraph verbatim.

---

## 9. Drafting Workflow

Use this workflow for every substantial thesis edit.

1. Identify the chapter and section role.
2. Read the relevant guideline documents.
3. Check glossary and notation.
4. Identify the claim being made.
5. Identify the evidence that supports the claim.
6. Draft concise prose.
7. Remove repeated theory or implementation detail.
8. Check cross-references, labels, notation, and terminology.
9. Check whether the paragraph belongs in another chapter.

If the evidence is missing, write the limitation or leave the claim out.

---

## 10. Agent Behavior Rules

Codex and Claude Code should follow these rules.

- Prefer thesis-ready LaTeX prose when the user asks for a draft.
- State when a paragraph should replace existing text.
- Do not silently edit files if the user asks only for draft text.
- Do edit files when the user explicitly asks to implement or update.
- Keep wording close to the user's technical voice.
- Avoid generic thesis filler.
- Avoid broad claims without numerical or structural support.
- Raise terminology, notation, or scope conflicts explicitly.
- Suggest compaction when a section repeats another chapter.
- Keep verification, validation, benchmark, and discussion separate.

---

## 11. Maintenance Rules

Keep this directory consistent.

- Update paths when files are moved.
- Remove obsolete references to old guideline locations.
- Do not duplicate glossary entries in chapter-specific files.
- Do not duplicate notation definitions in chapter-specific files.
- Keep chapter guidelines focused on chapter role, structure, claim boundary,
  and evidence.
- Move long engineering notes out of chapter guidelines if they become too
  detailed for drafting.

Recommended future additions:

- Fill `ch1_intro.md`, `ch3_requirements.md`, and `ch4_architecture.md`
  when those chapters enter a dedicated polishing pass.

---

## 12. Short Rule

Write only what the reader needs at that point in the thesis.
Use the right chapter for the right type of content.
Make every claim traceable to evidence.
