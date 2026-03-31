co_simulation_terminology_schmoll

# Motivation

- Modeling and Simulation of complex system with interest in the interplay and inter dependencies between different coupled subsystems
- Goal is to couple system parts which are developed in different tools
- Tool are specialized on mono-disciplinary research questions
- Coupled simulation / solver coupling describes the technique to couple detailed models of a subsystems of a system into a modular system model of the total system
- The specialized tools are used with their full functionality and subsystems are simulated with their specialized and optimized solvers provided by the simulation tool

# Classification of Coupling Strategies

- **Classical Simulation:**
    
    - actually no coupling since only a single modeling environment and a single solver
    - Example: Modelica
    - Result of mode creating: a single multi-physical / multi-domain equation system describing the system
    - System Model is solved by a single equation solver
- **Strong / Tight Coupling:**
    
    - Subsystems are modeled in different modeling environments and exported/imported into a single program which solves the whole system model with a single solver
    - Export can be equations or code describing the subsystem model equations
- **Co-Simulation / Weak Coupling:**
    
    - Multiple solvers are involved in the simulation
    - Coupling variables are only exchanged at predefined communication point (macro time steps)
    - In between, the coupling variables need to be approximated
    - Solvers of the subsystems need to be synchronized in time
- **Model Separation**
    
    - Only a single modeling environment is used to create system model equations
    - System model equations are distributed over several solvers
    - Purpose: Parallelization of the solving process or to separate stiff equation parts (only this part requires small step size)

# Co-Simulation:

- Multiple modeling environments and multiple solvers
- Allows different subsystem step sizes  (micro steps)
- Allows different Solvers (explicit / implicit), and multi-rate, and multi-method solvers
- Subsystems are selected such that they are mono-disciplinary and can be modeled with a single modeling environment and solved with optimized solvers and algorithms
- Co-Simulation considers the coupling of two or more dynamical subsystems
    
    - Subsystems are simulated with distinct but coupled time integrator / solvers
- Co-Simulation: coupling of at least two dynamic solvers
    
    - Dynamic systems are divided into at least two subsystems
- Assumption: Total system is describe bale by a DAE
    
    - Subsystems are coplued via inputs and outputs
    - During simulation, coupling variables needs to be exchanged
    - Coupling variables are approximated during macro step size

## Co-Simulation Strategies

- Time steps of involved subsystem solver needs to be synchronized
- Different execution strategies and algorithms possible

## Iterative Methods

- Macro steps are repeated to re-calculate the solutions of the subsystems with updated inputs
- Requirement: Subsystem solvers need to perform state rollback to jump back in time

## Explicit Methods

### Parallel (direct) execution

- Jacobi type / Conventional Parallel Staggered (CPS) procedure
- Subsystem solvers are started for each macro time step in parallel
- Coupling variables are communicated first
- Both subsystems start at the same time with the integration
- Both subsystems extrapolate their input variables
- Coupling variables are exchanges after both solvers have reached the next communication point

### Serial (alternating, sequential ) execution

- Gauß-Seidel Type / Conventional Serial Staggerd Procedure (CSS)
- Time integration of subsystems is done in sequence, one after the other
- required inputs for the first subsystem are extrapolated from already available output values / initial conditions
- After finishing first time step of first subsystem, outputs of subsystem 1 are communicated to subsystem 2, and subsystem 2 starts with integration ar the start of the macro time step (extrapolates input variables)
- Outputs of subsystem 2 are communicated to subsystem 1, and subsystem 1 can start with the next macro time step integration
- Question: Which of the subsystems should execute first?