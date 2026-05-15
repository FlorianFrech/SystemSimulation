# Chapter 3 Guideline: Requirements and Tool Selection

## Purpose

Chapter 3 defines what the framework must do and which external tools support those capabilities.
It is the bridge between motivation (Chapter 1) and architecture/implementation (Chapters 4 and 5), and it is the anchor for evidence (Chapters 5 and 6).

The chapter must answer three questions:

- What does the user expect from the framework?
- What features must the framework implement to meet those expectations?
- Which external tools provide the modeling capabilities the framework relies on?

## Required Context Before Writing

Read these documents before drafting or revising Chapter 3:

- `thesis/guideline/README.md`
- `thesis/guideline/thesis_concept.md`
- `thesis/guideline/writing_style.md`
- `thesis/guideline/glossary.md`

Chapter 3 must follow the glossary strictly.
URs are user-facing and tool-agnostic.
SRs describe what the framework realizes.
Use `subsystem` and `simulation unit` in URs; `component` and `System` only in SRs.

## Chapter Role

Use Chapter 3 for:

- user requirements (UR) describing capabilities expected of the workflow
- system requirements (SR) describing framework features that realize each UR
- the mapping from requirements to evidence (verification and validation)
- justified selection of the external tools the framework integrates

Do not use Chapter 3 for:

- mathematical definitions or theory (these belong in Chapter 2)
- framework class names, method signatures, or data-structure choices (Chapter 5)
- implementation algorithms such as Tarjan SCC detection or active-output filtering
- case-study parameters, results, or benchmark figures (Chapter 6)
- broad surveys of every available tool in each domain

## Requirements Model

The thesis uses a two-level requirements model.

| Level | Purpose | Owner | Evidence | Chapter |
| --- | --- | --- | --- | --- |
| User requirement (UR) | What the user expects from the workflow | Tool-agnostic | Validated by case-study use | Chapter 6 |
| System requirement (SR) | What the framework must implement | `syssimx`-specific | Verified by isolated feature test | Chapter 5 |

State this mapping explicitly in the chapter introduction so that the reader knows where each requirement is discharged.
The mapping is what makes Chapter 3 load-bearing for the rest of the thesis.

### Validation versus Verification

Use the terms exactly as defined in [README.md](README.md) §5 and [writing_style.md](writing_style.md) §6:

- **Verification** of an SR: the implemented feature behaves as the SR requires.
  Evidence is a Chapter 5 verification section that references the SR ID.
- **Validation** of a UR: the integrated workflow supports the user expectation in a representative scenario.
  Evidence is the Chapter 6 case study.
- *Physical validation* is not in scope.
  Do not use "validate" to mean "compare against measured data".

## UR and SR Rules

### Identifier conventions

- Use `UR-NN` for user requirements (two-digit, zero-padded, e.g. `UR-09`).
- Use `SR-NN-MM` for system requirements derived from `UR-NN`.
- Identifiers are persistent.
  Do not renumber requirements once they are referenced in Chapters 5 or 6.

### Modal verb conventions

- `shall` marks a mandatory requirement.
- `should` marks a recommended requirement.
- `may` marks an optional requirement.
- Do not mix `shall` and `should` for items the chapter introduction calls mandatory.
- If interaction or visualization features are optional, say so explicitly in the category introduction and use `should` consistently for those URs and their SRs.

### Glossary rules inside requirements

- URs are tool-agnostic.
  Use `subsystem`, `subsystem model`, `simulation unit`, `connection`, `workflow`, `system model`.
  Do not write "common component abstraction" in a UR.
- SRs describe the `syssimx` framework.
  Use `component`, `port`, `System`, `algorithm`, `master algorithm`.
- Replacement examples for current URs:
  - "into the component-based workflow" → "into the coupled co-simulation workflow"
  - "common component abstraction" (in a UR) → "common simulation-unit abstraction"
  - "component-based modeling" (in a UR) → "subsystem-based modeling"

### UR-to-SR boundary

A UR states a *capability the user expects*.
An SR states a *framework feature the user does not see directly*.
Neither should preview implementation mechanisms.

Examples of correct wording:

- UR: "The workflow shall support runtime switching between alternative model representations of the same subsystem."
- SR: "The framework shall allow multiple interchangeable models to be registered under a unified component interface."

