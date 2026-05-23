# Kübler & Schiehlen (2000): Two Methods of Simulator Coupling

**Reference:** Kübler, R., & Schiehlen, W. (2000). *Two Methods of Simulator Coupling*. *Mathematical and Computer Modelling of Dynamical Systems*, 6(2), 93–113. [https://doi.org/10.1076/1387-3954(200006)6:2;1-M;FT093](https://doi.org/10.1076/1387-3954%28200006%296:2;1-M;FT093)

## 1. Core Motivation

Kübler and Schiehlen study the **modular simulation of complex engineering systems**. Instead of formulating the complete system as one monolithic model, the global system is decomposed into interacting subsystems. This is especially relevant for **mechatronic systems**, where mechanical, control, and electronic subsystems are often developed by different domain experts and simulated with different tools.

The modular approach has several advantages:

* subsystems can be modeled independently,
* subsystem experts can work in parallel,
* modules can be exchanged or modified without rebuilding the full system,
* different simulation tools can be used for different engineering domains,
* internal subsystem dynamics can be hidden during the simulation of the global system.

However, simulator coupling introduces a numerical problem. If the coupled subsystems contain **algebraic loops**, the modular simulation may become unstable. The paper therefore analyzes the zero-stability of modular numerical integration and introduces two coupling methods for systems with algebraic loops:

1. **Iterative simulator coupling**
2. **Elimination of algebraic loops by filters**

---

## 2. Modular Simulation and Model Description Levels

The paper distinguishes three model description levels:

| Level                              | Description                                                                                              |
| ---------------------------------- | -------------------------------------------------------------------------------------------------------- |
| **Physical model description**     | Physical representation of the engineering system, e.g. geometry, masses, circuits, mechanical structure |
| **Mathematical model description** | Equations describing the subsystem behavior, e.g. equations of motion or state-space equations           |
| **Behavioral model description**   | Simulated input-output behavior, e.g. time trajectories of positions, velocities, forces, or currents    |

The coupling of models on the **behavioral model description level** is called **modular simulation** or **simulator coupling**.

In this setup, the global system is simulated by a **time-discrete linker and scheduler**. The linker combines subsystem inputs and outputs at discrete communication instants. The scheduler controls when subsystems are advanced and when data are exchanged.

This allows the global system to be assembled from separate simulators, but it also means that subsystem coupling is only enforced at discrete communication points.

---

## 3. Mathematical Description of Subsystems

Each subsystem (i) is described by nonlinear state-space equations:

$$
\dot{x}^{i} = f^{i}(x^{i}, u^{i}, t),
\qquad
x^{i}(t_0) = x^{i}_0
$$

$$
y^{i} = g^{i}(x^{i}, u^{i}, t),
\qquad
i = I, II, \ldots, N
$$

where:

| Symbol  | Meaning                        |
| ------- | ------------------------------ |
| $x^{i}$ | state vector of subsystem $i$  |
| $u^{i}$ | input vector of subsystem $i$  |
| $y^{i}$ | output vector of subsystem $i$ |
| $N$     | number of subsystems           |

The global system is formed by interconnecting subsystem inputs and outputs. The input vector of subsystem $i$ is computed from the global output vector:

$$
u^{i} = L^{i} y
$$

Here, $L^{i}$ is an incidence matrix whose entries are zero or one. It encodes which subsystem outputs are connected to which subsystem inputs.

This formulation supports modularity because each subsystem is coupled only through explicit input and output variables.

---

## 4. Numerical Integration and Input Extrapolation

The paper distinguishes between:

* the **local integration step size** (h),
* the **global communication step size** (H).

A subsystem may perform $m$ local integration steps during one global communication step:

$$
H = m h
$$

During the integration interval, the future subsystem inputs are generally unknown. Therefore, the inputs are approximated by extrapolation:

$$
\hat{u}_{k+r}
=
\sum_{j=0}^{p_E-1} \gamma_j(r) u_{k-j},
\qquad
r \in [0,1]
$$

The extrapolation has order $p_E - 1$. For example, constant extrapolation corresponds to $p_E = 1$.

The time-discrete description of subsystem $i$ can be written as:

$$
x^{i}_{k+1}
=
\Phi^{i}(\varphi^{i}, m^{i}, \hat{u}^{i})
$$

$$
y^{i}_{k+1}
=
g^{i}(x^{i}_{k+1}, u^{i}_{k+1}, t_{k+1})
$$

The coupling equations at the global communication point are:

$$
u^{i}_{k+1} = L^{i} y_{k+1}
$$

Thus, each subsystem is integrated with extrapolated inputs, while the actual coupling is enforced only at communication instants.

---

## 5. Zero-Stability of Modular Integration

The paper first recalls the zero-stability of a numerical integration method. A discrete integration method is zero-stable if the eigenvalues of the corresponding characteristic equation lie inside the unit circle and all eigenvalues on the unit circle are simple.

For coupled subsystem integration, the same idea is applied to the global time-discrete coupled system. The coupled integration is zero-stable if the resulting global discrete system is stable.

The paper considers one-step methods and assumes that the output equations depend linearly on the inputs:

$$
y^{i} = \bar{g}^{i}(x^{i}) + D^{i} u^{i}
$$

The matrix $D^{i}$ describes the **direct feed-through** from the subsystem input $u^{i}$ to the subsystem output $y^{i}$.

By inserting the coupling equations, the global output update contains products of the direct-feedthrough matrices $D^{i}$ and the incidence matrices $L^{i,j}$. Stability then depends on the spectral radius of the resulting coupling matrix:

$$
\rho(D) < 1
$$

where $\rho(D)$ is the spectral radius of the matrix $D$.

For two coupled subsystems, the paper shows that if at least one subsystem has no direct feed-through, then no algebraic loop exists. If both subsystems have direct feed-through and are mutually connected, an algebraic loop is present.

The central conclusion is:

> Modular numerical integration is guaranteed to be zero-stable if no algebraic loops exist between the coupled subsystems.

For an arbitrary number of subsystems, an algebraic loop exists if the global system contains a closed loop of interconnected subsystems in which all involved outputs directly depend on their inputs.

If no algebraic loop exists, all outputs can be determined explicitly from the subsystem states:

$$
y_k = H(x_k)
$$

Then, for one-step methods and vanishing step size, the coupled system reduces to a stable discrete system:

$$
x_{k+1} = x_k = \text{const.}
$$

---

## 6. Algebraic Loops as the Central Problem

An **algebraic loop** occurs when subsystem outputs depend directly on subsystem inputs and these inputs are themselves computed from other subsystem outputs in a closed cycle.

In such a situation, the coupled interface variables cannot be evaluated explicitly in a sequential order. Instead, they form an implicit nonlinear algebraic problem at the global communication point.

Without special treatment, simulator coupling uses extrapolated input variables. The paper shows that instability can occur due to the dynamics introduced by the extrapolation of unknown inputs.

Therefore, algebraic loops must be treated explicitly. Kübler and Schiehlen propose two approaches:

1. solve the interface problem iteratively,
2. eliminate algebraic loops by inserting filters.

---

## 7. Iterative Simulator Coupling

The first method is **iterative simulator coupling**. Its purpose is to solve the unknown coupling variables consistently at every global communication step.

The paper distinguishes two variants:

1. **Iteration of output equations**
2. **Iteration of the global integration step**

Both variants lead to nonlinear algebraic equations that must be solved iteratively at each global time step.

---

## 7.1 Iteration of Output Equations

In the first variant, each subsystem is integrated once using extrapolated input values. After integration, the output equations are evaluated iteratively at the communication point.

The important point is that the new input vector $u^{i}_{k+1}$ is **not extrapolated** for the output evaluation. Instead, the coupling equation

$$
u^{i}_{k+1} = L^{i} y_{k+1}
$$

is inserted directly into the output equations.

This yields a nonlinear algebraic system for the global output vector:

$$
y_{k+1} = \Psi_o(y_{k+1})
$$

This system must be solved for each global time step.

Conceptually:

```text
1. Extrapolate subsystem inputs over the communication interval.
2. Integrate each subsystem once.
3. At the communication point, insert u_{k+1} = L y_{k+1}.
4. Solve the resulting nonlinear algebraic output system iteratively.
5. Use the converged coupling variables for the next step.
```

The advantage is that the subsystem integration does not have to be repeated in every iteration. Only the output equations are iterated.

---

## 7.2 Iteration of the Global Integration Step

In the second variant, the new inputs $u^{i}_{k+1}$ are used not only in the output equations but also in the interpolation or extrapolation of the inputs during the integration step:

$$
\hat{u}_{k+r}
=
\sum_{j=0}^{p_E}
\gamma_j(r) u_{k+1-j}
$$

Because $u^{i}_{k+1}$ appears inside the integration step, the state update also depends on the unknown new coupling variables. The subsystem equations become:

$$
x^{i}_{k+1}
=
\Phi^{i}(\varphi^{i}, m^{i}, \hat{u}^{i})
$$

$$
y^{i}_{k+1}
=
g^{i}(x^{i}_{k+1}, u^{i}_{k+1}, t_{k+1})
$$

After inserting the coupling equations, this again yields a nonlinear algebraic system:

$$
y_{k+1} = \Psi_s(y_{k+1})
$$

This has the same structure as in the iteration of output equations, but now each iteration requires repeating the global integration step.

Conceptually:

```text
1. Guess the new coupling variables at t_{k+1}.
2. Use these variables inside the input interpolation/extrapolation.
3. Integrate all subsystems over the global communication step.
4. Evaluate outputs and coupling equations.
5. Check consistency.
6. Repeat the complete global integration step until convergence.
```

This method is more expensive than iterating only the output equations, because subsystem integration must be repeated for each iteration. However, it treats the influence of the new coupling variables during the integration interval more consistently.

---

## 7.3 Zero-Stability of Iterative Methods

For vanishing global step size, both iterative coupling variants lead to the same discrete system:

$$
x^{i}_{k+1}
=
\Phi^{i}(\varphi^{i}(h \rightarrow 0), m^{i})
$$

$$
y^{i}_{k+1}
=
g^{i}(x^{i}_{k+1}, u^{i}_{k+1}, t_{k+1})
$$

$$
u^{i}_{k+1}
=
L^{i} y_{k+1}
$$

The paper concludes that the only condition for the stability of the global system is the use of zero-stable numerical integrators.

Therefore:

> Iterative simulator coupling guarantees zero-stability of the coupled integration if zero-stable subsystem integration methods are used.

This is the main theoretical advantage of iterative coupling.

---

## 7.4 Solvers for the Nonlinear Interface Problem

Both iterative methods require solving nonlinear algebraic equations at every global communication step.

The paper mentions several possible iterative solvers:

| Solver                     | Comment                                                                                        |
| -------------------------- | ---------------------------------------------------------------------------------------------- |
| **Jacobi iteration**       | Does not require gradient information, but is not always locally convergent                    |
| **Gauss-Seidel iteration** | Does not require gradient information and is often practical for modular simulation            |
| **Newton method**          | Quadratically convergent if the start value is close enough, but requires the Jacobian         |
| **Broyden method**         | Secant approximation to the Jacobian; locally convergent and avoids exact Jacobian computation |

The paper notes that gradient information is usually not available in modular simulator coupling because each simulator may only be accessible through input and output terminals. Therefore, methods that do not require explicit Jacobians are practically important.

---

## 8. Filter Method

The second method eliminates algebraic loops by introducing **filters**.

The starting point is an algebraic loop in which all subsystems in the loop have direct feed-through:

$$
\dot{x}^{j} = f^{j}(x^{j}, u^{j}, t)
$$

$$
y^{j} = g^{j}(x^{j}, u^{j}, t),
\qquad
j \in {I, \ldots, N}
$$

Since the outputs explicitly depend on the inputs, algebraic loops can occur.

The filter method inserts filters into the coupling paths such that the subsystem outputs are no longer directly used as inputs to another feed-through subsystem. The filter has its own state equation and output equation:

$$
\dot{x}^{F} = f^{F}(x^{F}, u^{F}, t)
$$

$$
y^{F} = g^{F}(x^{F}, t)
$$

The important property is that the filter output $y^F$ does **not** explicitly depend on the filter input $u^F$. Therefore, the filter has no direct feed-through.

The original subsystem output is used as the filter input:

$$
u^{F} = y^{j}
$$

The filtered output is then used as the coupling input for the next subsystem.

Introducing the new state vector

$$
x^{z}
=
\begin{bmatrix}
x^{j} \
x^{F}
\end{bmatrix}
$$

the modified subsystem can be written as:

$$
\dot{x}^{z}
=
f^{z}(x^{z}, u^{j}, t)
$$

$$
y^{z}
=
g^{z}(x^{z}, t)
$$

Because the modified output equation no longer explicitly depends on the input, the modified subsystem has no direct feed-through. Consequently, the algebraic loop is removed.

---

## 8.1 Interpretation of the Filter Method

The filter method replaces an instantaneous algebraic dependency by a dynamic relation:

```text
original subsystem output
→ filter state dynamics
→ filtered signal
→ receiving subsystem input
```

This breaks the algebraic loop because the receiving subsystem input no longer depends instantaneously on the upstream output.

The method is related to:

* Baumgarte stabilization,
* force-coupling approximations in multibody system dynamics.

---

## 8.2 Advantages and Disadvantages of the Filter Method

The main advantage is:

* no iterations are required during modular simulation.

However, the paper emphasizes several disadvantages:

* the original problem is not solved exactly because the filter changes the dynamics,
* the filter parameters determine how close the modified system is to the original system,
* if the filter approximation is chosen too aggressively, high-frequency dynamics are introduced,
* high-frequency dynamics can force the numerical integrator to use a much smaller time step.

Thus, the filter method can remove algebraic loops, but it modifies the mathematical model and may introduce stiffness or additional numerical cost.

---

## 9. Numerical Example

The paper illustrates the analytical results using a **double pendulum** modeled as a multibody system. After describing and decomposing the physical model into two subsystems, the mathematical model of each subsystem is set up independently.

The example is used to compare the two simulator-coupling methods:

1. iterative simulator coupling,
2. filter-based elimination of algebraic loops.

The purpose of the example is to show how algebraic loops arise in modular multibody simulation and how the two proposed methods affect stability and computational efficiency.

---

## 10. Main Findings

The main findings of the paper are:

1. **Modular simulation is attractive for complex engineering systems.**
   It supports independent subsystem development, module exchange, parallel work, and the use of domain-specific simulation tools.

2. **Input-output coupling introduces numerical stability issues.**
   In modular simulation, subsystem inputs over a communication interval are usually unknown and must be extrapolated.

3. **Algebraic loops are the critical structural problem.**
   If direct-feedthrough subsystems form a closed coupling loop, the coupled integration may become unstable.

4. **No algebraic loops implies guaranteed zero-stability.**
   If the coupled system has no algebraic loops and the subsystem integrators are zero-stable, modular numerical integration is zero-stable.

5. **Iterative coupling guarantees zero-stability for systems with algebraic loops.**
   Iterative methods solve the interface consistency problem at each global time step. Stability then depends only on the zero-stability of the subsystem integrators.

6. **The filter method removes algebraic loops but modifies the system.**
   Filters eliminate direct feed-through and avoid iterative coupling, but they change the original dynamics and may introduce high-frequency behavior.

---

## 11. Relevance for syssimx

This paper is directly relevant for the algebraic-loop and co-simulation part of `syssimx`.

| Kübler & Schiehlen concept                   | syssimx counterpart                                            |
| -------------------------------------------- | -------------------------------------------------------------- |
| Modular decomposition of engineering systems | Component-based system construction                            |
| Subsystem input/output vectors (u^i, y^i)    | Typed input and output ports                                   |
| Incidence matrices (L^i)                     | Connection graph / dependency graph                            |
| Direct-feedthrough matrices (D^i)            | Direct-feedthrough metadata                                    |
| Algebraic loop between subsystems            | Strongly connected component in the dependency graph           |
| Time-discrete linker and scheduler           | Master algorithm / system execution layer                      |
| Iterative simulator coupling                 | Iterative algebraic-loop solution                              |
| Iteration of output equations                | Solving interface variables at a communication point           |
| Iteration of global integration step         | Repeating coupled simulation steps until consistency           |
| Filter method                                | Alternative loop-breaking strategy not chosen as core approach |
| Double-pendulum example                      | Controlled-pendulum case study in `syssimx`                    |

The paper provides a theoretical foundation for the design decision that `syssimx` should not simply execute coupled components sequentially when algebraic loops are present. Instead, cyclic direct-feedthrough dependencies must be detected structurally and solved by the master algorithm.

The `syssimx` approach is closest to the **iterative simulator coupling** strategy. Algebraic loops are detected from component metadata and resolved at system level. The filter method is conceptually relevant but less suitable as a default strategy because it modifies the physical dynamics by inserting artificial filter states.

---

## 12. Thesis-Relevant Interpretation

Kübler and Schiehlen formalize simulator coupling as the interconnection of subsystem state-space models through input-output incidence matrices. Their analysis shows that modular numerical integration is zero-stable if the coupled system does not contain algebraic loops. If algebraic loops exist, extrapolation of unknown coupling inputs can destabilize the simulation.

This directly motivates:

* explicit input-output port definitions,
* direct-feedthrough metadata,
* graph-based dependency analysis,
* strongly connected component detection,
* iterative treatment of algebraic loops at the master-algorithm level.

Compared with the setting of Kübler and Schiehlen, `syssimx` extends the simulator-coupling problem in three directions:

1. **Heterogeneity:** components may be FMUs, OpenSim models, FEM/NGSolve models, or Python components.
2. **Hybrid behavior:** components may define events, zero-crossing indicators, and state resets.
3. **Runtime model switching:** alternative models of the same subsystem can be activated during simulation.

---

## 13. Compact Thesis-Ready Summary

Kübler and Schiehlen (2000) study simulator coupling as a modular simulation approach for complex engineering systems. Each subsystem is described by nonlinear state-space equations with explicit input and output variables, and the global system is assembled through algebraic coupling equations using incidence matrices. This formulation supports independent subsystem modeling, software reuse, and the use of different simulation tools for different engineering domains.

The paper analyzes the zero-stability of modular numerical integration. During one global communication step, subsystem inputs are generally unknown and are therefore approximated by extrapolation. If the coupled system contains no algebraic loops, the subsystem outputs can be determined explicitly from the subsystem states, and zero-stability of the coupled integration is guaranteed for zero-stable subsystem integration methods. If, however, direct-feedthrough subsystems form a closed coupling loop, the coupled outputs and inputs form an implicit algebraic problem. In this case, extrapolated coupling inputs can destabilize the modular simulation.

To treat algebraic loops, the paper introduces two simulator-coupling methods. The first method is iterative simulator coupling. Two variants are discussed: iteration of the output equations and iteration of the complete global integration step. Both lead to nonlinear algebraic systems that must be solved iteratively at each global time step. The paper concludes that iterative coupling guarantees zero-stability if zero-stable subsystem integrators are used. The second method eliminates algebraic loops by inserting filters into coupling paths, thereby replacing direct algebraic dependencies by dynamic relations. This avoids iterative solution but modifies the mathematical model and can introduce additional high-frequency dynamics.

For this thesis, the paper is relevant because it establishes algebraic loops as a fundamental numerical issue in modular simulator coupling. The structural dependency analysis and iterative algebraic-loop handling in `syssimx` follow the same motivation: cyclic direct-feedthrough dependencies between coupled components must be detected and resolved at the master-algorithm level. In contrast to Kübler and Schiehlen, `syssimx` applies this principle to heterogeneous hybrid co-simulation with FMUs, OpenSim models, FEM components, event localization, and runtime model switching.

---

## 14. Possible Thesis Sentence

```latex
Kübler and Schiehlen analyze simulator coupling through subsystem state-space models connected by input-output incidence matrices and show that modular numerical integration is zero-stable only if no algebraic loops exist between direct-feedthrough subsystems. Their iterative coupling approach motivates the treatment of cyclic direct-feedthrough dependencies as nonlinear interface problems in \syssimx{}, while the present framework extends this principle to heterogeneous hybrid co-simulation with tool-specific subsystem wrappers, event localization, and runtime model switching.
```