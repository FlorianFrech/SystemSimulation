# Chapter 5 — FMUComponent Section Guideline

This document defines the scope, structure, and boundary rules for the
FMUComponent subsection of Chapter 5 (Feature Implementation and
Verification). It must be read together with:

- `research/guideline.md` (global thesis guideline)
- `research/theory/glossary.md` (terminology)
- `research/theory/notation.md` (notation)
- `research/theory/modeling_approaches.md` (equation-based modeling paradigm)

If a draft conflicts with these documents, the draft is revised.

---

## 1. Role of the Section

The FMUComponent section describes the realization of the first backend
wrapper in `syssimx`: the bridge between FMI 2.0 Co-Simulation FMUs and
the `CoSimComponent` interface defined in
Section~\ref{sec:impl_component_interface}.

The reader must be able to understand, after reading this section:

- which FMI features are supported and which are explicitly out of scope,
- how an FMU's interface (declared in `modelDescription.xml`) is mapped
  onto the port system and component contract of `syssimx`,
- how the FMI 2.0 Co-Simulation lifecycle (instantiate, initialize, step,
  reset) is realized through the primitive and hook operations of
  `CoSimComponent`,
- how direct feedthrough is obtained automatically from the FMU model
  structure,
- how the wrapper is verified in isolation from any concrete FMU.

The section must stay at the level of *implementation description*, not
API reference. It is not a user tutorial and not a replacement for the
fmpy documentation.

---

## 2. Scope Boundaries

### 2.1 In scope

- FMI 2.0 Co-Simulation mode only (the version actually supported by the
  wrapper).
- Port derivation from the FMU model description.
- Unit handling delegated to the port system (already covered in
  Section~\ref{sec:impl_port_system}).
- Direct-feedthrough extraction from the `ModelStructure` element.
- Value-reference caching per FMI base type.
- Lifecycle mapping to `CoSimComponent` primitive and hook methods.
- State serialization via the `syssimx` `get_state()` / `set_state()`
  interface, with an explicit distinction from native FMI FMU-state
  snapshotting.
- Zero-step output evaluation via `evaluate_outputs()` for algebraic-loop
  resolution.

### 2.2 Out of scope

- FMI 1.0 and FMI 3.0 (not implemented).
- FMI Model Exchange mode (Section~\ref{sec:cosim_fmi} already explains
  why the framework uses Co-Simulation mode).
- FMU export or generation. The section assumes a valid FMU binary is
  supplied by the user.
- Reproducing the FMI 2.0 specification. Concepts such as
  `fmi2EnterInitializationMode` or `fmi2DoStep` may be referenced by name
  but must not be re-derived.
- Complete API documentation of `fmpy`. Only the calls actually used by
  the wrapper are mentioned.
- Source-code listings. Algorithm behavior is conveyed through prose,
  tables, or small pseudo-code blocks when necessary — not through full
  Python code.

---

## 3. Required Subsection Pattern

The section follows the Chapter 5 template already established by
Sections~\ref{sec:impl_port_system} and
\ref{sec:impl_component_interface}:

1. **Motivation.** One short paragraph naming the requirement that
   motivates the feature (SR-03-01 or equivalent) and stating the role
   of the wrapper.
2. **Background bridge.** At most one short paragraph that recalls the
   relevant theory from Chapter 2 (FMI 2.0 Co-Simulation, equation-based
   modeling export). No re-derivation of the standard.
3. **Architecture / Mapping.** How FMI artefacts map onto the
   `CoSimComponent` abstractions. This is the conceptual heart of the
   section.
4. **Lifecycle Realization.** How the primitive operations and hook
   operations of `CoSimComponent` are implemented on top of the fmpy
   `FMU2Slave` interface.
5. **State Access and Rollback Boundary.** How `get_state()` /
   `set_state()` expose readable FMU variable dictionaries, and why this
   is distinct from native FMI rollback via internal FMU state snapshots.
6. **Verification.** A representative verification setup and a summary
   table of verified properties.

Each of items 3–6 should be its own `\paragraph{...}` or `\subsection{...}`,
consistent with the style of the surrounding sections.

---

## 4. Mapping Strategy (Core Content)

The section must make the following mapping explicit, ideally in a
table:

| FMI artefact | `syssimx` abstraction |
|---|---|
| `modelDescription.xml` | Source of ports, parameters, direct feedthrough |
| `ScalarVariable` with causality `input` / `output` | `PortSpec` with direction `in` / `out` |
| `ScalarVariable._python_type` | `PortType` enumeration value |
| `ScalarVariable.unit` (FMI-style string) | Pint-compatible unit on `PortSpec` |
| `ScalarVariable` with causality `parameter` | Entry in `parameters` dictionary |
| `ModelStructure/Outputs` dependencies | `direct_feedthrough` mapping |
| `valueReference` | Cached per type in `_vrs_in_*` / `_vrs_out_*` |
| `fmi2SetupExperiment` + init-mode block | Body of `_initialize_component()` |
| `fmi2DoStep` | Body of `_do_step_internal()` |
| `fmi2GetReal/Integer/Boolean/String` | Body of `_update_output_states()` |
| FMI variables readable through getter calls | Dictionary returned by `get_state()` |

This table is the single most important artefact of the section. It
makes the mapping strategy auditable without reading the source.

---

## 5. Lifecycle Realization

### 5.1 Initialization

The section must explain the six-step initialization sequence realized
in `_initialize_component()`:

1. Extract FMU archive.
2. Instantiate `FMU2Slave` with model identifier and GUID.
3. Call `setupExperiment(startTime=t0)`.
4. Enter initialization mode.
5. Apply parameter and input start values (batched per FMI base type).
6. Exit initialization mode.

