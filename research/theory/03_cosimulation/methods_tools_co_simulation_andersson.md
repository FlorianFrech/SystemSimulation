methods_tools_co_simulation_andersson

# **Summary:**

**Part 1:**

**1\. Motivation and Background**

- Different tools use different ways to model and store system data
- FMI (Functional Mock-up Interface) was developed to enable tool independent model exchange and co-simulation
- FMUs allow to create a model in one tool, connect it in another, and simulate it in a third

**2\. Coupled Systems and Co-Simulation**

- Strong coupling: complete access to model equations, monolithic solvers
- Weak coupling (co-simulation): models exchange only inputs/outputs at discrete points
    
    - Allows parallel execution of models
    - Tailored solvers per domain -> electrical vs. mechanical
    - Different time scales are supported
- Challenges of weak coupling: numerical stability, synchronization, consistent communication

**3\. FMI and FMUs**

- FMI standard defines:
    
    - Model exchange FMU: requires an external solver
    - Co-Simulation FMU: includes internal solver, only interface needed is discrete time stapping
- Features:
    
    - Event handling (state, time, step)
    - Initialization support
    - Directional derivatives -> analytical Jacobian
    - Save/load state -> for rollbacks
    - Higher-order input / output derivatives
    - Dependency and sparsity information

**4\. Simulation Algorithms and Software**

- Assimulo: solver interface for ODE/DAE used with PyFMI
- PyFMI: Python interface for FMI, simulation, parameter estimation, co-simulation
- Master Algorithm
    
    - orchestrates the information exchange between FMUs
    - controls step size, interpolation/extrapolation strategy, evaluation order
    - ensures numerical stability
- Common co-simulation schemes:
    
    - Parallel: subsystems simulate same macro time step, then exchange values
    - Staggered: sequential evaluation with dependency ordering

**5\. Advanced Methods & Considerations**

- Feed-through subsystems: outputs depend directly on current input
- Multi-rate integration: different subsystems use different time scales
- Error estimation: used to control global step size
- Co-simulation requires careful treatment of
    
    - consitency and causality
    - discontinuities and events
    - rollback strategies
    - system initialization

**Part 2:**

**6\. Initialization of coupled systems**

- Coupling models in co-simulation often requires computing a consitent initial state
- Results in a set of algebraic equations: [image]
- Equations may form a loop and needed to be solved numerically
- Direct Feed-through: outputs depend directly on the input y(t) = f(u(t))
- Algebraic loop occurs when no explicit evaluation order exists for computing outputs -> circular dependencies
- Avoid / resolve algebraic loops by using structural analysis and graph-based methods

**7\. Structural Analysis**

- Approach: represent inputs/outputs as nodes in a directed graph
- Tarjans Algorithm to
    
    - identify strongly connected components (SSC) -> sets of variables in algebraic loops
    - determine evaluation order
- If the dependency matrix DL is nilpotent (DL^k=0 for some k) then
    
    - there are no circular dependencies
    - spectral radius is zero -> system can be evaluated explicitly
- System is structurally well-posed if there are no algebraic loops and an explicit evaluation sequence exists
- Otherwise simultaneous solving of coupled systems is required -> iterative solver, index reduction

**8\. Reducing the number of evaluations**

- Problem: Evaluating a model is computationally expensive due to internal dynamics
- Goal: minimize the number of internal evaluations when initializing coupled systems
- Strategy
    
    - Simplify the graph: remove not involved feed-through terms, group outputs no contributing to loops
    - Apply Tarjan's algorithm: determine SSC and evaluation order
    - Oprimize the order: adjust order to evaluate as many inputs as possible pefore triggering outputs

**Part 3:**

**9\. Assimulo: Sover Framework for ODEs and DAEs**

- Python based simultion interface for integrating differential equations (ODEs and DAEs)
- Focuses on unifying various solvers under a consitent Python interface, not developing algorithms
- Problem: defines equations and events
- Solver: defines how the problem is solved (tolerances, methods)
- Assimulo support discontinuous systems via:
    
    - State events: zero-crossing functions -> contact
    - Time events: discrete changes at specific times
    - Step events: reparameterization without simulation
- Event handling requires
    
    - event indicator functions
    - restarting solver on events
    - Optional simplifications when localization is not required
- Models are implemented as Cython/Python classes

**10\. PyFMI: FMI Wrapper and Co-Simulation Engine**

- PyFMI is a package for loading and simulating FMUs
- Provides a high level API that wraps the FMI interface using an object-oriented approach
- Functionalities:
    
    - Load and simulate single and coupled FMUs
    - Linearize FMU
    - Parameter Estimation
    - Result Handling
- Master algorithm based on Jacobi-like parallel Execution
    
    1. Inputs provided to each model
    2. Time step integration
    3. Output exchanged
    4. Inputs updated
- Instabilities may occur due to input discontinuities
    
    - Input smoothing
    - Directional derivatives
    - Step size control and extrapolation
- Architecture
    
    - Cytho-based core, wrapping FMI C API
    - Access via variable names that are mapped to value references
    - Models are structured as object-oriented classes