Examples of SRs that drift into implementation:

- "detect algebraic loops as strongly connected components" — SCC is a Chapter 5 choice.
  Prefer "detect circular instantaneous dependencies in the coupled structure".
- "build a dependency graph" — graph as a data structure is a Chapter 5 choice.
  Prefer "derive structural execution metadata from the registered connections and direct-feedthrough information".

The implementation chapter is then free to commit to graphs, SCC algorithms, and metadata field names without re-deriving the requirement.

### UR categories

The current four categories are appropriate and should be preserved:

1. General system modeling (UR-01 to UR-04)
2. Heterogeneous integration (UR-05 to UR-09)
3. Simulation (UR-10, UR-11)
4. Interaction (UR-12, UR-13)

Each category subsection should:

- give one or two sentences of category-level motivation;
- reference earlier chapters for any theoretical background (do not repeat Chapter 2);
- present the URs and their derived SRs in one `longtable`;
- end without restating the URs in prose.

### Table style

- All four UR/SR tables should use the same column widths, header style, and continued-caption macros for consistency across the chapter.
- Bold the UR rows; leave the SR rows in plain text so the visual hierarchy follows the requirements hierarchy.
- Do not embed itemize lists inside table cells.

## Tool Selection Rules

### Scope of the comparison

§3.2 is not a survey of every modeling environment in each domain.
State this explicitly in the section introduction and keep it as a working rule.

For each tool decision, the structure should be:

1. **Capability requirements** for this domain, traced to the URs of §3.1.
2. **Selected tool** with a one-paragraph justification.
3. **Alternatives considered** with a brief reason for rejection.
4. **Limitations of the selected tool** stated directly.

### Stylistic consistency

All tool subsections must use the same level of rigor.
Either every subsection has a small comparison table or none does — do not mix.

Recommended approach for this thesis (low cost, high consistency): keep the equation-based comparison table and add an analogous compact table (3 to 4 rows, 3 to 4 columns) for the musculoskeletal and finite element subsections.
Each table should list the selected tool plus the two alternatives that were actually considered.

If a systematic comparison is not feasible (as for musculoskeletal tools), state that limitation directly in one sentence — do not paper over it with rhetorical filler.

### Required coverage

The tool-selection section must justify every external tool the framework depends on, not only the modeling tools.
The current minimum set is:

- Modelica with the OpenModelica toolchain (equation-based modeling)
- OpenSim (musculoskeletal modeling)
- Netgen/NGSolve (finite element modeling)
- fmpy (Python loader for FMI 2.0 Co-Simulation FMUs)

`fmpy` is currently missing from §3.2 and must be added.
The justification is short: FMUs exported from OpenModelica must be loaded and executed from Python, and the framework needs a maintained library that exposes the FMI 2.0 Co-Simulation interface.

### Tool-selection summary

End §3.2 with a single-sentence or single-row-table summary that lists the four tools and the requirement category each one addresses.
This is the table the reader will scan when checking the toolchain.

## Cross-Referencing Rules

Chapter 3 should be cited from many places.
Make those references easy to write.

- Every UR and SR should have a `\label{...}` that can be referenced from Chapters 5 and 6.
  Suggested convention: `req:UR-09`, `req:SR-09-03`.
- Chapter 5 verification sections should cite the relevant `SR-` IDs (this is already the practice in [55_structural_analysis.tex](../chapters/5_implementation/55_structural_analysis.tex)).
- Chapter 6 case-study sections should cite the relevant `UR-` IDs to make the validation argument explicit.
- The chapter introduction of Chapter 3 should forward-reference Chapter 5 and Chapter 6 once, to make the evidence chain visible up front.

## Writing Style

Apply [writing_style.md](writing_style.md) strictly.
For Chapter 3 in particular:

- Avoid "stakeholder discussions" without naming who.
  Either identify the stakeholder context or remove the phrase.
- Avoid filler such as "comprehensive analysis", "rigorous comparison", "carefully selected".
  State the criterion, the candidates, and the decision.
- Avoid "the proposed methodology" — write "the framework" or `\syssimx{}`.
- Avoid the "not A; instead B" pattern (per the recent rule in [writing_style.md](writing_style.md) §2).

Preferred:

