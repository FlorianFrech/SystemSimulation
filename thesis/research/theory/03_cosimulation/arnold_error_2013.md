# Arnold, Clauss & Schierz (2013): Error Analysis and Error Estimates for Co-Simulation in FMI 2.0

**Reference:** Arnold, M., Clauss, C., & Schierz, T. (2013). *Error analysis and error estimates for co-simulation in FMI for Model Exchange and Co-Simulation V2.0*. *Archive of Mechanical Engineering*, 60(1), 75–94. DOI: `10.2478/meceng-2013-0005`.

## 1. Core Motivation

Arnold, Clauss, and Schierz analyze the numerical error behavior of **co-simulation** in the context of **FMI for Model Exchange and Co-Simulation v2.0**. The paper starts from the observation that complex multi-disciplinary systems are usually built from subsystems, often modeled in different mono-disciplinary simulation tools. FMI provides a standardized interface for importing/exporting model components and for co-simulation interfaces in nonlinear system dynamics. 

The central numerical issue is that co-simulation exchanges subsystem inputs and outputs only at discrete **communication points**. Between two communication points, the subsystem inputs are unknown and must be approximated, typically by polynomial extrapolation or interpolation. This approximation introduces additional error terms and may cause numerical instability. FMI 2.0 addresses these issues by supporting higher-order input approximation, communication step size control with step rejection, and stabilization techniques. 

The paper focuses specifically on **reliable local error estimation** for **communication step size control** in FMI-compatible co-simulation environments. 

---

## 2. Co-Simulation Model Structure

The paper considers a block-oriented representation of coupled systems. Each subsystem $j$ is described by state, input, and output variables:

$$
\dot{x}_j(t) = f_j(x_j(t), u_j(t), u_{\mathrm{ex}}(t)),
$$

$$
y_j(t) = g_j(x_j(t), u_j(t)).
$$

The subsystems are coupled through input-output relations:

$$
u_j(t) = c_j\bigl(y_1(t), \ldots, y_{j-1}(t), y_{j+1}(t), \ldots, y_r(t)\bigr).
$$

In compact form, the coupled system is written as

$$
\dot{x}(t) = f(x(t), u(t), u_{\mathrm{ex}}(t)),
$$

$$
y(t) = g(x(t), u(t)),
\qquad
u(t) = c(y(t)).
$$

This formulation represents the coupled system as a DAE in the variables $x$, $y$, and $u$. If no subsystem has direct feed-through, i.e.

$$
y_j(t) = g_j(x_j(t)),
\qquad
\frac{\partial g_j}{\partial u_j} \equiv 0,
$$

the system can be reduced to an ODE-like structure. This case is numerically more favorable, but it excludes important couplings such as force-displacement couplings between mechanical systems. 

---

## 3. Direct Feed-Through and Algebraic Loops

A major part of the paper is the structural analysis of direct feed-through paths. If an output depends directly on an input, and that input is computed from other outputs, closed dependency chains can arise. These closed paths correspond to **algebraic loops**.

The paper formulates the interface problem as nonlinear equations in the input variables:

$$
u = c(g(x,u)).
$$

A structural feed-through path exists from one input component to another if the corresponding derivative of $c(g(x,u))$ with respect to $u$ is structurally nonzero. The authors represent these dependencies by a directed graph $G$, where vertices correspond to input components and directed edges represent structural feed-through paths. A cycle in this graph represents a closed feed-through path, i.e. an algebraic loop. 

To exclude algebraic loops, the paper assumes that the directed graph $G$ is **acyclic**. This implies that the adjacency matrix $A(G)$ is nilpotent:

$$
(A(G))^M = 0
$$

for some finite (M). The adjacency matrix therefore represents the structural sparsity pattern of the interface Jacobian

$$
\frac{\partial c(g(x,u))}{\partial u}.
$$

This graph-based criterion is directly relevant for co-simulation master algorithms because it gives a structural way to decide whether interface variables can be evaluated explicitly or whether an algebraic loop must be treated specially. 

---

## 4. Communication Step Size and Input Approximation

