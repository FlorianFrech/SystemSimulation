Gomes, C., Thule, C., Broman, D., Larsen, P. G., & Vangheluwe, H.  
**Co-Simulation: A Survey.** *ACM Computing Surveys (CSUR)*, 51(3), Article 49, 2018.  
https://doi.org/10.1145/3179993

### **1. Introduction Co-Simulation**

- **Core Concept:** Simulate a global system by composing multiple independent subsystems, each potentially using different simulation tools or solvers.
    - Computing the behavior of the combined models over time.
    - Each simulation unit with its own interface for getting, setting inputs/outputs and computing the behavior of its model over a given interval of time.
- **Tool Incompatibility:** Models from different tools are difficult to exchange and integrate
- **Interface Coupling:** Components exchange data through well-defined input/output interfaces
- **Master algorithm:** scheduling execution and communication of each co-simulation unit
    - representing a system assembled from models in various domains; each with their own appropriate simulator
	- black-box-models which hide internal details
- **Problem:** difficult to ensure that the results produced by a co-simulation can be trusted
    - communication frequency betweeen different differential-equation-based units
	- event propagation order
	- numerical properties of the participating units
	- users do not always know how to configure the co-simulation
- **Problem of algebraic loops:** Arise when differential-algebraic equation-based units are coupled
	- Solve algebraic loops by fixed point iteration
	- Requires simulation units support state rollback
	- OpenModelica exported FMUs do not support state rollback directly

### **2. Basics on Co-Simulation Algorithms**

#### **2.1 Dynamical systems and behavior**

- A **dynamical system** is an abstract model of a real system (physical or computational) characterized by:
	- state: $x(t)$  
	- inputs: $u(t)$  
	- outputs: $y(t)$  
	- evolution rules (typically ODEs/DAEs)

- **State–space representation:**
	- Continuous-time form (general):
		$$\dot{x} = f(x, u, t),\qquad y = g(x, u, t)$$
	- Where:
		- $\dot{x}$ denotes the time derivative of the state,
		- $f$ describes state evolution,
		- $g$ maps state and inputs to outputs.

- **Behavior:**
	- The behavior of the system is the set of trajectories $(x(t), y(t))$ that satisfy the evolution equations under a given experimental frame (assumptions, boundary conditions, input signals, etc.).
	- Simulation time $t$ is the independent time variable; it may run faster, slower, or equal to wall‑clock time depending on the simulator.

- **Simulator (solver):**
	- A simulator is a numerical algorithm that approximates trajectories $(x(t), y(t))$.
	- Accuracy depends on:
		- numerical method (e.g., explicit/implicit integrators),
		- step size and step control,
		- how continuous signals are represented and discretized (interpolation, sample-and-hold, etc.).

#### **2.2 Simulation Units and Co-Simulation**

A Simulation Unit (SU) packages:
- a dynamical system model (its equations, parameters, internal state), and

- a numerical solver,

behind a black-box interface with well-defined inputs and outputs. Given input trajectories $u_i(t)$, an SU produces output trajectories $y_i(t)$.

A co-simulation is a simulation of a coupled system composed from several SUs $S_i$ that:

- are treated as black boxes (internal details hidden),
- interact only via their input/output variables,
- may themselves be software solvers, real-time controllers, test benches, or physical hardware.

To obtain a global system trajectory, an orchestrator (or co-simulation master) is required to

- manage simulated time,
- schedule the SUs,
- route outputs to inputs according to a co-simulation scenario (connection graph).

The orchestrator + coupled SUs together behave like a single composite SU (a co-SU). This enables hierarchical setups: a co-simulation can itself be used as a building block inside a larger co-simulation.

#### **2.3 Continuous-Time Simulation Units and Communication Grid**

Continuous-time (CT) SUs internally integrate ODE/DAE systems.

Key notions:

- Each SU $S_i$ may uses its own internal step size $h_i$ and its own solver
- The orchestrator defines a communication grid with macro step size $H$

$$ t_n = t_0 + nH, \quad n = 0, 1, 2, \ldots $$

- At these communication times, SUs exchange inputs/outputs.

- Between $t_n$ and $t_{n+1}$ each SU advances independently using internal micro-steps, while seeing its input approximated over the macro step.

- A continuous-time simulation unit can be described as follows:

$$S_i = \langle X_i, U_i, Y_i, \delta_i, \lambda_i, x_i(0), \phi_{U_i} \rangle$$

where
 - $X_i, U_i, Y_i$ are the state, input, and output spaces,
 - $\delta_i$ is the internal state transition over one macro step (including its numerical solver),
 - $\lambda_i$ maps state and inputs to outputs,
 - $x_i(0)$ is the initial state,
 - $\phi_{U_i}$ is the interpolation/extrapolation scheme used to approximate $u_i(t)$ between communication points (e.g. zero-order hold, linear, higher order).


The co-simulation scenario consists of
- a set of SUs $D = \{ S_1, \ldots, S_N \}$,
- their external inputs/outputs,
- a set of coupling equations $L$ that relate outputs to inputs,
- interpolation functions $\phi_{U_{ext}}$ for external inputs.