```text
The selected tool had to support FMI 2.0 Co-Simulation export so that
exported simulation units can be loaded from Python.
OpenModelica satisfies this and is open source.
Dymola was rejected because it is commercial.
```

Avoid:

```text
A comprehensive analysis was carried out in order to identify the most
suitable tool capable of supporting the proposed methodology of this
thesis.
```

## Figures and Tables

Figures are usually not needed in Chapter 3.
The requirement tables and the tool-comparison tables carry the structure.

If a figure is added, it should be:

- a single category map (URs grouped by category) used only if the chapter benefits from a visual overview, or
- a requirements-to-evidence diagram showing the UR/SR → Chapter 5/Chapter 6 chain.

Do not add architecture or class diagrams here.

## Common Chapter 3 Risks

| Risk | Correction |
| --- | --- |
| URs use `component` and read like framework specs | Reword URs with `simulation unit`, `subsystem`, `workflow` |
| SRs preview Chapter 5 mechanisms (SCC, graphs, fields) | Restate the SR in terms of the required capability, not the algorithm |
| Tool subsections use inconsistent comparison style | Either every subsection has a small table or none does |
| `shall`/`should` mixed inside a category labelled mandatory | Use one modal consistently or state explicitly which URs are recommended |
| fmpy or other infrastructure tools missing from §3.2 | Add a short justification subsection |
| No bridge between requirements and Chapter 5 / Chapter 6 evidence | Add the UR-validation / SR-verification mapping in the chapter intro |

## Revision Checklist

Before considering Chapter 3 polished, check:

- Every UR uses tool-agnostic vocabulary (`simulation unit`, `subsystem`, `workflow`).
- Every SR can be verified in isolation by a Chapter 5 verification section.
- Every UR can be validated by the case study in Chapter 6.
- All four UR/SR tables use the same column widths, headers, and continued-caption macros.
- The chapter intro states the UR-validates-via-Chapter-6 and SR-verifies-via-Chapter-5 mapping.
- §3.2 covers Modelica/OpenModelica, OpenSim, Netgen/NGSolve, and fmpy.
- Each tool subsection follows the same structure (capability, choice, alternatives, limitations).
- `shall` versus `should` is consistent with the mandatory-versus-recommended classification stated in the chapter intro.
- No UR or SR references an implementation field name from Chapter 5.
- No tool subsection contains marketing language or "comprehensive analysis" filler.

## Open Tasks

Items pending before Chapter 3 can be considered finalized.

- Add bib entries and `\cite{...}` calls for the alternatives named in §3.2.2 (Musculoskeletal Modeling):
  - **AnyBody Modeling System**: suggested reference `damsgaard_analysis_2006` (Damsgaard et al., 2006) or the AnyBody Technology corporate reference.
  - **MuJoCo**: suggested reference `todorov_mujoco_2012` (Todorov, Erez, Tassa, 2012).
  - Add citations at first mention in the *Alternatives considered* paragraph and in `tab:musc_tool_comparison`.
- Fix the CoFMPy bib key used in §3.2.2:
  - Current key: `friedrich_cofmupy_nodate` (contains a spelling error and `_nodate` suffix).
  - Correct key: `friedrich_cofmpy_2025`.
  - Add the DOI `10.1109/MODELS-C68889.2025.00027` and the year 2025 to the bib entry.
  - Update all uses across `12_state_of_the_art.tex`, `32_tool_comparison.tex`, and the planned §7.1 paragraph.
  - The framework name in prose is *CoFMPy* (no `u`); fix the typo *CoFmuPy* at [12_state_of_the_art.tex:83](../chapters/1_introduction/12_state_of_the_art.tex#L83).

## CoFMPy Note for §3.2.2

CoFMPy is a Python-native co-simulation framework, not only an FMI loader.
§3.2.2 already lists CoFMPy as an alternative for the FMU import role and rejects it because its scope (coordinator, communication, storage, Python FMU proxy for non-FMU components) is broader than the importer role required there.
Keep this framing.
Do not turn the §3.2.2 alternatives paragraph into a comparative discussion of CoFMPy's framework features.
The framework-level contribution boundary against CoFMPy belongs in Chapter 7.

## Short Rule

Chapter 3 should say what the framework must do, what features realize each capability, and which external tools the framework depends on.
Everything else belongs in another chapter.
