# Notation

## Purpose

This document is the single source of truth for mathematical notation in the thesis.
It defines the symbols that should be used consistently across Chapter 2 and in later theory-facing references.

The current co-simulation notation is aligned to:

- `thesis/chapters/2_theoretical_background/23_cosimulation_principles.tex`

The notation table in:

- `thesis/chapters/2_theoretical_background/20_notation_and_conventions.tex`

should be derived from this document rather than maintained independently.

---

# 1. General Principles

- A **system** is decomposed into **subsystems** indexed by $i$.
- Continuous-time variables are functions of physical time $t$.
- Differential states are denoted by $x(t)$.
- Algebraic variables are denoted by $z(t)$.
- Discrete modes or discrete states are denoted by $q(t)$.
- Inputs and outputs are denoted by $u(t)$ and $y(t)$.
- Communication points in co-simulation are indexed by $k$.
- Superdense-time microstep indices are denoted by $\nu$.
- Vectors are denoted by symbols such as $x$, $z$, $u$, and $y$; individual components are written with subscripts.

## Time-argument convention

The time argument $(t)$ is declared in prose on first introduction and may be omitted inside equations when the time dependence is clear from context.
It should be written explicitly when a named time instant such as $t_0$, $T_k$, or $t_e$ is discussed.

---

# 2. Global Symbols

## 2.1 Indices and Time

| Symbol | Meaning | Usage |
|--------|---------|-------|
| $t$ | Physical time | Continuous-time and hybrid evolution |
| $t_e$ | Event time | Hybrid systems and hybrid co-simulation |
| $i$ | Subsystem index | General subsystem or simulation-unit indexing |
| $j$ | Event or indicator index | Event definitions |
| $k$ | Communication-point index | Co-simulation |
| $\nu$ | Superdense-time microstep index | Ordering of discrete updates at fixed physical time |
| $T_k$ | Communication point $k$ | Co-simulation communication grid |
| $H_k = T_{k+1}-T_k$ | Macro step size | Communication interval in co-simulation |
| $H$ | Generic requested step duration | Simulation-unit interface or generic co-simulation operator |
| $\Delta t_{i,r}$ | Internal step size of subsystem $i$ at local step $r$ | Internal stepping between communication points |

## 2.2 Continuous-Time and DAE Models

| Symbol | Meaning | Usage |
|--------|---------|-------|
| $x(t)$ | Continuous or differential state vector | ODE and DAE models |
| $z(t)$ | Algebraic variable vector | DAE and hybrid models |
| $u(t)$ | Input vector | Continuous, hybrid, and co-simulation models |
| $y(t)$ | Output vector | Continuous, hybrid, and co-simulation models |
| $f(\cdot)$ | State-transition map | Explicit ODE or semi-explicit DAE |
| $h(\cdot)$ | Output map | Continuous and hybrid models |
| $g(\cdot)$ | Algebraic constraint function | Semi-explicit DAE |
| $G(\cdot)$ | Implicit DAE residual form | Implicit DAE and hybrid mode-dependent dynamics |

## 2.3 Hybrid-System Symbols

| Symbol | Meaning | Usage |
|--------|---------|-------|
| $q(t)$ | Discrete mode or discrete state | Hybrid systems |
| $\gamma_j(\cdot)$ | Event indicator / zero-crossing function | Hybrid systems and hybrid co-simulation |
| $R_j(\cdot)$ | Continuous-state reset map | Hybrid systems |
| $\delta_j(\cdot)$ | Discrete-state update map | Hybrid systems |
| $(\cdot)^-$ | Value immediately before an event | Hybrid systems |
| $(\cdot)^+$ | Value immediately after an event | Hybrid systems |
| $(t,\nu)$ | Superdense time | Hybrid simulation semantics |

## 2.4 Co-Simulation Symbols

