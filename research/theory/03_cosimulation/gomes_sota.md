co_simulation_sota_gomes

**Co-simulation: a Survey**

- Modeling and simulation techniques are today extensively used both in industry and science
- larger systems are typically modeled and simulated by different, techniques, tools, and algorithms
- Experts from different disciplines use various modeling and simulation techniques
- This makes it difficult to study coupled heterogeneous systems
- Co-Simulation: technique where global simulation of a coupled system can be achieved by composing the simulation of its parts

**1 Introduction**

- Modern engineered systems are **highly complex**, integrating physical, software, and network aspects, and are developed **concurrently and distributed** across many teams and suppliers.
- Each party builds only a **partial solution** with its own tools; integrating these parts late in the process is costly and risky.
- **Holistic, iterative integration** of partial solutions early and often is needed to check requirements, explore design alternatives, and study interactions across subsystems.
- Modeling and simulation help at the **partial-solution level**, but:
    
    - Models from different tools are **hard to exchange/integrate**.
    - External models may hide details due to **IP protection**.
    - System validation often requires coupling models with **physical prototypes, software, and human operators** (Model/Software/Hardware/Human-in-the-loop).
- A single monolithic model of a large system is often **impractical**, so we need to integrate multiple interacting simulators.
- **Co-simulation** = simulating a global system by **composing simulators** that:
    
    - are treated as **black boxes**,
    - exchange inputs/outputs over a coupling interface,
    - can be numerical solvers, real-time hardware, test stands, or human-in-the-loop setups.
- To structure the discussion, the paper distinguishes:
    
    - **Discrete Event (DE)** co-simulation (Section 3),
    - **Continuous Time (CT)** co-simulation (Section 4),
    - and **hybrid / mixed DE–CT** co-simulation (Section 5),

**2 Modeling, Simulation, and Co-Simulation**

- **Dynamical system**
    
    - Abstract model of a real system (physical or computational) with:
        
        - a **state** and
        - **evolution rules** (e.g. traffic light changing color, mass–spring–damper ODEs).
- **Behavior trace**
    
    - The set of trajectories of states/outputs over (simulated) time.
    - Time variable t is **simulated time**, distinct from **wall-clock time**.
    - Relationship between simulated and real time can be:
        
        - faster than real-time, slower, equal (α = 1), or paused.
- **Experimental frame**
    
    - Describes the **assumptions and conditions** under which a dynamical system is observed.
    - Validity = how well the behavior trace of the model matches that of the real system under the same experimental frame.
    - This is what gives simulations **predictive power**.
- **Simulation / solver**
    
    - A **simulator** (solver) is an algorithm that computes an approximation of the behavior trace.
    - Two ways to obtain behavior: analytic solution vs numerical approximation (simulation).
    - Errors arise from:
        
        - numerical approximation, and
        - discrete representation of continuous behavior.
    - An **accurate simulator** has errors below a given bound; accuracy is a property of the simulator.
- **Simulation unit (SU)**
    
    - An SU = **simulator + dynamical system** packaged as something that, given inputs, produces behavior.
    - The simulated behavior trace produced by an SU is called a **simulation**.
    - SUs can represent pure software models or interfaces to real-world entities (hardware, humans, etc.).
- **Co-simulation**
    
    - A **co-simulation** is a simulation composed from **multiple SUs** coupled via input/output signals.
    - Each SU is treated as a **black box**; only its interface is visible.
    - An **orchestrator** is needed to:
        
        - schedule SUs,
        - advance their simulated times,
        - route outputs to inputs according to a **co-simulation scenario** (how they are interconnected).
- **Co-simulation scenario & co-SU**
    
    - A **co-simulation scenario** bundles:
        
        - the SUs,
        - their couplings,
        - and the orchestration rules needed for a correct co-simulation.
    - The orchestrated composition behaves like a single SU, called a **co-SU**:
        
        - a “virtual simulator” for the coupled system,
        - enabling **hierarchical** co-simulation (co-SUs can be coupled again).
- **Correctness, validity, accuracy**
    
    - Correctness of an SU depends on:
        
        - accuracy of the simulator,
        - validity of the dynamical system model.
    - In co-simulation, correctness also depends on the **orchestration** and coupling.
