# Solver Notes for the Case Study

This note summarizes the solver facts needed for Chapter 6.
It is background material for writing the thesis, not thesis text.

## Scope in the Thesis

The solver discussion in Chapter 6 should stay short.
Section 6.4 should report the solvers and the simulation options used for the
reference trajectories and for the FMUs.
It should not derive DASSL, CVODE, BDF methods, or nonlinear solver internals.

Use solver details only to explain reproducibility or interpretation.
The relevant interpretation points are:

- The OpenModelica reference trajectories are numerical references, not
  experimental ground truth.
- DASSL selects internal time steps adaptively.
- The stored `stepSize` option defines the output spacing of the exported
  reference trajectory.
- The FMU internal solver is separate from the co-simulation macro step.
- The Euler-based PID FMU is a special case used for reset handling.

## DASSL in OpenModelica

Role in the thesis:

- Used for monolithic OpenModelica reference simulations.
- Used for the baseline and rigid-contact references.

Main characteristics:

- DASSL is the default OpenModelica solver.
- It is an implicit, higher-order, multistep method.
- It is based on backward differentiation formulas.
- It is intended for stiff systems and differential-algebraic systems.
- OpenModelica lists DASSL with adaptive order 1 to 5 and adaptive step size.
- Internal nonlinear and linear systems are solved by dense methods unless
  other solver options are selected.

Simulation options used for the reference export:

```text
startTime = 0
stopTime = 2        # baseline
stopTime = 1        # contact reference
stepSize = 0.001
tolerance = 1e-06
solver = dassl
outputFormat = mat
```

Thesis wording should make clear that `stepSize` is the exported output spacing.
It should not be described as a prescribed internal DASSL step size unless an
OpenModelica flag such as `maxStepSize` was explicitly used.

## CVODE in the FMUs

Role in the thesis:

- Used as the default internal solver for the exported Co-Simulation FMUs.
- Used inside the FMU pendulum and other continuous FMU components unless a
  scenario states otherwise.

Main characteristics:

- CVODE is part of SUNDIALS.
- It solves ordinary differential equation initial value problems.
- It uses variable-order, variable-step multistep methods.
- In OpenModelica, the stiff default uses BDF with order 1 to 5.
- The default nonlinear solver is a modified Newton iteration with fixed
  Jacobian.
- For non-stiff problems, an Adams-Moulton method with order 1 to 12 can be
  selected.

Thesis wording should distinguish the FMU internal solver step size from the
co-simulation communication step.
The macro step is controlled by the master algorithm.
CVODE selects internal steps inside each FMU step.

## Euler-Based PID FMU

Role in the thesis:

- Used only for the PID controller variant with reset handling.

Main characteristics:

- Explicit Euler is a fixed-step, first-order solver.
- The reset-capable PID FMU uses this variant because the reset input is
  applied through a zero-duration event-handling step.
- This is an implementation choice for the case-study setup, not a general
  solver recommendation.

## Suggested Thesis Citations

Use these sources depending on the level of detail.

- OpenModelica User's Guide, "Solving Modelica Models".
  Use this as the main citation for the solver characteristics as implemented
  and exposed by OpenModelica.
- Petzold, "A description of DASSL: A differential/algebraic system solver",
  1982.
  Use this if the thesis states the original DASSL algorithm background.
- Hindmarsh et al., "SUNDIALS: Suite of nonlinear and differential/algebraic
  equation solvers", ACM Transactions on Mathematical Software, 2005.
  Use this if the thesis states CVODE as part of SUNDIALS.
- Fritzson et al., "The OpenModelica Modeling, Simulation, and Development
  Environment", 2005.
  Use this only when citing OpenModelica as the modeling and simulation
  environment, not for specific solver properties.

## Suggested Short Thesis Text

```latex
The OpenModelica reference simulations use DASSL.
OpenModelica characterizes DASSL as an implicit BDF-based multistep solver with
adaptive order and adaptive step-size control.
The exported reference trajectories use
\(\texttt{startTime}=0\), \(\texttt{stepSize}=10^{-3}\,\mathrm{s}\),
\(\texttt{tolerance}=10^{-6}\), \(\texttt{solver}=\texttt{dassl}\), and
\(\texttt{outputFormat}=\texttt{mat}\).
The baseline reference uses \(\texttt{stopTime}=2\), while the contact
reference uses \(\texttt{stopTime}=1\).
The stored step size defines the output spacing of the reference trajectory.
DASSL selects its internal integration steps adaptively.
```

```latex
The Co-Simulation FMUs use CVODE as their default internal solver.
In OpenModelica, CVODE is a SUNDIALS solver for ODE initial value problems and
uses variable-order, variable-step multistep methods.
The exported stiff configuration uses BDF with order 1 to 5.
The co-simulation macro step is set by the master algorithm and is separate
from the FMU internal solver steps.
```
