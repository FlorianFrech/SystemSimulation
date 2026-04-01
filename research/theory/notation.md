# Notation

## Purpose

This file defines the mathematical notation used consistently throughout the thesis.
The goal is not to mirror Python variable names literally, but to establish a stable
conceptual mapping between the theory chapters and the *SysSimX* implementation.

## General Principles

- A **system** is decomposed into **subsystems** indexed by $i$.
- Continuous-time variables are functions of physical time $t$.
- Differential states are denoted by $x(t)$.
- Algebraic variables are denoted by $z(t)$.
- Discrete modes or discrete states are denoted by $q(t)$.
- Inputs and outputs are denoted by $u(t)$ and $y(t)$.
- Communication points in co-simulation are indexed by $k$.
- Superdense-time microstep indices are denoted by $\nu$.

Vectors are denoted by symbols such as $x$, $z$, $u$, and $y$; individual components
are written with subscripts.

## Indices and Time

| Symbol | Meaning | Usage |
|--------|---------|-------|
| $t$ | Physical time | Continuous-time and hybrid evolution |
| $t_e$ | Event time | Time at which an event occurs |
| $i$ | Subsystem or component index | Co-simulation and coupled models |
| $j$ | Event or indicator index | Hybrid-system event definitions |
| $k$ | Communication-point index | Co-simulation |
| $\nu$ | Superdense-time microstep index | Hybrid event ordering at fixed physical time |
| $T_k$ | Communication point $k$ | Co-simulation communication grid |
| $H_k = T_{k+1} - T_k$ | Macro step size | Communication interval |
| $H$ | Constant macro step size | Use only when the communication step is fixed |
| $\Delta t_{i,r}$ | Internal step size of subsystem $i$ at local step $r$ | Micro-stepping inside a subsystem |

## Continuous-Time and DAE Models

The time argument $(t)$ is declared in prose on first introduction and omitted
inside equations. It is written explicitly only when a named time instant
$(t_0, T_k, t_e)$ is referenced.


### Explicit state-space form

A continuous-time subsystem is written as

$$
\dot{x}(t) = f(x(t),u(t),t),
\qquad
y(t) = h(x(t),u(t),t).
$$

Here:

- $x(t)$ is the differential state
- $u(t)$ is the input
- $y(t)$ is the output
- $f$ is the state-transition map
- $h$ is the output map

### Implicit and semi-explicit DAE form

A general implicit DAE is written as

$$
0 = G(\dot{x}(t),x(t),z(t),u(t),t).
$$

A semi-explicit DAE is written as

$$
\dot{x}(t) = f(x(t),z(t),u(t),t),
\qquad
0 = g(x(t),z(t),u(t),t),
\qquad
y(t) = h(x(t),z(t),u(t),t).
$$

Here:

- $x(t)$ are differential states
- $z(t)$ are algebraic variables
- $g(\cdot)$ denotes algebraic constraints
- $G(\cdot)$ denotes an implicit DAE residual form

## Hybrid-System Notation

A hybrid subsystem is represented by

$$
\bigl(q(t),x(t),z(t),u(t),y(t)\bigr),
$$

where:

- $q(t)$ is the discrete mode or discrete state
- $x(t)$ is the continuous state
- $z(t)$ are algebraic variables
- $u(t)$ is the input
- $y(t)$ is the output

Between events, the active mode defines the continuous-time model:

$$
0 = G_{q(t)}(\dot{x}(t),x(t),z(t),u(t),t),
\qquad
y(t) = h_{q(t)}(x(t),z(t),u(t),t).
$$

Event indicators are denoted by

$$
\gamma_j(x(t),z(t),q(t),u(t),t).
$$

An event occurs when $\gamma_j = 0$.

Event update maps are written as

$$
x^{+} = R_j(x^{-},z^{-},q^{-},u^{-},t_e),
\qquad
q^{+} = \delta_j(x^{-},z^{-},q^{-},u^{-},t_e).
$$

Superdense time is represented by

$$
(t,\nu),
$$

where $t$ is the physical time and $\nu$ orders multiple discrete updates at the
same physical time.

## Co-Simulation Notation

Subsystem $i$ is described by

$$
\dot{x}_i(t) = f_i(x_i(t),z_i(t),u_i(t),t),
\qquad
0 = g_i(x_i(t),z_i(t),u_i(t),t),
\qquad
y_i(t) = h_i(x_i(t),z_i(t),u_i(t),t).
$$