- **Black-box constraint and information**
    
    - The survey mainly considers SUs as **black boxes** (internal models hidden, often for IP reasons).
    - Some properties (e.g., compositional correctness) may require **relaxing** this strict black-box view to access extra information (e.g., Jacobians, structure).
- **Compositionality challenge**
    
    - Many co-simulation challenges relate to **compositionality**:
        
        - If each SU satisfies property P, does the composed co-SU also satisfy P?
    - Desired properties include correctness, validity, and accuracy.
    - Ensuring compositional guarantees for a given set of properties is an open research problem.
- **Outlook of the survey**
    
    - Subsequent sections classify techniques and information used to tackle these issues.
    - Co-simulation approaches are grouped into:
        
        - **Discrete-event** co-simulation,
        - **Continuous-time** co-simulation,
        - **Hybrid** co-simulation (DE + CT).

**4 Continuous-Time Based Co-Simulation**

**4.1 CT Simulation Units**

- A **CT Simulation Unit (CT SU)** represents a dynamical system whose **state evolves continuously in time**.
- Example: a **mass–spring–damper** with state = displacement x1​ and velocity v1​; dynamics given by ODEs and an external input force Fe.
- A CT SU’s behavior is thus **similar to a numerical ODE solver** computing the state trajectory over time.
- CT SUs are often **mock-ups of CT systems**, but the concept also covers real solvers; e.g., an SU that simulates the mass–spring–damper takes input $F_e(t)$, integrates the ODEs with a step $h$
- and outputs the new state $[x(t+h), v(t+h)]^\top$.
- If $f(x,u)$ is sufficiently differentiable, $x$ can be approximated with a truncated Taylor series
- SU is assumed to have a behavior that is similar to one of a numerical solver computing a set of differential equations

**4.2 CT Co-Simulation Orchestration**

- **Different internal step sizes:**
    
    - Each CT Simulation Unit (SU) uses its own micro-step size hi.
    - To couple them, an orchestrator defines a **communication step size** H(macro step or communication grid) at which SUs exchange inputs / outputs.
- **Need for input extrapolation / interpolation:**
    
    - During one macro step an SU advances with many micro-steps.
    - Its inputs are only known at communication times, so the orchestrator (or the SU) uses an **extrapolation / interpolation function** to approximate $u_i(t)$ for intermediate times.
    - **Common schemes:** constant, linear, polynomial, extrapolated interpolation, context-aware, estimated dead-reckoning, etc.
    - Quality of these schemes strongly affects co-simulation accuracy.
- **Formal CT-SU behavior in co-simulation:**
    
    - Each SU $S_i$ is described by $S_i = \langle X_i, U_i, Y_i, \delta_i, \lambda_i, x_i(0), \phi_{U_i} \rangle$, where
        
        - $X_i$​: state space, $U_i$​: input space, $Y_i$​: output space
        - $\delta_i$: state transition over one macro step using inputs (with extrapolation)
        - $\lambda_i$​: output function,
        - $x_i(0)$: initial state,
        - $\phi_{U_i}$​​: input approximation functions.
- **CT co-simulation scenario:**
    
    - A scenario includes:
        
        - the set of ordered SUs $D = \{S_1,\ldots,S_n\}$},
        - the external input and output spaces,
        - a set of **coupling equations** L that relate SU outputs to inputs (connection graph),
        - the input approximation functions $\phi_{U_{cs}}$ ​​ for external inputs.
- **Jacobi (parallel) orchestration:**
    
    - Generic **Jacobi scheme** (Algorithm 3):
        
        1. At time $t$, solve the algebraic system for unknown outputs/inputs  
            $y_i = \lambda_i(t, x_i, u_i)$ and couplings $L(y_1,\dots,y_n,u_1,\dots,u_n,u_{cs}) = 0$
        2. With the resolved inputs $u_i$​, instruct each SU to advance its state:  
            $x_i \leftarrow \delta_i(t, x_i, u_i)$
        3. Increase time $t \leftarrow t+H$ and repeat.
    - All SUs advance **in parallel** from the same time $t$ to $t+H$, using extrapolated inputs.
