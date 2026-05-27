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
- [ ] Check abbreviation handling across the thesis.
- [ ] Define abbreviations in one central LaTeX file instead of manually repeating long forms.
- [ ] Use abbreviation macros consistently after the first definition.
- [ ] Verify that the list of abbreviations contains all relevant entries and no unused entries.
- [ ] Check that captions do not duplicate the surrounding text.
- [ ] Check that tables are not data dumps.
- [ ] Check that cross-references are specific.

---

## 8. Reproducibility and Software Archival

Pin the case study to an archived, citable software release before
submission. This is the availability statement an examiner expects for a
framework thesis and removes any need for code-listing appendices
(supersedes audit item LIT-03).

**Status (2026-05-23):** drafted, blocked on the Zenodo DOI. The DOI can
only be minted from the tagged submission release. `HEAD` is currently
`b29e887`, which is 34 commits past the `v0.1.5` tag, so no existing tag
points at the thesis-figure state — a fresh release is required.

- [ ] Cut a tagged submission release at the final figure-producing commit,
  e.g. `git tag -a v0.1.6 -m "Thesis submission"; git push origin v0.1.6`,
  then create the GitHub Release from that tag.
- [ ] Enable the Zenodo–GitHub integration **before** creating the release.
  zenodo.org → avatar → GitHub (`https://zenodo.org/account/settings/github/`)
  → toggle `FlorianFrech/SystemSimulation` ON; use "Sync now" if it is
  missing. Only releases made after the toggle is on are archived.
- [ ] Take the **version DOI** (not the concept DOI) from the Zenodo record
  so the cite pins the exact release.
- [ ] (Optional) Add a `CITATION.cff` at the repo root before releasing so
  Zenodo records the correct author, title, ORCID, and MIT license instead
  of guessing from GitHub metadata.
- [ ] Upgrade the `frech_syssimx_2026` entry in `references.bib` to a
  software release with version, commit, and DOI. The class sets
  `url=false, doi=true`, so the repo URL must stay inside `note`:

  ```bibtex
  @misc{frech_syssimx_2026,
    author = {Frech, Florian},
    title  = {{SysSimX}: A {Python} Framework for Heterogeneous Hybrid Co-Simulation},
    year   = {2026},
    % doi  = {10.5281/zenodo.XXXXXXX},  % uncomment after the Zenodo version DOI is minted
    note   = {Software release, version~0.1.6, Git commit~\texttt{b29e887}. Available: \url{https://github.com/FlorianFrech/SystemSimulation}},
  }
  ```
  Replace `0.1.6` / `b29e887` with the final submission tag and commit.

- [ ] Update the §6.4 reproducibility paragraph (`64_reference_model.tex:11`)
  to pin the version and commit:

  ```latex
  The case-study scenarios are reproducible from the archived \syssimx{} release~\cite{frech_syssimx_2026}.
  The reported results were produced with the framework at version~0.1.6, Git commit~\texttt{b29e887}.
  The scenario notebooks in the repository define the co-simulation configurations used for the figures in this chapter.
  The OpenModelica reference models belong to the controlled-pendulum Modelica package.
  The reference trajectories are exported once and loaded by the plotting scripts.
  This allows the thesis figures to be regenerated without recompiling the Modelica models.
  Reproducing the exported reference trajectories requires OpenModelica~\texttt{1.26.3}.
  ```

- [ ] Recompile (biber + pdflatex ×2) and confirm the DOI renders in the
  bibliography and the `frech_syssimx_2026` cite resolves.

---

## Short Rule

Temporary cleanup tasks belong here.
Stable thesis concept, chapter roles, terminology, notation, and writing style
belong in their dedicated guideline documents.

---

## Audit Findings (2026-05-19)

Cross-cutting items from the structural + cross-reference audit.
Chapter-specific items are tracked in each chapter guideline.

### High Priority

- [x] **Front matter — placeholder text.** Resolved (2026-05-26):
  abstract, Kurzfassung, acknowledgements, and affidavit are written;
  the funding-statement block with `<Organisation>` / `<project name>`
  placeholders has been removed from `other/affidavit.tex`.
- [ ] **Empty `\appendix` in `main.tex`.** Affidavit is now included via
  the frontmatter path. The `\appendix` call on line 115 of `main.tex`
  remains, but no appendix chapter follows. Decide: remove the call, or
  add intended appendix content. Either is acceptable for the supervisor
  draft; finalize before submission.

### Medium Priority

- [x] **Macro step notation `$H_k$` vs `$\Delta t$`.** Resolved
  (TN-02, audit log): `notation.md` now permits scalar `\Delta t` as a
  Chapter 5–6 macro-step abbreviation.
- [ ] **Acronym macro usage.** Defined acronyms that are never used via
  `\ac{}` in the chapters:
  - `IJCSA` — used as plain text throughout Chapter 5 (`55_structural_analysis.tex`,
    `56_algebraic_loops.tex`, `57_master_algorithms.tex`,
    `59_multi_component.tex`).
  - `PID`, `ADC`, `BLDC` — appear in Chapter 6 as plain text only.
  - `API` — appears in `41_architectural_overview.tex` as plain text only.

  For each, either use `\ac{...}` at first occurrence or remove the
  entry from `other/acronyms.tex`. Acronyms defined but unused at all:
  `CSV`, `DOF`, `PDE`, `SR`, `UR` — consider removing.