In co-simulation, data are exchanged only at communication points

$$
T_n,
\qquad
T_{n+1} = T_n + H,
$$

where $H$ is the **communication step size** or **macro step size**. During the interval $[T_n, T_{n+1}]$, the true subsystem input $u_j(t)$ is not known. It is approximated by a polynomial interpolation or extrapolation function.

The paper considers an approximation of degree $k$:

$$
\Psi_j(t)
=
\sum_{\iota=0}^{k}
u_j(T_{n-\iota})
\prod_{\substack{l=0 \ l \neq \iota}}^{k}
\frac{t - T_{n-l}}{T_{n-\iota} - T_{n-l}},
$$

with approximation error

$$
\Psi_j(t) = u_j(t) + O(H^{k+1}).
$$

Important special cases are:

* **constant extrapolation**: (k = 0), input is frozen over the communication step,
* **linear extrapolation**: (k = 1),
* **quadratic extrapolation**: (k = 2).

The paper deliberately neglects the micro-integration errors inside the subsystems in the theoretical part to isolate the additional error introduced by the coupling approximation. 

---

## 5. Local and Global Error Behavior

A central result of the paper is that **communication step size control may be based on local error estimates**, but only under structural assumptions on the coupled system.

For coupled systems without algebraic loops, the authors derive global errors of the form

$$
|\varepsilon^x_n| = O(H^{k+1}),
\qquad
|\varepsilon^u_n| = O(H^{k+1}).
$$

Thus, the global error on finite time intervals can be bounded in terms of local errors if the coupled system is free of algebraic loops and the acyclic feed-through condition holds. The paper also notes that local order-reduction effects do not necessarily deteriorate the global error order if there are no closed structural feed-through paths. 

This result is important because it provides a theoretical justification for adaptive communication step size control in co-simulation.

---

## 6. Local Error Estimation

For communication step size control, an estimate of the local error is compared against user-defined tolerances. The paper studies two local error estimation approaches:

1. **Classical Richardson extrapolation**
2. **A modified FMI-oriented error estimate**

Richardson extrapolation compares:

* two consecutive communication steps of size $H$,
* one larger communication step of size $2H$.

In classical ODE and DAE integration, this gives a reliable estimate of the leading local error term. For modular time integration, the corresponding estimate is denoted as

$$
EST_{\mathrm{Rich}}.
$$

However, co-simulation differs from classical ODE/DAE time integration because errors also enter through the approximated coupling inputs. The paper shows that Richardson extrapolation may become asymptotically wrong if the coupled system has direct feed-through in at least one subsystem, i.e. if terms of the form $L_nD_n \neq 0$ occur. If there is no direct feed-through, Richardson extrapolation reproduces the local output error correctly up to higher-order terms. 

The paper therefore studies a modified estimator, denoted in the numerical section as

$$
EST_{\mathrm{mod}},
$$

which reduces the computational effort compared with classical Richardson extrapolation and is tailored to the FMI co-simulation setting. 

---

## 7. Direct Feed-Through and Error-Estimate Degradation

The paper distinguishes two important coupling cases:

| Coupling type                          |  Direct feed-through? | Error behavior                   |
| -------------------------------------- | --------------------: | -------------------------------- |
| **Displacement-displacement coupling** |                    No | More favorable error behavior    |
| **Force-displacement coupling**        | Yes, in one subsystem | Local error order may be reduced |

For systems without direct feed-through, the local output error behaves like

$$
|l^y_{n+2}| = O(H^{k+2}).
$$

For systems with direct feed-through in at least one subsystem, the order is reduced to

$$
|l^y_{n+2}| = O(H^{k+1}).
$$

The quarter-car benchmark confirms this behavior: displacement-displacement coupling shows the higher local-error order, while force-displacement coupling shows reduced local-error order. In both cases, the modified estimator $EST_{\mathrm{mod}}$ was reported to be as reliable as the classical Richardson estimator $EST_{\mathrm{Rich}}$. 

---

## 8. Numerical Test: Quarter-Car Benchmark