- **Gauss–Seidel (sequential) orchestration:**
    
    - Alternative scheme: SUs are advanced in sequence; some SUs use **already updated** outputs of others at time $t+H$.
    - Allows more accurate use of current outputs instead of extrapolations, but reduces parallelism.
- **Orchestrator as a co-SU:**
    
    - The orchestrator + coupled SUs together behave as a **composite SU (co-SU)** with:
        
        - state = product of all SU states,
        - inputs = scenario external inputs,
        - outputs = scenario outputs,
        - transition/output logic implemented by the orchestrator.
    - This enables **hierarchical co-simulation** (co-SUs can be coupled again like regular SUs).
- **Black-box coupling and limitations:**
    
    - Orchestration can work with **very limited internal knowledge** of SUs (black-box assumption).
    - However, such blind coupling can cause **compositionality and stability problems**, motivating techniques that access more information from SUs (e.g., Jacobians, structural info) in later sections.

**4.3 Challenges**

- **Modular composition & algebraic constraints**
    
    - When subsystems are coupled through physical constraints (e.g., rigid links), the coupling is not just simple signal assignments.
    - Constraints like equal positions/velocities and action–reaction forces lead to **algebraic equations** that must be satisfied across SUs.
    - Under a black-box assumption this is hard; frameworks often need **sensitivities (derivatives) of outputs w.r.t. inputs** and rollback capabilities to enforce constraints.
- **Algebraic loops**
    
    - Occur when variables indirectly depend on themselves through the coupling.
    - Two types:
        
        - Loops involving only **input variables**.
        - Loops involving **states as well** (more serious).
    - Neglecting loops can cause large errors; must use **fixed-point (Newton-like) iterations**, possibly with rollback, to solve them.
    - Variants: dynamic iteration, waveform iteration, strong/onion coupling; trade-off between accuracy and computational cost.
    - Current FMI co-simulation (step mode) doesn’t fully support this; strong coupling on outputs is a common workaround.
- **Consistent initialization of simulators**
    
    - Each SU has its own initial state, but algebraic constraints across SUs impose extra conditions at t=0t=0t=0.
    - Need to solve an **initialization problem** (co-initialization) so all SUs start from a state consistent with the coupling constraints; may again involve algebraic loops and fixed-point iterations.
- **Compositional convergence & error control**
    
    - Error comes from solver, micro-step size, communication step size H, and input extrapolation.
    - Larger $H$ generally → larger extrapolation error; but decreasing H doesn’t always guarantee better global accuracy due to non-Lipschitz behavior of the coupled system.
    - For **convergent co-SUs**, classical numerical techniques can **estimate and control error**:
        
        - Richardson extrapolation, multi-order input extrapolation, embedded methods, conservation laws, etc.
    - Once error exceeds a threshold, corrections can be applied pessimistically (rollback & repeat step) or optimistically (adapt next step), possibly only for sensitive SUs.
- **Compositional stability**
    
    - Stability of the co-simulation depends on coupling method and extrapolation choices, not just individual SUs.
    - Spectral-radius analysis of the error dynamics can be used for linear cases.
    - Rules of thumb:
        
        - Co-simulators with **fixed-point iterations** tend to be more stable.
        - **Gauss–Seidel** ordering can improve stability if done with a physically meaningful order (e.g., heavy masses later).
- **Compositional continuity**
    
    - If a CT SU models a continuous system, its inputs should also be continuous.
    - Poorly chosen input extrapolation (e.g., piecewise constant) or sudden input changes can:
        
        - harm solver performance (step size reductions, re-initialization),
        - discard useful history (multi-step methods),
        - introduce spurious discontinuities that propagate to other SUs.
    - Using **higher-order / smooth interpolation** helps preserve continuity.
- **Real-time constraints, noise, and delay**
    
    - In real-time co-simulation, SUs must satisfy $t_\text{wall} = \alpha t_\text{sim}$​ (often $\alpha = 1$), which is harder with many heterogeneous SUs.
    - Some SUs may be physical devices; their measurements are noisy and delayed, and extrapolation must be robust (e.g., Kalman filtering).
    - Network latency and jitter create **delays**; the orchestrator needs strategies (prediction, buffering, compensation) so that real-time SUs still receive inputs on time.