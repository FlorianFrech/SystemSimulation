Sicklinger, S., Belsky, V., Engelmann, B., Elmqvist, H., Olsson, H., Wüchner, R., & Bletzinger, K. ‐U. (2014). Interface Jacobian‐based Co‐Simulation. *International Journal for Numerical Methods in Engineering*, *98*(6), 418–444. [https://doi.org/10.1002/nme.4637](https://doi.org/10.1002/nme.4637)

# Interface Jacobian-Based Co-Simulation
The **Interface Jacobian-based Co-Simulation Algorithm (IJCSA)** (Sicklinger, 2014) generalizes the excplicit schemes by applying a **Newton method at the interface level**, using the Jacobian of the interface constraints.

- Co-Simulation: each subsystem integrates its own equations internally
- Boundary variables (inputs/outputs) are exchanged at communication points
- Consistency as main challenge:
    - Each subsystem i produces outputs yi depending on its current states and inputs ui
    - inputs of each subsystem depend on other subsystems' output (via coupling equation)
- All simulators are interdependent and form potentially algebraic loops at the interface
- IJCSA introduces a residual-based iterative coupling using the jacobian of the interface equation to stabilize and accelerate convergence
- Core Idea of the Interface Jacobian-based Co-Simulation Algorithm (IJCSA)
    - develop an algorithm that can handle a co-simulation scenario of an arbitrary number number of codes (=simulation units) where additional interface conditions can be specified.
    - important property is to feature accurate and stable simulations
    - performance is critical: simulators need to be able to run in parallel without data flow dependence

## Interface Constraint Operator and Residual

Consider $N$ subsystems(SUs) with input vector $U_i$ and output vector $Y_i$.
Collect all interface inputs and outputs as:

$$U = \begin{bmatrix} U_1 \\ \vdots \\ U_N \end{bmatrix}, \quad
Y = \begin{bmatrix} Y_1 \\ \vdots \\ Y_N \end{bmatrix}$$
​
The couplings are expressed by a possibly nonlinear **interface constraint operator:**

$$L(U, Y) = 0$$

For a simple signall assignment coupling $U_i = Y_j$ for some $i, j$, the constraint operator can be described as:
$$L(U, Y) = U_i - Y_j$$

And the interface residual is defined as 
$$r = L(U, S(U)) = U_i - Y_j$$

where $S(U)$ denotes the composition of all SUs stepped over one macro interval with given interface inputs $U$, producing $Y$.

We are interested in finding interface inputs $U^*$ such that the residual vanishes:
$$r(U^*) = L(U^*, S(U^*)) = 0$$
This ensures that all coupling constraints are satisfied.

## Newton Iteration at the Interface

The IJCSA applies a Newton method in the space of the interface unknowns $U$ to solve $r(U) = 0$.

1. **Time loop** $t_n \to t_{n+1}$:
Given a current macro step $[t_n, t_{n+1}]$ and a previous solution $U^n$ (or a predictor), initialize the iteration with $U^{(0)} = U^n$

2. **Iteration Loop** for $m = 0, 1, 2, \ldots$:
    1. **Parallel subsystem evaluation:** For all SUs $S_i$ in parallel
        - Integrate internally from $t_n$ to $t_{n+1}$ using current input guess $U_i^{(m)}$ (and appropriate interpolation / extrapolation)
        - Obtain outputs $Y_i^{(m)}$ at $t_{n+1}$
    2. **Residual evaluation**: Evaluate the interface residual
        $$r^{(m)} = L(U^{(m)}, Y^{(m)})$$
        - If $\|r^{(m)}$ is below a tolerance accept $U_{n+1} = U^{(m)}$ and proceed to the next macro step.
    3. **Interface Jacobian Assembly**
        - Compute or approximate the Jacobian
        $$J^{(m)} = \frac{\partial r}{\partial U}\bigg|_{U^{(m)}} = \frac{\partial L}{\partial U} + \frac{\partial L}{\partial Y} \frac{\partial Y}{\partial U}$$
        - This involves contribution form the explicit interface constrain operator $L$, and
        - Local interface Jacobians $\frac{\partial Y_i}{\partial U_j}$ from each $SU$ (from directional derivative if FMU supports or via finite differences)
        - All these blocks are assembled into a global interface Jacobian matrix (dimension is equal to the number of interface unknowns)
    4. **Newton Update**: Solve the linear system
        $$J^{(m)} \Delta U^{(m)} = -r^{(m)}$$
        for the correction $\Delta U^{(m)}$, and optionally apply **relaxation for stability:**
        $$U^{(m+1)} = U^{(m)} + \alpha \Delta U^{(m)}, \quad 0 < \alpha \leq 1$$

3. **Carry over to the next step:**
 - After convergence, the consistent interface inputs $U^{n+1} = U^{(m)}$ can be used as
    - Final inputs for SUs at $t_{n+1}$
    - Initial guess for the next macro step.

**Properties:**
- Implicit coupling: By solving the interface constraints iteratively, IJCSA can handle algebraic loops and tightly coupled systems.
- Parallelism: Each iteration step evaluates all SUs in parallel.
- Jacobian requirement: Accurate Jacobians are crucial for convergence; finite difference approximations can be costly.

**Iteration Sequence for the Newton Method**

$$^{m+1} \mathbf{\phi} = ^{m} \mathbf{\phi} - J(\mathbf{r}(^{m} \mathbf{\phi}))^{-1} \mathbf{r}(^{m} \mathbf{\phi}) $$


$$ J(\mathbf{r}(^{m} \mathbf{\phi}))\underbrace{\left(^{m+1}\mathbf{\phi} - ^{m} \mathbf{\phi}\right)}_{\Delta^{m+1} \mathbf{\phi}} = - \mathbf{r}(^{m} \mathbf{\phi})$$


$$ J(\mathbf{r}(^{m} \mathbf{\phi})) \Delta^{m+1} \mathbf{\phi} = - \mathbf{r}(^{m} \mathbf{\phi})$$

$$ \mathbf{\phi}=\left[\begin{matrix}U_1\\U_2\\\end{matrix}\right],\quad \mathbf{r}=\left[\begin{matrix}R_1\\R_2\\\end{matrix}\right]
$$

where
 - $\mathbf{\phi}$ is the vector of unknowns
 - $\mathbf{r}$ is the residual vector
 - $J$ is the Jacobian operator (dimension only dependent on number of input vraiables at the interface level)
 - $m$ is the iteration index

**Linear Interface System for the Newton Method**

$$
J(r(^{m}\phi)) =
\left[
\begin{matrix}\frac{\partial R_1}{\partial U_1}&\frac{\partial R_1}{\partial U_2}\\
\frac{\partial R_2}{\partial U_1}&\frac{\partial R_2}{\partial U_2}\\
\end{matrix}
\right]
=
\left[
\begin{matrix}\frac{\partial I_1}{\partial U_1} & \frac{\partial I_1}{\partial U_2}\\
\frac{\partial I_2}{\partial U_1} & \frac{\partial I_2}{\partial U_2}\\
\end{matrix}
\right]
=
\left[
\begin{matrix}\frac{\partial (U_1 - Y_2)}{\partial U_1}&\frac{\partial (U_1 - Y_2)}{\partial U_2}\\
\frac{\partial (U_2 - Y_1)}{\partial U_1} & \frac{\partial (U_2 - Y_1)}{\partial U_2}\\
\end{matrix}
\right]
=
\left[
\begin{matrix}\ I & -\frac{\partial (Y_2)}{\partial U_2}\\
-\frac{\partial (Y_1)}{\partial U_1} & I\\
\end{matrix}
\right]
$$

$$
\left[
\begin{matrix}\ I & -\frac{\partial (Y_2)}{\partial U_2}\\
-\frac{\partial (Y_1)}{\partial U_1} & I\\
\end{matrix}
\right] 

\left[
\begin{matrix} \Delta U_1 \\ \Delta U_2 \end{matrix}
\right] 

= 

- \left[
\begin{matrix} \Delta R_1 \\ \Delta R_2 \end{matrix}
\right]

$$

## Practical Considerations for FMU-based Co-Simulation

**Availability of directional derivatives**
- If CS-FMUs provide fmi2GetDirectionalDerivative, local interface Jacobians $\frac{\partial Y_i}{\partial U_j}$ can be evaluated efficiently
- Otherwise, finite difference approximations can be used at the cost of extra FMU evaluations.

**FMU state management**
- A conceptually clean interface Newton step assumes one can:
    - Save the FMU state at $t_n$,
    - perform trial macro steps with different inputs,
    - rollback to the saved state when needed.

- **FMI 2.0**
    - offers getFMUstate/setFMUstate, but many tools (such as your OpenModelica-generated CS-FMUs) do not support them.
    - In such cases, one must emulate rollback by re-initializing the FMU and reapplying consistent start conditions, or design the iteration so that it only uses local output evaluations at fixed time with 
    - $dt = 0$(no state advancement), combined with careful handling of direct feedthrough.

**Use of ModelStructure**
 - Detect which outputs have direct feedthrough from which inputs,
 - Identify algebraic loops (cycles where outputs depend directly on current inputs),
 - Focus the Jacobian on the subset of variables that actually participate in interface constraints.

 -----

 ## Contractivity vs. Local Regularity

 Both conditions describe when an algebraic-loop solver can find a consistent coupling state. They differ in how much the underlying map has to behave.

1) What "contractive loop gain" means
Let $T(U_A) = \Gamma_A(Y_A(U_A))$ be the loop-gain map — starting from a trial input vector, run the simulation units, route their outputs back to inputs, and see what the inputs would become. A fixed point $U^*$ satisfies $U^* = T(U^*)$.