At communication points $T_k$, subsystem outputs are exchanged through coupling relations.
A generic coupling operator is written as

$$
u(T_k) = \Gamma(y(T_k)).
$$

If needed, interface residuals for algebraic-loop resolution are written as

$$
\mathcal{R}(U) = 0,
$$

where $U$ denotes the stacked interface unknowns.

Direct feedthrough means that the current output $y_i(T_k)$ depends directly on the
current input $u_i(T_k)$.

An algebraic loop is present when direct feedthrough dependencies create a closed cycle
of simultaneous interface equations.

## Reserved Symbols

To avoid collisions, the following conventions are fixed.

- $q$ is reserved for the discrete mode or discrete state.
- $z$ is reserved for algebraic variables.
- $g(\cdot)$ is reserved for algebraic constraints.
- $\gamma_j(\cdot)$ is reserved for event indicators.
- $k$ is reserved for communication-point indices.
- $\nu$ is reserved for superdense-time microstep indices.
- $R_j$ is reserved for event reset maps.
- $\mathcal{R}$ is reserved for algebraic-loop residuals.
- $h(\cdot)$ is reserved for output maps.
- Therefore internal subsystem step sizes are not denoted by $h_i$, but by $\Delta t_{i,r}$.

## Local Example Conventions

To avoid collisions with the global notation, local coordinates in examples should not
reuse reserved symbols.

- Do not use $q_x,q_y$ for Cartesian pendulum coordinates because $q$ is reserved for the discrete mode.
- Prefer $r_x,r_y$ or $p_x,p_y$ for Cartesian position coordinates.

## Mapping from Thesis Notation to Implementation

| Thesis concept | Thesis symbol | Implementation name |
|---------------|---------------|---------------------|
| Physical time | $t$ | `t` |
| Initial time | $t_0$ | `t0` |
| Final time | $t_f$ | `tf` |
| Current communication interval | $H_k$ or $T_{k+1}-T_k$ | `dt` in `System.run()` and `Algorithm.step()` |
| Left and right interval boundary | $T_k$, $T_{k+1}$ | `t_left`, `t_right` in `HybridAlgorithm` |
| Continuous state | $x_i$ | backend-internal state, exposed via `get_state()` / `set_state()` |
| Algebraic variables | $z_i$ | backend-internal variables, usually not explicit in `CoSimComponent` |
| Input | $u_i$ | `inputs`, `set_inputs()` |
| Output | $y_i$ | `outputs`, `get_outputs()` |
| Discrete mode | $q_i$ | backend-specific mode variables |
| Event indicator | $\gamma_{i,j}$ | `event_indicators[name]` |
| Direct feedthrough relation | direct dependency of $y_i$ on $u_i$ | `direct_feedthrough` |
| Communication-point index | $k$ | implicit in simulation loop, not stored explicitly |
| Superdense-time index | $\nu$ | `DenseTime.micro` |
| Superdense time | $(t,\nu)$ | `DenseTime(t, micro)` |
| Execution generations | conceptual ordered sets | `execution_order` |
| Algebraic loops | SCCs of zero-delay dependency graph | `algebraic_loops` |
| Master algorithm | orchestration method | `system.algorithm` |

## Practical Naming Rules

- Keep `t`, `t0`, `tf`, and `dt` in Python code. They are idiomatic and already stable.
- Keep `inputs`, `outputs`, `direct_feedthrough`, `event_indicators`, `execution_order`,
  and `algebraic_loops` in the implementation.
- Use $z$ in theory-facing notes, derivations, and future math-heavy code comments for
  algebraic variables; avoid introducing a competing generic variable $w$.
- Do not use bare $n$ for superdense microsteps in theory text. Use $\nu$.
- In theory text, reserve $q$ for discrete modes only.
- In theory text, use $\gamma_j$ for event indicators and $g$ only for algebraic constraints.
- In theory text, use $G_q$ for implicit hybrid dynamics, not $F_q$, to avoid conflicts
  with force notation in mechanical examples.

## Immediate Thesis-Level Cleanup Targets

The most important notation harmonizations for the current draft are:

1. Replace $w$ by $z$ for algebraic variables.
2. Replace $g_j$ by $\gamma_j$ for event indicators.
3. Replace $(t,n)$ by $(t,\nu)$ for superdense time.
4. Replace $q_x,q_y$ by $r_x,r_y$ or $p_x,p_y$ in the Cartesian pendulum example.
5. Replace $F_q$ by $G_q$ in the hybrid-system equations.
