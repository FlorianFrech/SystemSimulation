# Revision Checklist

This document collects operational cleanup tasks that should not live in
`thesis_concept.md`.
It is a working checklist for polishing the thesis after drafting.

Use this document together with:

- `README.md`
- `writing_style.md`
- the chapter-specific guideline for the affected chapter

---

## 1. Global Build Checks

- [ ] Compile the full thesis.
- [ ] Check unresolved references.
- [ ] Check duplicated labels.
- [ ] Check missing bibliography entries.
- [ ] Check overfull and underfull boxes.
- [ ] Check figure and table placement.
- [ ] Check that every figure and table is referenced in the text.
- [ ] Check that figures and tables appear in a reasonable order.
- [ ] Check that all abbreviations and symbols are defined before use.

---

## 2. Structural Cleanup

- [ ] Remove the duplicate English abstract inclusion in `thesis/main.tex` if it is still present.
- [ ] Replace or remove placeholder appendix content.
- [ ] Remove obsolete references to old guideline paths.
- [ ] Check that chapter input files are included only once.
- [ ] Check that renamed guideline files are reflected in `README.md`.

---

## 3. Repetition Cleanup

- [ ] Remove repeated definitions of direct feedthrough.
- [ ] Remove repeated definitions of strongly connected components.
- [ ] Remove repeated definitions of algebraic loops.
- [ ] Remove repeated definitions of execution order.
- [ ] Remove repeated definitions of rollback.
- [ ] Remove repeated definitions of dense time.
- [ ] Remove repeated explanations of event localization.
- [ ] Replace repeated explanations with cross-references.

---

## 4. Chapter 5 Reduction Pass

Perform this pass after Chapter 5 is fully drafted.

- [ ] Shorten verification tables that read like test coverage reports.
- [ ] Shorten captions that restate full paragraphs.
- [ ] Remove tables that only repeat class attributes or method names.
- [ ] Keep only figures that clarify data flow, control flow, or verification evidence.
- [ ] Check that each implementation section has a clear feature boundary.
- [ ] Check that each verification paragraph states setup, expected behavior, observed result, and conclusion.
- [ ] Remove implementation details that are not needed to understand the feature.

---

## 5. Chapter 6 Evidence Pass

- [ ] Check that Chapter 6 does not re-explain Chapter 5 mechanisms.
- [ ] Check that verification, validation, and benchmark claims are separated.
- [ ] Check that no physical validation is claimed without experimental data.
- [ ] Check that all scenario parameters needed for reproducibility are stated once.
- [ ] Check that case-study figures are thesis-ready and not notebook screenshots.
- [ ] Check that reported runtime values match the final benchmark notebook.

---

## 6. Chapter 7 Synthesis Pass

- [ ] Check that Chapter 7 answers the thesis objective.
- [ ] Check that Chapter 7 does not introduce new implementation details.
- [ ] Check that limitations are stated directly.
- [ ] Check that conclusions are supported by evidence from Chapters 5 and 6.
- [ ] Check that future work follows from the limitations.

---

## 7. Final Style Pass

- [ ] Split long sentences.
- [ ] Remove vague phrases.
- [ ] Remove unsupported intensifiers such as "robust" or "clearly" where not quantified.
- [ ] Check terminology against `glossary.md`.
- [ ] Check notation against `notation.md`.
- [ ] Check that captions do not duplicate the surrounding text.
- [ ] Check that tables are not data dumps.
- [ ] Check that cross-references are specific.

---

## Short Rule

Temporary cleanup tasks belong here.
Stable thesis concept, chapter roles, terminology, notation, and writing style
belong in their dedicated guideline documents.
