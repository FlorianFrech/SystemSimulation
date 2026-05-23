# Chapter 4 Guideline: Framework Architecture

## Purpose

Chapter 4 describes the framework architecture of `syssimx`.
It explains the abstractions, their responsibilities, and how they fit
together to support heterogeneous hybrid co-simulation.
It is not a theory chapter and it is not an implementation chapter.

The chapter should answer:

- Which abstractions does `syssimx` introduce, and what does each own?
- How are components, ports, connections, systems, and algorithms related?
- Which design rationale justifies the chosen abstractions?

## Required Context Before Writing

Read these documents before drafting or polishing Chapter 4:

- `thesis/guideline/README.md`
- `thesis/guideline/thesis_concept.md`
- `thesis/guideline/writing_style.md`
- `thesis/guideline/glossary.md`
- `thesis/guideline/notation.md`

Chapter 4 is the first chapter where `component` and `System`
(`syssimx` class) are the primary terms.
Use `subsystem` only when contrasting with the physical/theoretical level.

## Chapter Role

Use Chapter 4 for:

- the component abstraction and its responsibilities
- the port and connection model
- the `System` abstraction as an owner of structural definition
- the algorithm interface and the separation between system and algorithm
- design rationale for the chosen abstractions

Do not use Chapter 4 for:

- mathematical definitions of co-simulation, feedthrough, or algebraic loops
  (these are theory and belong in Chapter 2)
- class diagrams or method signatures
  (these belong in Chapter 5 where they document the implementation)
- routine names, attribute names, data-structure choices, or graph-metadata
  fields
- verification or benchmark results

## Boundary Rule

Chapter 4 owns *what an abstraction is for*.
Chapter 5 owns *how it is realized*.
Chapter 2 owns *what concept it implements*.

If a paragraph re-states a theoretical definition or re-draws a result that
belongs to the implementation, replace it with a cross-reference.

Typical anti-patterns:

- "the framework derives a topologically sorted execution order, identifies
  direct-feedthrough dependencies, and detects algebraic loops" — this
  re-states Chapter 2 concepts. Replace with one sentence and a reference to
  Section 2.3.3.
- showing the *result* of structural analysis (zero-delay graph, condensed
  graph, execution order numbers) inside an architecture figure. Defer to
  the implementation figure.

## Figures

Architecture figures should show *what an abstraction owns* or *how
abstractions compose*, not what they compute.

Appropriate Chapter 4 figures:

- block diagrams of abstractions and their relationships
- ownership diagrams (which class holds which data)
- user-facing views of a system (components, ports, connections, feedthrough
  markers)

Avoid:

- class diagrams with method signatures (Chapter 5)
- sequence diagrams of method calls (Chapter 5)
- rendered results of structural analysis (Chapter 5)
- case-study plots (Chapter 6)

### System Figure (Section 4.2.2)

Role:
Show what a user-defined `syssimx` system looks like before any analysis is
performed.
The figure communicates the architectural content: a `System` collects
components, signal connections, event connections, and per-component
direct-feedthrough markers.

Required content (single panel):

- four labelled components (A, B, C, D) with their typed ports
- signal connections as solid arrows
- one event connection as a dashed arrow in a distinct color
- per-component direct-feedthrough paths as solid red arrows between
  internal port pairs
- a legend distinguishing signal connection, event connection, and direct
  feedthrough

What the figure must not show:

- the derived dependency graph, zero-delay graph, or condensed graph
- execution-order numbers, generation labels, or SCC shading
- attribute names such as `\texttt{graph}`, `\texttt{\_dag}`, or
  `\texttt{execution\_order}`
- a class diagram (the class-level overview of `System` is owned by
  Chapter 5)

Caption must state that the figure shows a user-defined system in `syssimx`.
The structural metadata derived from this definition must be referenced by
the implementation figure in Section 5.5, not duplicated here.

## Writing Style

Apply `writing_style.md` strictly.
Architecture prose should describe responsibilities and relations, not
mechanisms.

Preferred:

- "The `System` class collects components and connections and exposes the
  structural metadata derived during initialization."