| Symbol | Meaning | Usage |
|--------|---------|-------|
| $I$ | Finite index set of simulation units | Co-simulation scenario |
| $\mathsf{SU}_i$ | Abstract simulation unit representation | Co-simulation theory |
| $\mathcal{S}_i$ | Internal state space of simulation unit $i$ | Co-simulation theory |
| $\mathcal{U}_i$ | Set of input ports of simulation unit $i$ | Co-simulation theory |
| $\mathcal{Y}_i$ | Set of output ports of simulation unit $i$ | Co-simulation theory |
| $\mathcal{V}_i$ | Value domain of the ports of simulation unit $i$ | Co-simulation theory |
| $s_i(T_k)$ | Internal state of simulation unit $i$ at communication point $T_k$ | Execution-strategy discussion |
| $\operatorname{set}_i$ | Input staging operator of simulation unit $i$ | Simulation-unit interface |
| $\operatorname{get}_i$ | Output query operator of simulation unit $i$ | Simulation-unit interface |
| $\operatorname{step}_i$ | Time-advancement operator of simulation unit $i$ | Simulation-unit interface |
| $F_i$ | Direct-feedthrough relation of simulation unit $i$ | Structural analysis |
| $\mathcal{C}$ | Co-simulation scenario | Co-simulation theory |
| $\mathcal{L}$ | Set of directed port connections | Co-simulation scenario |
| $\mathcal{U}$ | Global set of indexed input ports | Co-simulation scenario |
| $\mathcal{Y}$ | Global set of indexed output ports | Co-simulation scenario |
| $\Gamma_i$ | Coupling operator mapping outputs to the inputs of simulation unit $i$ | Co-simulation theory |
| $\Gamma_A$ | Coupling operator restricted to one algebraic loop | Algebraic-loop theory |
| $\hat{u}_i(t)$ | Extrapolated input of simulation unit $i$ between communication points | Co-simulation |
| $\mathcal{R}(\cdot)$ | Interface residual for algebraic-loop consistency | Co-simulation algebraic loops |
| $U_A$ | Stacked interface inputs of one algebraic loop | Co-simulation algebraic loops |
| $Y_A(U_A)$ | Interface outputs induced by a trial input vector $U_A$ | Co-simulation algebraic loops |

## 2.5 Structural-Analysis Symbols

| Symbol | Meaning | Usage |
|--------|---------|-------|
| $G=(V,E)$ | Directed dependency graph | Structural analysis |
| $j \rightarrow i$ | Directed dependency edge from simulation unit $j$ to simulation unit $i$ | Structural analysis |
| $A \subseteq I$ | Set of simulation units participating in one algebraic loop | Structural analysis and algebraic-loop theory |

---

# 3. Canonical Forms

## 3.1 Explicit state-space form

A continuous-time subsystem is written as

$$
\dot{x}(t) = f(x(t),u(t),t),
\qquad
y(t) = h(x(t),u(t),t).
$$

## 3.2 Semi-explicit DAE form

A semi-explicit DAE is written as

$$
\dot{x}(t) = f(x(t),z(t),u(t),t),
\qquad
0 = g(x(t),z(t),u(t),t),
\qquad
y(t) = h(x(t),z(t),u(t),t).
$$

## 3.3 Hybrid subsystem form

A hybrid subsystem is represented by

$$
\bigl(q(t),x(t),z(t),u(t),y(t)\bigr),
$$

and between events follows

$$
0 = G_q(\dot{x},x,z,u,t),
\qquad
y = h_q(x,z,u,t).
$$

At an event time $t_e$, the update maps are written as

$$
x^{+} = R_j(x^{-},z^{-},q^{-},u^{-},t_e),
\qquad
q^{+} = \delta_j(x^{-},z^{-},q^{-},u^{-},t_e).
$$

## 3.4 Simulation-unit abstraction

At co-simulation level, subsystem $i$ is represented by

$$
\mathsf{SU}_i =
\left\langle
\mathcal{S}_i,\,
\mathcal{U}_i,\,
\mathcal{Y}_i,\,
\operatorname{set}_i,\,
\operatorname{get}_i,\,
\operatorname{step}_i
\right\rangle.
$$