### **3. Challenges in Continuous-Time Co-Simulation**

**Problem:** Even if each individual SU is valid and accurate, their composition is not automatically correct

- **Algebraic Constraints:** Physical coupling (e.g. rigid joints, action–reaction forces) yields algebraic equations that must hold across SUs (equal positions/velocities, force balance). With black-box SUs, enforcing these constraints is non-trivial and often requires sensitivities / Jacobians and rollback.

- **Algebraic loops**
    - Couplings can create cycles where variables depend (possibly nonlinearly) on themselves through other SUs.
    - Purely “input–input” loops are already delicate.
    - Loops involving states are more serious and may change the DAE index.
    - Ignoring these loops leads to large errors or instability; they typically require fixed-point or Newton-like iterations over the interface.

- **Accuracy and error control:** Error has several sources:
    - Internal solvers and micro step sizes $h_i$
    - Communication step size $H$
    - Input interpolation $\phi_{U_i}$
    - Reducing $H$ often improves accuracy, but not always; A co-simulation master needs some form of error assessment and possibly step size control.

- **Stability of the coupled system:** Stability is not just a property of each SU. It depends strongly on:
    - coupling topology,
    - orchestration scheme (Jacobi vs Gauss–Seidel vs iterative),
    - interpolation/extrapolation choice.
    - For linear systems, the stability can be studied via the spectral radius of the global error propagation matrix. Iterative schemes (dynamic iteration, IJCSA) often improve stability.

- **Continuity of inputs**
    - CT SUs expect continuous inputs. Piecewise constant extrapolation or sudden changes can:
        - reduce solver efficiency,
        - trigger reinitializations,
        - introduce artificial discontinuities that propagate through the system.

These challenges motivate more sophisticated master algorithms than simple explicit schemes. In the following, we summarize three central orchestration strategies used in this thesis: Jacobi, Gauss–Seidel, and the Interface Jacobian-based Co-Simulation Algorithm (IJCSA).

### **4. Classical Co-SImulation Algorithms**

In this section we consider one communication step from $t_n$ to $t_{n+1}$ with macro step size $H$.

Let
 - $S_i$ be SUs with internal state $x_i$, inputs $u_i$, and outputs $y_i$
 - $L(y, u, u_{ext})$ be a set of coupling equations relating all SU input/ouputs and any external inputs

 #### **4.1 Jacobi Co-Simulation Algorithm**

The Jacobi co-simulation algorithm is an **explicit, non-iterative** method where **all SUs are advanced in parallel** using input values from the previous communication point.

1. At communication time $t_n$, each SU has state $x_i^n$ and input $u_i^n$. The **inputs at the next step** $u_i^{n+1}$ are defined by the couplings using only outputs at time $t_n$ (explicit coupling).

2. For the next macro step:
    - The orchestrator freezes each SU's input as some extrapolated function (e.g., zero-order hold or linear).
    - All SUs integrate in **parallel** from $t_n$ to $t_{n+1}$ using these frozen inputs, producing new states $x_i^{n+1}$ and outputs $y_i^{n+1}$.
    $$
    x_i^{n+1} = \delta_i(t_n, x_i^n, u_i^{n}(\cdot)), \quad y_i^{n+1} = \lambda_i(t_{n+1}, x_i^{n+1}, u_i^{n+1})
    $$

3. At $t_n+1$, the new outputs $y_i^{n+1} are available and used to compute the inputs for the next step $u_i^{n+2}$ via the coupling equations.

**Properties:**
- Parallelism: All SUs can run concurrently between $t_n$ and $t_{n+1}$
- Simplicity: No interface iterations or rollback; suitable for loosely coupled systems.
- Phase lag / extrapolation error: Each SU sees “old” information about others; in closed loops this introduces effective delays and can degrade accuracy or stability.

#### **4.2 Gauss-Seidel Co-Simulation Algorithm**

The Gauss-Seidel scheme is sequential and uses the most recent information inside the macro step.

1. Fix an order of SUs, e.g., $S_1, S_2, \ldots  S_N$.

2. At communication time $t_n$:
 - $S_1$ is advanced first from $t_n$ to $t_{n+1}$ with inputs extrapolated from data at $t_n$ or earlier:
 
 $$x_1^{n+1}, y_1^{n+1} = \text{step}(S_1, x_1^n, u_1^{n}(\cdot))$$

3. $S_2$ is advanced next. Its inputs may now use $y_1^{n+1}$, which has just been updated by $S_1$.
Generally:
- Early SUs see *old* outputs from later SUs
- Later SUs see *new* outputs from earlier SUs

4. After all SUs have been advanced, time is increased to $t_{n+1}$.

**Properties**
- Reduced phase lag compared to Jacobi: some couplings use updated outputs within the same macro step.
- Potentially better stability for certain physical orderings (e.g. integrating light masses before heavy masses, or input–output chains in causality order).
- Loss of parallelism: SUs must be advanced sequentially in the chosen order.
- Order sensitivity: The chosen sequence can significantly affect accuracy and stability.