$T$ is contractive on a region if there is a constant $L < 1$ with
$$|T(U) - T(V)| \le L,|U - V|.$$
For smooth $T$, this is locally equivalent to the spectral radius of its Jacobian being strictly less than one,
$$\rho(G) < 1,\qquad G = \frac{\partial T}{\partial U_A}.$$

Why it matters for fixed-point iteration. The scheme
$$U_A^{(k+1)} = T(U_A^{(k)})$$
has error dynamics $e^{(k+1)} \approx G,e^{(k)}$. If $\rho(G) \ge 1$, the error does not shrink and the iteration fails.

Concrete example — the §5.6 verification scenario
The Inner subtractor and its self-connection give
$$d = p - n,\qquad n = d\ \ \Rightarrow\ \ T(n) = p - n.$$
So
$$G = \frac{\partial T}{\partial n} = -1,\qquad \rho(G) = 1.$$
The loop is not contractive. Fixed-point substitution starting from $n^{(0)} = 0$ with $p = 1$ gives
$$n^{(0)}=0,\ n^{(1)}=1,\ n^{(2)}=0,\ n^{(3)}=1,\ldots$$
It oscillates forever. This is the failure mode Newton is introduced to avoid.

Compare: if the Inner block were $d = 0.5,p - 0.5,n$ instead, then $G = -0.5$ and $\rho(G) = 0.5 < 1$. Fixed-point iteration would converge geometrically. So whether plain substitution works depends entirely on a property of the loop itself, not of the solver.