## 3.5 Co-simulation scenario

A co-simulation scenario is written as

$$
\mathcal{C} =
\left\langle
I,\;
\{\mathsf{SU}_i\}_{i \in I},\;
\mathcal{L},\;
\{F_i\}_{i \in I}
\right\rangle.
$$

## 3.6 Coupling relation

At a communication point $T_k$, the coupling relation is written as

$$
u_i(T_k) = \Gamma_i\!\bigl(y_1(T_k),\ldots,y_N(T_k)\bigr).
$$

## 3.7 Input extrapolation

For zero-order hold, the extrapolated input is written as

$$
\hat{u}_i(t) = u_i(T_k),
\qquad
t \in [T_k,T_{k+1}).
$$

## 3.8 Algebraic-loop residual

For one algebraic loop $A \subseteq I$, the interface residual is written as

$$
\mathcal{R}(U_A) = U_A - \Gamma_A\!\bigl(Y_A(U_A)\bigr).
$$

---

# 4. Reserved Symbols and Naming Rules

The following conventions are fixed.

- $q$ is reserved for the discrete mode or discrete state.
- $z$ is reserved for algebraic variables.
- $g(\cdot)$ is reserved for algebraic constraints.
- $G(\cdot)$ is reserved for implicit residual formulations.
- $\gamma_j(\cdot)$ is reserved for event indicators.
- $k$ is reserved for communication-point indices.
- $\nu$ is reserved for superdense-time microstep indices.
- $R_j$ is reserved for event reset maps.
- $\delta_j$ is reserved for discrete-state update maps.
- $\mathcal{R}$ is reserved for algebraic-loop residuals.
- Internal subsystem step sizes are denoted by $\Delta t_{i,r}$, not by $h_i$.
- The abstract simulation-unit symbol is $\mathsf{SU}_i$, not $\Sigma_i$.

## Local example conventions

- Do not use $q_x,q_y$ for Cartesian pendulum coordinates because $q$ is reserved for the discrete mode.
- Prefer $r_x,r_y$ or $p_x,p_y$ for Cartesian position coordinates.

---

# 5. Mapping from Thesis Notation to Implementation

| Thesis concept | Thesis symbol | Implementation name |
|---------------|---------------|---------------------|
| Physical time | $t$ | `t` |
| Initial time | $t_0$ | `t0` |
| Final time | $t_f$ | `tf` |
| Macro step size | $H_k$ or $T_{k+1}-T_k$ | `dt` in `System.run()` and `Algorithm.step()` |
| Continuous state | $x_i$ | backend-internal state, exposed via `get_state()` / `set_state()` |
| Algebraic variables | $z_i$ | backend-internal variables, usually not explicit in `CoSimComponent` |
| Input | $u_i$ | `inputs`, `set_inputs()` |
| Output | $y_i$ | `outputs`, `get_outputs()` |
| Discrete mode | $q_i$ | backend-specific mode variables |
| Event indicator | $\gamma_{j}$ or $\gamma_{i,j}$ | `event_indicators[name]` |
| Direct feedthrough relation | $F_i$ | `direct_feedthrough` |
| Communication-point index | $k$ | implicit in simulation loop |
| Superdense-time index | $\nu$ | `DenseTime.micro` |
| Superdense time | $(t,\nu)$ | `DenseTime(t, micro)` |
| Execution generations | ordered generation sets | `execution_order` |
| Algebraic loops | cycle / loop block in zero-delay graph | `algebraic_loops` |
| Master algorithm | orchestration method | `system.algorithm` |

---

# 6. Practical Usage Rules

- Use the symbols in this document as the default notation for Chapter 2.
- If a local subsection introduces additional symbols, define only the symbols that are new in that subsection.
- If a symbol listed here is not used anymore in the thesis text, remove it from this document before regenerating the Chapter 2 notation table.
- Do not duplicate symbol choices in `research/guideline.md`; that file should refer here instead.
- When a theory subsection is revised, update this document first if the notation actually changes.
