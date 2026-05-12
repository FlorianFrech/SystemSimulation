# Claims and Evidence

This document maps thesis claims to the evidence that supports them.
It prevents unsupported claims and keeps verification, validation, and benchmark
wording consistent.

Use this document when drafting results, discussion, conclusions, abstracts, and
chapter transitions.

---

## 1. Claim Categories

| Category | Meaning |
|---|---|
| Implementation claim | A claim about what `syssimx` implements |
| Feature-level verification claim | A claim that an implementation feature behaves as expected in a focused scenario |
| Numerical verification claim | A claim that a co-simulation result agrees with an analytical or monolithic numerical reference |
| Workflow validation claim | A claim that the framework workflow is suitable for the intended case-study use |
| Benchmark claim | A claim about computational cost or runtime behavior |
| Limitation claim | A claim about what the thesis does not establish |

---

## 2. Main Thesis Claims

| Claim | Evidence location | Claim type |
|---|---|---|
| `syssimx` provides a common component abstraction for heterogeneous co-simulation backends. | Chapter 4 architecture and Chapter 5 component implementation | Implementation claim |
| The framework derives structural execution metadata from components, connections, and direct-feedthrough information. | Chapter 5 structural-analysis section and its verification scenario | Implementation and feature-level verification |
| The implemented continuous master algorithms execute coupled simulations according to the stored execution order. | Chapter 5 master-algorithm section and verification plots | Feature-level verification |
| The algebraic-loop implementation resolves SCC-local zero-delay dependencies. | Chapter 5 algebraic-loop section and IJCSA verification | Feature-level verification |
| The hybrid algorithm detects, localizes, and handles events with rollback-capable event sources. | Chapter 5 hybrid section and hybrid verification scenarios | Feature-level verification |
| The multi-model component keeps a fixed external interface while switching active internal models. | Chapter 5 multi-component section and switching verification | Feature-level verification |
| The baseline controlled-pendulum co-simulation converges toward the OpenModelica reference as the macro step size decreases. | Chapter 6 baseline scenario and convergence figure | Numerical verification |
| The multi-model contact scenario combines heterogeneous tools, hybrid events, PID reset, FEM contact, and runtime switching in one workflow. | Chapter 6 multi-model contact scenario | Workflow validation and numerical verification |
| Runtime switching reduces FEM computational cost in the selected contact benchmark. | Chapter 6 performance benchmark | Benchmark claim |
| The case study does not establish physical validation. | Chapter 6 objective and Chapter 7 limitations | Limitation claim |

---

## 3. Claim Boundary Rules

- Do not use "validated" for numerical agreement with OpenModelica.
  Use "verified against the monolithic OpenModelica reference".
- Do not use "physically validated" unless experimental data are used.
- Do not use benchmark results as correctness evidence.
- Do not generalize one case-study result to all hybrid co-simulation problems.
- State numerical values when claiming convergence, deviation, or speedup.
- State the tested scenario when a verification result is scenario-specific.

---

## 4. Evidence Needed Before Making a Claim

Before making a claim, identify at least one of the following evidence types.

- Requirement trace.
- Design description.
- Implementation section.
- Unit or feature-level test.
- Verification figure or table.
- Analytical reference.
- Monolithic numerical reference.
- Runtime benchmark.
- Literature reference.

If no evidence exists, either remove the claim or state it as a limitation or
future-work item.

---

## 5. Result-to-Discussion Mapping

Use this mapping to avoid repeating results in the discussion.

| Result in Chapter 6 | Discussion point in Chapter 7 |
|---|---|
| Baseline convergence toward OpenModelica | The co-simulation implementation is numerically consistent for the tested smooth closed-loop scenario |
| Contact trajectory follows the rigid-contact reference with model deviations | The framework workflow works, but contact comparison is limited by different contact models |
| Switched FEM run reduces runtime | Multi-fidelity switching can reduce cost, but the benefit depends on switching overhead and FEM problem size |
| Switched and full-FEM trajectories differ in the contact window | State projection at a mode switch cannot preserve the full FEM deformation history |

---

## Short Rule

Every strong thesis claim must point to evidence.
If the evidence is scenario-specific, the claim must be scenario-specific too.