2) What "local regularity" (nonzero determinant) means
The residual is
$$\mathcal{R}(U_A) = U_A - T(U_A),\qquad \frac{\partial \mathcal{R}}{\partial U_A} = I - G.$$
The solver is locally regular at $U^*$ if this matrix is invertible,
$$\det(I - G(U^*)) \neq 0,$$
equivalently, $1$ is not an eigenvalue of $G(U^*)$.

Why it matters for Newton. The update
$$U_A^{(k+1)} = U_A^{(k)} - (I - G^{(k)})^{-1},\mathcal{R}(U_A^{(k)})$$
only requires that you can invert $I - G$ near the solution. It does not require $\rho(G) < 1$.

Same scenario, Newton side
$$\mathcal{R}(n) = n - (p - n) = 2n - p,\qquad J = \frac{\partial \mathcal{R}}{\partial n} = 2.$$
$\det J = 2 \neq 0$, so the system is locally regular, even though the loop was not contractive. One Newton step from $n^{(0)} = 0$:
$$n^{(1)} = 0 - \frac{2 \cdot 0 - 1}{2} = \tfrac{1}{2}.$$
This matches the analytical solution and the debug log in Listing~\ref{lst:ijcsa_verification_log}.

A 2D view of "determinant nonzero"
Two linearly coupled simulation units with
$$y_A = a,u_A,\quad y_B = b,u_B,\quad u_A = y_B,\quad u_B = y_A$$
produce loop-gain matrix
$$G = \begin{pmatrix} 0 & a \ b & 0 \end{pmatrix},\qquad I - G = \begin{pmatrix} 1 & -a \ -b & 1 \end{pmatrix},\qquad \det(I - G) = 1 - ab.$$

Newton works whenever $ab \neq 1$, i.e. any case except a unit-gain cycle.
Fixed-point iteration works only when $|ab| < 1$ (spectral radius of $G$ is $\sqrt{|ab|}$).
So contractivity demands $|ab| < 1$. Regularity only rules out $ab = 1$. The gap between them is exactly the set of loops where Newton succeeds and simple substitution does not.

3) The hierarchy in one table
Property	Formal condition	Verification scenario
Contractive $T$	$\rho(G) < 1$	Fails — $\rho(G) = 1$
Regular $I - G$	$\det(I - G) \neq 0$	Holds — $\det = 2$
Local regularity is strictly weaker than contractivity. Every contractive loop is regular, but many regular loops are not contractive. This is why §2.3.5 says the Newton-type treatment replaces the contractivity requirement with local regularity.

Singularity of $I - G$ corresponds to $1 \in \operatorname{spec}(G)$. The two textbook cases are

identity feedback $y = u$, giving $G = I$ and $I - G = 0$,
a unit-gain cycle where the product of loop gains around the cycle equals one.