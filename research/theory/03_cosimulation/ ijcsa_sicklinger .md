 ijcsa_sicklinger 

**1 Context and Goal**

- Co-Simulation: each subsystem integrates its own equations internally
- Boundary variables (inputs/outputs) are exchanged at communication points
- Consistency as main challenge:
    
    - Each subsystem i produces outputs yi depending on its current states and inputs ui
    - inputs of each subsystem depend on other subsystems' output (via coupling equation)
- All simulators are interdependent and form potentially algebraic loops at the interface
- IJCSA introduces a residual-based iterative coupling using the jacobian of the interface equation to stabilize and accelerate convergence

**2 Algorithm**

1. Time loop: each subsystem advances from time t_n to t_n+1 via co-simulation
2. Iteration loop: coupling iterations per time step
    
    - at each communication step, the coupled system must converge to a consistent interface state
    - iterations continue until the interface residuals are below a tolerance eps
3. Parallel subsystem evaluation
    
    - each subsystem integrtates its model internally using its local solver, given its current input guess
    - outputs are computed for the next communication point
    - this step can be done in parallel for all subsystems
4. Compute and check interface residulas
    
    - interface residuals measure how well the coupling equations are satisfied
    - Example: if subsystems i's input should equal another subsystem's output R_i = u_i - y_i
        
        - R_i = 0 means perfect coupling consistency
    - if the residual norm is consistent, exit the iteration
5. Compute local interface Jaconians
    
    - each simulator provides the sensitivity of its inputs yi with respect to its inputs U_i
    - can be obtained analytically if the FMU support directional derivatives or approximated numerically
    - describes how the interface react to small perturbations in coupling variables
6. Assemble global interface Jacobian
    
    - global interface jacobian collects all local derivatives
    - adds coupling terms that reflect how outputs of one subsystem affect the inputs of others
    - each block shows how residuals in one subsystems are influenced by state/output changes in others
7. Solve for corrector step
    
    - Newton like correction-step
    - r_n: current residuals
    - J_global: Jacobian of the residuals
    - Solving for delta c providesthe necessary corrections to subsystem input guesses U_i to drive residuals towards zero
8. Apply correction
    
    - each subsystem input guess is updated with the corrector term
    - then iteration restarts with the updated coupling inputs
9. Prepare for next communication step
    
    1. after convergence the final consistent input vector is stored as the initial guess for the next time step

\-------------------------------------------------------------------------------------------------------------------------------

**Interface Jacobian-based Co-Simulation**

- Co-Simulation as a prominent method to solve multi-physics problem
- Multi-physics simulation using a co-simulation approach allow well established and specialized simulation tools for different fields and signals to be combined and reused with minor adaptions in contrast to the monolithic approach
- drawback of stability and accuracy challenges if different subsystems are used to form so-simulation scenario
- Co-simulation algorithm based on Interface jacobians which allows for the stable and accurate solution of complex co-Simulation scenarios involving several different subsystems
- Fomrulated such that it enables parallel execution of the participating subsystems
- the Interface Jacobian-based Co-Simulation Algorithm handles algebraic loops as the co-simulation scenario is defined in residual form

**1 Introduction**

- Sophisticated simulation tools exist for solving individual and combined physical pehenomena
- Due to incereased complexity, designer must include more physics in his virual model
- multi-physics simulations using a co-simulation approach have an intrinsic advantage that allows established and specialized simulation tools for different fields to be combined
- Core Idea of the Interface Jacobian-based Co-Simulation Algorithm (IJCSA)
    
    - develop an algorithm that can handle a co-simulation scenario of an arbitrary number number of codes (=simulation units) where additional interface conditions can be specified.
    - important property is to feature accurate and stable simulations
    - performance is critical: simulators need to be able to run in parallel without data flow dependence

**2 Idea of the Interface Jacobian-based Co-Simulation Algorithm**

- Example with two subsystems each equipped with one input and one output quantity
- sysnonyms for subsystems: client, code, simulator, solver, and agent

<table><tbody><tr><td><p><strong>Equations</strong></p></td><td><p><strong>Descriptions</strong></p></td></tr><tr><td><p>[image]</p></td><td><ul><li><ul><li>subsystems S1(U1) and S2(U2)</li><li>internal state variables X1, X2</li><li>output variables Y1, Y2</li><li>subsystems are assumed to model a nonlinear relation between output Y and input U quantities</li><li>S is in general a nonlinear operator</li></ul></li></ul></td></tr><tr><td><p>[image]</p></td><td><ul><li><ul><li>L is the interface constraint operator which can also be nonlinear in general</li><li>Interface constraint operator is essential to the IJCSA</li><li>Reflects the relationship between input and output variables</li><li>Basic Idea: formulate a Newton method at interface level</li><li>In contrast to a monolithic approach a much smaller system needs to be solved</li><li>Newton method is used to solve the set of in general non-linear interface constraint equations</li></ul></li></ul></td></tr><tr><td><p>[image]</p></td><td><ul><li><ul><li>Combination of the two equation systems leads to a nonlinear equation system</li><li>Newton method should be applied to the system</li></ul></li></ul></td></tr><tr><td><p>[image]</p></td><td><ul><li><ul><li>Definition of the interface residual</li><li>solving the set of equations, we determine the set of input values U for each system</li></ul></li></ul></td></tr><tr><td><p>[image]</p></td><td><ul><li><ul><li>iteration sequence for the Newton method</li><li>phi: vector of unknowns</li><li>r: residual vector</li><li>J: Jacobian operator (dimension of the Jacobian operator is only dependent on the number of input variables at the interface level)</li><li>m: ietartion index</li></ul></li></ul></td></tr></tbody></table>

**Example:**

- Linear interface system of the Newton method

<table><tbody><tr><td><p>[image]</p></td><td><p>[image]</p></td></tr></tbody></table>

- Interface Conditions:

[image]

- Linear interface system becomes:

[image]

- Final Form of the interface equation system is

[image]

**Two Subsystems Algorithm:**

- If the global Jacobian matrix is set to the identity matrix, the algorithm reduces to the classical fixed-point Jacobi scheme
- For this case it is in general necessary to introduce a relaxation parameter alpha to achieve convergence

[image]

[image]

**Algorithm for an arbitrary number of subsystems**

- from the derivations, it is obvious that the entries of the jacobian matrix are composed of two basic kind of derivatives
- First parts need to be provided by the interface
- Second parts need to be provided by each individual subsystem

[image]

[image]