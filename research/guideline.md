# Thesis Writing Guideline

This document is the authoritative working guideline for drafting and revising the thesis, with special focus on Chapter 2.

It must be used together with:

- `research/theory/notation.md`
- `research/theory/glossary.md`

If a future draft conflicts with this document, `notation.md`, or `glossary.md`, the draft should be revised rather than the conflict ignored.

---

# 1. General Requirements for the Thesis

## 1.1 Core principle

Every chapter must have a clear role.
Do not let one chapter absorb the function of another.

## 1.2 Chapter roles

- Chapter 1 introduces motivation, problem context, research gap, contributions, and related work orientation.
- Chapter 2 provides the minimum complete theoretical basis needed to understand the framework, implementation, and case study.
- Chapter 3 defines requirements and tool choices.
- Chapter 4 explains the framework architecture and abstractions.
- Chapter 5 explains how the framework is implemented and verified in detail.
- Chapter 6 applies the framework in the case study.
- Chapter 7 discusses limitations, conclusions, and outlook.

## 1.3 Global writing rules

- Do not repeat the motivation from Chapter 1 in later chapters.
- Do not include theory that is never used later in the thesis.
- Do not include implementation detail in theory chapters unless a short preview is necessary for orientation.
- Do not include framework-specific software terminology in theory chapters when a framework-neutral term exists.
- Keep all cross-references valid and specific.
- Keep notation consistent across chapters.
- Keep terminology consistent across chapters.
- Use only figures that directly improve understanding.
- Remove or rewrite any figure whose caption and visual logic no longer match the text.

## 1.4 Cross-reference and consistency rules

- Every chapter reference must point to an existing label.
- Every globally defined symbol should either be used consistently or be removed from the notation table.
- If a symbol is introduced globally, local sections must not silently redefine it with a different meaning.
- If a concept is described in theory and implemented later, the theory chapter should explain what it means, while the implementation chapter should explain exactly how it is realized.

---

# 2. General Requirements for Chapter 2

## 2.1 Role of Chapter 2

Chapter 2 should provide the minimum complete theoretical basis needed for the reader to:

- understand the framework architecture,
- understand the component abstractions,
- understand the terminology of continuous-time, hybrid, and co-simulation models,
- follow the implementation and case study without conceptual gaps.

## 2.2 What Chapter 2 must not do

Chapter 2 must not:

- become a detailed algorithm chapter,
- become a second state-of-the-art chapter,
- include code-level or API-level implementation detail,
- derive framework-specific procedures that belong in Chapter 5,
- overload the reader with formalism that is not required later.

## 2.3 Standard subsection pattern for Chapter 2

Each theory subsection should follow this pattern as far as practical:

1. short prose bridge,
2. notation block or notation extension,
3. core concept explanation,
4. minimal example or figure,
5. boundary sentence that defers technical realization to Chapter 5.

## 2.4 Theory versus implementation boundary

The theory chapter should explain:

- what a concept is,
- why it matters,
- what problem it solves,
- what information it produces,
- and what later chapter realizes it concretely.

The implementation chapter should explain:

- exact data structures,
- exact graph construction,
- exact iteration schemes,
- exact solver logic,
- exact ordering logic,
- and verification of the realized behavior.

---

# 3. Notation and Terminology Rules

## 3.1 Binding notation rules

The notation rules in `research/theory/notation.md` are binding.
This guideline document must not duplicate or redefine concrete symbol choices.
All symbol definitions, reserved symbols, canonical forms, and notation-to-implementation mappings belong exclusively in `notation.md`.

## 3.2 Binding terminology rules

The terminology rules in `research/theory/glossary.md` are binding.
In particular:

- use *subsystem* for the theoretical constituent of the modeled system,
- use *simulation unit* for the framework-neutral executable co-simulation participant,
- use *component* only for the concrete `syssimx` realization,
- use *master algorithm* for orchestration logic,
- use *System* only when referring to the concrete `\texttt{System}` class.

## 3.3 Immediate consistency rule

Before adding or revising content, check:

- whether the symbols already exist in Chapter 2 notation,
- whether the terms match the glossary hierarchy,
- whether the notation in equations matches the notation table,
- whether the prose is theory-level or implementation-level.

---

# 4. Chapter 2 Co-Simulation Section: Current Evaluation

This section records the currently valid review outcome for
`thesis/chapters/2_theoretical_background/23_cosimulation_principles.tex`.

## 4.1 What is already appropriate

The following subsection topics are appropriate for Chapter 2:

- From Monolithic Simulation to Co-Simulation
- Mathematical Formulation of Co-Simulation
- Structural Analysis of a Co-Simulation Scenario
- Co-Simulation Execution Strategies
- Algebraic Loops in Co-Simulation
- Hybrid Co-Simulation
- The Functional Mock-up Interface (FMI)

The issue is not the presence of these subsections.
The issue is the depth and boundary control inside some of them.

## 4.2 Main remaining problems

- The hybrid co-simulation subsection is still too algorithmic.
- The execution-order paragraph is inconsistent with the revised structural-analysis logic.
- The co-simulation section still lacks a short conceptual discussion of coupled-system initialization.
- The notation table and the co-simulation section are not fully harmonized.
- At least one forward reference is broken.
- The current dependency-graph figure logic is still not suitable for Chapter 2.