The numerical benchmark is a simplified **quarter-car model**. It consists of two point masses:

* $m_w$: unsprung mass,
* $m_c$: sprung mass.

Both masses have vertical degrees of freedom. They are coupled by a linear spring-damper element representing the suspension, and the tire force is modeled by another spring-damper element between the wheel mass and the road profile. 

The benchmark compares:

1. **displacement-displacement coupling**, without direct feed-through,
2. **force-displacement coupling**, with direct feed-through in one subsystem.

The numerical results verify the theoretical local error analysis:

* without direct feed-through: local error order $O(H^{k+2})$,
* with direct feed-through: reduced local error order $O(H^{k+1})$.

The paper also states that the global errors do not suffer from order reduction in either coupling case, and that the practical implementation of such local error estimates must also account for micro-integration errors inside the subsystems, which remains an open issue. 

---

## 9. Main Conclusions of the Paper

The paper concludes that the numerical efficiency of co-simulation can be substantially improved by:

* higher-order approximations of subsystem inputs,
* variable communication step sizes,
* reliable local error estimates.

The mathematical analysis shows that global errors can be bounded in terms of local errors if there are no algebraic loops in the coupled system. Richardson-based estimates and modified estimates are effective for systems without direct feed-through, such as mechanical displacement-displacement coupling. However, force-displacement coupling introduces direct feed-through and can deteriorate the favorable asymptotic behavior of classical error estimation strategies. 

---

# Relevance for `syssimx`

## 1. Direct Relevance

This paper is relevant for `syssimx` because it provides theoretical support for several design choices in heterogeneous co-simulation.

| Arnold et al. concept                               | Relevance for `syssimx`                                              |
| --------------------------------------------------- | -------------------------------------------------------------------- |
| Block-oriented co-simulation                        | `syssimx` system of `CoSimComponent` objects                         |
| Subsystem inputs ($u_j$), outputs ($y_j$), states ($x_j$) | Input/output ports and component-local states                        |
| Communication points ($T_n$)                          | Macro steps in the master algorithm                                  |
| Communication step size ($H$)                         | `system.run(..., dt=...)` macro step size                            |
| Input extrapolation / interpolation                 | Assumption behind weak coupling between macro steps                  |
| Direct feed-through                                 | Component metadata used for dependency analysis                      |
| Structural feed-through graph                       | `syssimx` dependency graph                                           |
| Cycles in feed-through graph                        | Algebraic loops / strongly connected components                      |
| Nilpotent adjacency matrix for acyclic graph        | Structural condition for explicit evaluation order                   |
| Local error estimates                               | Basis for future communication-step control                          |
| Direct-feedthrough degradation of error estimates   | Motivation to distinguish feedthrough and non-feedthrough components |

---

## 2. Relation to Algebraic-Loop Handling

The paper’s graph-based feed-through analysis is highly relevant for the algebraic-loop handling in `syssimx`.

The key conceptual chain is:

```text
direct feed-through
→ structural feed-through paths
→ directed dependency graph
→ cycles in graph
→ algebraic loops
→ need for special master-level treatment
```

This maps closely to the `syssimx` approach:

```text
component input-output dependencies
→ system dependency graph
→ strongly connected components
→ algebraic-loop blocks
→ iterative solution by the master algorithm
```

Arnold et al. focus mainly on acyclic feed-through structures for the error analysis, whereas `syssimx` additionally implements mechanisms for detecting and solving algebraic loops at the framework level.

---

## 3. Relation to Step-Size Control

The paper is especially relevant as **future-work justification** for adaptive macro-step control in `syssimx`.

Currently, if `syssimx` uses a fixed macro step size, the user must select this step size manually. Arnold et al. show that communication step size control can be theoretically justified by local error estimates, provided the structural assumptions of the coupled system are satisfied.

For a future extension of `syssimx`, this implies:

* local co-simulation error estimates could be computed at communication steps,
* communication step sizes could be adapted automatically,
* step rejection would require rollback or state restore support,
* direct-feedthrough components require special care because classical Richardson estimates may be unreliable,
* micro-integration errors inside FMUs, OpenSim, or FEM components must also be considered.