Avoid:

- "The `System` class iterates over the registered components, builds a
  zero-delay graph, runs Tarjan's algorithm, and stores the resulting SCCs
  in `algebraic_loops`." (This belongs in Chapter 5.)

## Cross-References

Reference Chapter 2 for definitions.
Reference Chapter 5 for implementation details.
Do not preview Chapter 6.

## Revision Checklist

Before considering Chapter 4 polished, check:

- Each section describes one abstraction or one structural relation.
- No theoretical definition is re-introduced.
- No class-level or method-level detail is shown.
- Figures show ownership or composition, not derived results.
- Terminology follows `glossary.md`.
- The chapter does not duplicate the dependency-graph rendering of
  Chapter 2 or Chapter 5.

## Current Open Tasks

Use this list for the next Chapter 4 polishing pass.

### High Priority

All three high-priority items from the previous Chapter 4 pass are
resolved as of the 2026-05-19 structural audit.

- ~~System architecture figure in `422_system_connections.tex`~~
  **Resolved.** The current figure shows the user-defined system
  (components, typed ports, signal/event connections, feedthrough
  markers) without derived graphs or SCC shading.
- ~~System orchestration paragraph in `41_architectural_overview.tex`~~
  **Resolved.** Implementation-level dependency-graph wording has been
  removed; the paragraph now describes architectural responsibility and
  refers to Chapter 5 for the implementation.
- ~~API-level detail in `423_algorithms.tex`~~
  **Resolved.** Method signatures and the automatic-upgrade behavior
  have been removed. Algorithms are now presented as interchangeable
  orchestration strategies on a `System`.

### Medium Priority

- Re-check `421_cosimcomponent.tex` for method-level wording.
  The lifecycle, port interface, state handling, and optional capabilities are
  appropriate architectural content.
  Template-method and abstract-method details should stay short and serve only
  as design rationale.
- Replace "handler method" in `422_system_connections.tex` with an
  architectural term such as "event receiver" or "event-handling capability".
- Shorten the final transition in `424_multimodel.tex` and remove the double
  space before "the following chapter".

### Low Priority

- Remove semicolon-style caption wording.
  Prefer two short sentences over captions joined by semicolons.
- Check that all Chapter 4 figures state ownership or composition, not
  computed results.
- Verify terminology.
  Use `component`, `port`, `System`, `connection`, and `algorithm` as the main
  Chapter 4 terms.
  Use `subsystem` only when connecting the architecture back to the physical
  or theoretical level.

### Suggested Order

1. ~~Fix Section 4.2.2 and the system figure first.~~ Resolved.
2. ~~Clean the architectural overview.~~ Resolved.
3. ~~Polish the algorithm subsection.~~ Resolved.
4. Run a final style pass for captions, semicolons, double spaces, and
   cross-references.

---

## Audit Findings (2026-05-19)

Open items from the structural + cross-reference audit.

### Medium Priority

- **[Open] Macro step notation inconsistency.**
  `423_algorithms.tex:9` uses `$\Delta t$` for the macro step size, while
  Chapter 2 notation (`notation.md` and the Chapter 2 table) defines
  `$H_k = T_{k+1} - T_k$`. See the cross-cutting notation note added to
  Chapter 2 (dual-usage clarification) or change Chapter 4 to `H_k`.

### Low Priority

- **[Open] Short captions contain inline macros.**
  Figure captions in `421_cosimcomponent.tex`, `422_system_connections.tex`,
  and `424_multimodel.tex` use `\texttt{}` and `\syssimx{}` inside the
  short-form bracket. `writing_style.md` §10 recommends avoiding macros
  in the short form because they can mis-render in the LoF. Verify
  after the next full compile; replace with plain English noun phrases
  if the rendering is problematic.
- **[Open] Hard-coded vertical-spacing tweaks.**
  `\vspace{-1em}` and `\vspace{-0.5em}` appear around figures in
  `421_cosimcomponent.tex` and `422_system_connections.tex`. Re-tune
  after the final compile pass.