---

# 5. Concrete Requirements for Section 2.3 Co-Simulation

## 5.1 What Section 2.3 must achieve

The co-simulation section must explain just enough for the reader to understand:

- why simulation units exchange data only at communication points,
- why inputs must be approximated between communication points,
- why direct feedthrough matters for execution ordering,
- why algebraic loops arise from instantaneous cyclic dependencies,
- why coupled initialization is nontrivial,
- why hybrid co-simulation is harder than purely continuous co-simulation,
- why FMI matters as the standard interface layer.

## 5.2 What Section 2.3 must not do

The co-simulation section must not yet derive:

- detailed graph construction logic,
- active-output filtering details,
- SCC detection procedures,
- Tarjan or implementation-specific graph algorithms,
- the exact local or global IJCSA realization,
- Jacobian assembly details,
- convergence management details,
- event localization by bisection in procedural detail,
- rollback realization details,
- implementation-specific initialization sequences.

---

# 6. Concrete Revision Tasks for the Co-Simulation Section

### Structural-analysis figure for Chapter 2

The preferred figure for the structural-analysis subsection is a three-panel conceptual illustration:

- Panel 1: port connections and direct-feedthrough hints at simulation-unit level
- Panel 2: zero-delay dependency graph with one highlighted SCC
- Panel 3: condensed acyclic graph with the resulting generations

This figure should communicate the following story:

- the source information is the set of port connections together with direct-feedthrough information,
- this information induces a zero-delay dependency graph between simulation units,
- a directed cycle in that graph is one algebraic loop, i.e. one SCC,
- collapsing each SCC to one node yields an acyclic condensed graph,
- and the generations are defined only on that condensed graph.

The panels should therefore obey the following rules:

- Panel 1 may show ports and port-level arrows, but the explanation in the text must remain at simulation-unit level.
- Panel 2 should show the zero-delay graph only, not the full connection graph.
- Panel 2 should label the loop as one SCC, for example `SCC \{B,C\}` or `Algebraic Loop \{B,C\}`.
- Panel 3 should show the actual condensed graph, e.g. $A \rightarrow \{B,C\} \rightarrow D$, rather than the raw cyclic graph with generation braces added afterward.
- Generation labels such as `Gen 0`, `Gen 1`, `Gen 2` belong only to Panel 3.

The figure caption should explicitly state that the figure is a conceptual illustration of the structural-analysis principle.
It must not claim that the figure is an exact rendering of the \syssimx{} implementation.

### Important distinction: theory figure versus implementation

The Chapter 2 figure may use a clean conceptual example even when it omits implementation-specific refinements.
However, the text must not silently blur the difference between the theory-level picture and the actual realization in Chapter 5.

In particular, the implementation in \syssimx{} differs from the pure theory picture in the following ways:

- the zero-delay graph is constructed from port connections and direct-feedthrough data, but only for destination inputs that influence an output actually used downstream,
- this active-output filter can remove sink-like nodes from the implementation-level zero-delay graph even if a simple conceptual figure still shows them,
- the implementation computes generations on the condensed graph and then expands them back to component names,
- and delayed producers are post-processed as an implementation-specific scheduling heuristic.

Therefore:

- Chapter 2 may use a conceptually clean three-panel figure with nodes such as $A$, $B$, $C$, and $D$ to explain the principle,
- but Chapter 2 should describe it as a conceptual example,
- while Chapter 5 should explain the active-output filter, delayed-producer handling, and any resulting deviations from the simple theory figure.

---

# 7. Concrete Status of the Current Draft

## 7.1 Parts that are already in good shape

- The monolithic / model-exchange / co-simulation distinction is appropriate.
- The communication-grid explanation is appropriate.
- The structural-analysis subsection is much better aligned than before.
- The algebraic-loop subsection is now closer to the correct Chapter 2 level.
- The co-simulation section now mostly respects the subsystem / simulation unit / component terminology split.

## 7.2 Parts that still require revision

- Hybrid co-simulation is still too procedural.
- Execution order still uses wording that belongs to the old graph interpretation.
- Coupled initialization is still missing as an explicit conceptual issue.
- Notation is still not fully harmonized.
- The dependency-graph figure still encodes the old conceptual mistake.
- The FMI subsection still contains a broken forward reference.

---

# 8. Mandatory Checklist Before Generating New Thesis Content

Before drafting or revising any theory text, check all of the following:

- [ ] Does this content belong in this chapter, or in another chapter?
- [ ] Does the terminology match `glossary.md`?
- [ ] Does the notation match `notation.md` and the Chapter 2 notation table?
- [ ] Is the text conceptual rather than implementation-specific?
- [ ] Is every equation needed later in the thesis?
- [ ] Is every figure conceptually correct and actually useful?
- [ ] Does the subsection end with a clear boundary sentence if technical detail is deferred?
- [ ] Are all references and labels valid?
- [ ] Does the text avoid repeating Chapter 1 motivation?
- [ ] Does the text avoid becoming a mini-implementation chapter?

---

# 9. Working Rule for Future Drafting

Use this rule whenever generating thesis content:

> Write only the amount of theory required for the reader to understand the next architectural, implementation, or case-study chapter, and defer all framework-specific realization details to the chapter that owns them.