- [ ] **Caption short forms (`\caption[<short>]{<long>}`).**
  65 of 82 captions in chapter sources already use the short form.
  Remaining bare `\caption{...}` calls:
  - Chapter 3: four UR/SR tables and the equation-based tool table
    (`311_general_modeling.tex:15`, `312_heterogeneous.tex:15`,
    `313_simulation.tex:17`, `314_interaction.tex:12`,
    `32_tool_comparison.tex:45`).
  - Chapter 5: verification tables in `51_port_system.tex:35,95`,
    `52_co_sim_component.tex:150`, `531_fmu_component.tex:117`,
    `55_structural_analysis.tex:212`, `59_multi_component.tex:33`.
  - Chapter 6: `62_controlled_pendulum_system.tex:39`,
    `63_pendulum_models.tex:21`, `64_reference_model.tex:28`.
- [x] **Duplicate CoFMPy bib entry.** Resolved (2026-05-22): the
  `friedrich_cofmpy_2025-1` duplicate has been removed from
  `references.bib`; the DOI is preserved on the surviving entry.
- [ ] **Compile log inspection.** No log was provided to the audit.
  Compile `pdflatex` twice → `biber` → `pdflatex` twice and grep the
  `.log` for `Warning|Error|Overfull|Underfull|undefined`. Resolve
  unresolved refs, multiply-defined labels, and overfull boxes.

### Low Priority

- [ ] **`\input{...}` style inconsistency.**
  `2_theoretical_background.tex` mixes `.tex` and no-`.tex` extensions
  within one file (lines 13 and 17 use `.tex`; lines 14–16 do not).
  Chapters 5/6/7 use `.tex`; Chapters 1/3/4 use no extension. Pick one
  convention thesis-wide.
- [ ] **Zotero-imported bib keys.**
  Several entries use `noauthor_*_nodate` or `*_nodate` keys, indicating
  Zotero imports without proper author/date fields. Clean up where
  possible. See `ch3_requirements.md` audit findings for the list.
- [x] **Possible duplicate `gomes_co-simulation_2019` bib entry.**
  Resolved by using `gomes_co-simulation_2019` consistently.

---

## Status Check (2026-05-26)

Cross-check of the 2026-05-19 audit against the current PDF and source.
Most drafted drop-ins have been applied; this section records the state
on the day the draft was prepared for supervisor submission.

### Verified resolved since the 2026-05-19 audit

- Front-matter writing (abstract, Kurzfassung, acknowledgements,
  affidavit) and removal of the funding-statement placeholders.
- Drafted drop-ins VE-01–VE-04, TH-02, IC-02, IC-03, IC-04, ST-01,
  ST-02, TN-03, TN-04, TN-05 are present in the compiled PDF.
- LIT-01: §6.4 DASSL/CVODE sentences cite the OpenModelica User's Guide.
- PDF-01: abstract names SysSimX in paragraph 2.
- PDF-02 / FIG-01: 1.61× speedup reconciled across abstract,
  Kurzfassung, §6.5.3, Table 6.5, §7.1, §7.3, and Fig 6.6.
- PDF-07: affidavit page is present.
- FIG-02: Fig 5.9 figure label is `A = {Inner}`, matching the §5.6
  prose (verified 2026-05-26 against the compiled figure).
- NC-04 / ST-04: no duplicated Gauss–Seidel paragraph remains in
  `57_master_algorithms.tex` (verified 2026-05-26 — lines 153–154
  describe Gauss–Seidel; lines 156–158 describe IJCSA).
- Software-release bib entry `frech_syssimx_2026` carries version,
  Git commit, and repo URL.

### Open before sending the supervisor draft

- Decide on the empty `\appendix` in `main.tex:115` — remove the call
  or add intended appendix content.
- Final compile-log inspection (biber + `pdflatex` ×2, then grep the
  `.log` for `Warning|Error|Overfull|Underfull|undefined`).

### Optional polish (defer to post-feedback revision)

- PDF-03 (`\ac{UR}` / `\ac{SR}` sentence starts on p. 37).
- PDF-04 ("FEMs models" plural acronym before "models" in §7.1).
- PDF-05 ("Section 2" → "Notation section" on p. 10).
- PDF-08 (numbered but unreferenced equations in §2.4.3).
- FIG-03 (Fig 6.1 sub-label legibility at print size).
- Remaining acronym `\ac{}` consistency (IJCSA, PID, ADC, BLDC, API).
- Re-verify the listed caption short forms in Chapters 3, 5, and 6
  against the current PDF — most may already be done.
- §8 reproducibility paragraph expansion (drafted in §8 above; the
  current minimal wording already cites the upgraded software entry).

### Verdict

All HIGH-severity items are closed. The remaining MEDIUM-severity work
is contained to the empty `\appendix` call and the final compile-log
scan. The thesis is ready for supervisor draft submission once those
two items are addressed.