The batched application per type (real/int/bool/string) is an
implementation detail worth mentioning because it avoids per-variable
FMI overhead. Use one sentence, not a detailed derivation.

### 5.2 Stepping

`_do_step_internal(t, dt)` reduces to a single `doStep` call. This is
the simplest case of the template method pattern in the whole framework
and should be stated that way.

### 5.3 Output Refresh

`_update_output_states()` performs batched `getReal`/`getInteger`/
`getBoolean`/`getString` calls using cached value references, and writes
the results back into the PortStates. For REAL outputs, the declared
unit is attached to produce a Pint quantity.

### 5.4 Zero-Step Evaluation

`evaluate_outputs()` applies inputs without advancing history, issues a
`doStep` with `dt = 0`, and reads outputs. This is the mechanism that
allows the framework to evaluate a feedthrough output for a trial input
during algebraic-loop resolution, as introduced in
Section~\ref{sec:theory_direct_feedthrough}.

### 5.5 State Access and Rollback Boundary

The thesis section must describe the following distinction clearly:

- `reset()` releases the FMU instance. The component can be
  reinitialized for a new run.
- `get_state()` / `set_state()` in `syssimx` are not the same concept as
  the native FMI `getFMUState()` / `setFMUState()` operations.
- The `syssimx` methods expose a readable dictionary of FMU variables
  and their current values. This format is intended for state
  inspection, state transfer, and re-initialization.
- Native FMI state operations capture and restore the internal FMU
  solver state as an opaque backend object.

The generic `FMUComponent` does not natively implement
`snapshot_state()` / `restore_state()` and therefore does not provide
generic rollback support for the hybrid algorithm.
Rollback is implemented only by specialized subclasses when the concrete
FMU and solver support it.
For the controlled-pendulum FMU used in the case study, the Euler-based
variant uses native FMI state snapshotting, whereas the CVODE-based
variant is restored by reinitializing the FMU with updated initial
conditions.

The method `soft_reset()` currently exists in the source code but is an
implementation artefact and must not be documented in the thesis. It is
not part of the conceptual design of the FMU wrapper and is not used by
the hybrid algorithm.

---

## 6. Direct Feedthrough

The wrapper does not perform numerical perturbation to detect direct
feedthrough. It reads the dependencies declared in
`modelDescription.xml > ModelStructure > Outputs`. This is an important
point: for FMUs, feedthrough information is authoritative and does not
need to be discovered at runtime.

This must be contrasted explicitly with the default mechanism in
`CoSimComponent._detect_direct_feedthrough()`, which does perform
output perturbation (Section~\ref{sec:impl_component_interface}).

---

## 7. Verification

The verification subsection should demonstrate:

- Construction of an `FMUComponent` from a small test FMU produces the
  expected port specifications (names, types, directions, units).
- Direct feedthrough extracted from model structure matches the FMU's
  declared dependencies.
- A full initialize–step–reset cycle leaves the component in a reusable
  state.
- `evaluate_outputs()` with `dt = 0` returns outputs consistent with the
  FMU's algebraic output equation on a trial input.
- Parameter application through `set_parameters()` is reflected in
  subsequent outputs.
- Unit-string normalization handles the OpenModelica compact form.
- `get_state()` returns a readable dictionary of non-`fixed`,
  non-`local` FMU variables and their current values.
- `set_state()` reinitializes the FMU from such a readable dictionary
  by applying serialized parameters and inputs.
- Generic `FMUComponent` rollback is explicitly not claimed; rollback is
  discussed only for specialized hybrid FMU subclasses where implemented.

Results are summarized in one table matching the style of
Tables~\ref{tab:port_verification} and
\ref{tab:cosimcomp_verification}.

A full integration test with a real-world FMU is deferred to
Chapter~\ref{chap:case_study}.

---

## 8. Figures

At least one figure is expected: a UML class or block diagram showing
the relation between

- `CoSimComponent` (abstract base),
- `FMUComponent` (concrete subclass),
- `fmpy.FMU2Slave` (external dependency),
- `PortSpec` / `PortState` (interface representation).

A second optional figure is a sequence diagram of the initialization
block, showing the fmpy calls issued between
`enterInitializationMode` and `exitInitializationMode`. It is optional
because the corresponding text should already be unambiguous.

No figure is required for the step operation: it is a single call.

---

## 9. Terminology Discipline

- The wrapped artefact is an **FMU** (Functional Mock-up Unit), never a
  "model" in isolation.
- The `syssimx` object is a **component**, never a "simulation unit" in
  this chapter (Chapter 5 is framework-specific).
- The FMI 2.0 Co-Simulation mode must be named in full on first use.
- `fmpy` is a library, not a framework.
- Write `\texttt{FMUComponent}`, `\texttt{CoSimComponent}`,
  `\texttt{PortSpec}`, `\texttt{PortState}`, `\texttt{FMU2Slave}` in
  typewriter font throughout.

---

## 10. Mandatory Checklist

Before the FMUComponent section is considered ready:

- [ ] Does every FMI concept used in the text appear in Chapter 2 or is
      briefly introduced here without re-deriving the standard?
- [ ] Is the mapping table present and complete?
- [ ] Is every lifecycle method of `CoSimComponent` either realized
      concretely or explicitly noted as inherited default?
- [ ] Is the contrast with perturbation-based feedthrough detection
      stated?
- [ ] Does the verification table follow the style of the existing ones
      in Sections~\ref{sec:impl_port_system} and
      \ref{sec:impl_component_interface}?
- [ ] Are `\syssimx{}`, `\texttt{...}`, and `\ref{...}` usages consistent
      with the rest of Chapter 5?
- [ ] Are forward references to Sections~\ref{sec:impl_hybrid} and the
      case study Chapter~\ref{chap:case_study} valid?
- [ ] Are no source-code listings included?