The last point is particularly important for heterogeneous `syssimx` components because the internal solver errors of different backends are not always visible to the master algorithm.

---

## 4. Relation to Hybrid Events

The paper is not primarily about hybrid event detection, zero-crossing localization, or event propagation. Its focus is communication-step error analysis for continuous co-simulation.

However, it is still indirectly relevant for hybrid simulation because event localization and adaptive step-size control both require:

* reliable estimates of what happens inside a communication interval,
* rollback or repeatable simulation steps,
* clear distinction between macro-step error and subsystem-internal integration error,
* structural information about component dependencies.

In `syssimx`, the hybrid event algorithm uses bisection and rollback to localize event times. Arnold et al. provide complementary theory for communication error estimation and macro-step-size control.

---

## 5. Relation to Runtime Model Switching

The paper does not address runtime model switching directly. Nevertheless, its analysis is useful for interpreting switching workflows in `syssimx`.

Runtime switching between low- and high-fidelity models changes the active subsystem representation during simulation. This can affect:

* the direct-feedthrough structure,
* the communication error,
* the local consistency of exchanged variables,
* the validity of a chosen macro step size.

Therefore, a switching component should expose structural metadata consistently, and the master algorithm should update or validate dependency information when the active model changes.

---

# Compact Thesis-Ready Summary

Arnold, Clauss, and Schierz (2013) analyze communication-step errors in FMI-compatible co-simulation. They consider coupled systems in block representation, where each subsystem has state, input, and output variables and where subsystem inputs are computed from other subsystem outputs. During one communication step, the true subsystem inputs are unknown and must be approximated by polynomial extrapolation or interpolation. This signal approximation introduces additional error terms and motivates communication step size control. 

A central part of the paper is the structural analysis of direct feed-through. The interface equations can be written as (u = c(g(x,u))). If one input component structurally depends on another, this relation defines an edge in a directed feed-through graph. Cycles in this graph correspond to closed structural feed-through paths, i.e. algebraic loops. If the graph is acyclic, its adjacency matrix is nilpotent, and the coupled system is suitable for the convergence analysis used in the paper. 

The authors show that, for systems without algebraic loops, the global co-simulation error over finite time intervals can be bounded in terms of local errors. This provides theoretical justification for communication step size control based on local error estimates. The paper studies Richardson extrapolation and a modified FMI-oriented estimator. Classical Richardson extrapolation is reliable for systems without direct feed-through, but may become asymptotically wrong when direct feed-through exists in at least one subsystem. 

The numerical quarter-car benchmark verifies the theoretical findings. In displacement-displacement coupling, where no direct feed-through exists, the local output error has order (O(H^{k+2})). In force-displacement coupling, where one subsystem has direct feed-through, the local output error is reduced to (O(H^{k+1})). The modified estimator is reported to be as reliable as the classical Richardson estimator in the tested cases, but practical step-size control must also account for micro-integration errors inside the individual subsystems. 

For this thesis, the paper is relevant because it connects structural dependency analysis with numerical error behavior in co-simulation. The `syssimx` dependency graph and direct-feedthrough metadata follow the same motivation: cyclic feed-through dependencies must be detected because they affect both execution order and numerical reliability. While `syssimx` currently focuses on heterogeneous hybrid co-simulation, algebraic-loop handling, event localization, and runtime model switching, the error-estimation framework of Arnold et al. provides a theoretical basis for future adaptive communication-step control.

# Possible Thesis Sentence

```latex
Arnold, Clauss, and Schierz analyze FMI-compatible co-simulation as a block-structured modular time-integration problem in which subsystem inputs are approximated between communication points. Their feed-through graph formalism shows that cycles in the structural dependency graph correspond to algebraic loops, and their error analysis demonstrates that reliable communication-step error estimation depends on the absence of such closed feed-through paths. This motivates the direct-feedthrough metadata and graph-based dependency analysis in \syssimx{}, while their Richardson-based local error estimates provide a basis for future adaptive communication-step control.
```
