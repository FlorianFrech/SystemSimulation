hansen_verification_2021  

Hansen, S. T., Gomes, C., Palmieri, M., Thule, C., van de Pol, J., & Woodcock, J. (2021). Verification of Co-simulation Algorithms Subject to Algebraic Loops and Adaptive Steps. In A. Lluch Lafuente & A. Mavridou (Eds.), *Formal Methods for Industrial Critical Systems* (pp. 3–20). Springer International Publishing. [https://doi.org/10.1007/978-3-030-85248-1_1](https://doi.org/10.1007/978-3-030-85248-1_1)

# Introduction

- CPS is typically developed in a distributed fashion using different tools and techniques
- Co-simulation assists in the development of complex CPS
- Co-simulation is the study of how to coordinate multiple black-box simulation units (SUs)
    
    - each SU is responsible for computing the behavior of a subsystem
    - combined behavior of all SUs produces the global behavior of a system
- SUs are coupled by an orchestration algorithm that interacts with each SU
- Example of such an SU is a Functional Mock-up Unit defined by the Functional Mock-up Interface Standard (inspires the notation of an SU)
- Challenge in co-simulation is to ensure a correct simulation results
    
    - requires an algorithm tailored to the scenario that respects the SU’s input approximation functions
    - Simulation of complex scenarios with algebraic loops or adaptive steps
    - Complex scenarios use specific iterative algorithm
- Iterative Algorithm
    
    - Algebraic Loop: solves the cyclic dependencies between the SUs
    - Adaptive Step Size: ensures that all SUs agree on a step (step negotiation)

# Background

- Co-Simulation: technique enabling the global simulation of system consisting of multiple black-box SUs
- SU has an own solver that calculates the behavior trace of the dynamical system it represents
- Dynamical system as a function from time and space into some often multi-dimensional and continuous space
- System interacts with the environment through inputs and outputs

## Simulation Units

- SUs can be coupled through their inputs and outputs
- Coupling restriction: One state cannot exist independently; it is always connected to another state.
- Problem: coupling restrictions can be only satisfied at certain points in time (communication points), different to monolithic approaches where coupling restrictions are transparent
- Input Approximation: Each SU makes assumptions about the evolution of input values between the communication points (can cause accumulable errors)
- Scenario is simulated using an orchestrator, that is an algorithm that computes the behavior trace of all SUs trying to find the communication points that minimize the error introduces in the co-simulation

**Definition 1: Simulation Unit**

An SU with identifier $c$ is represented by the tuple

$$\langle S_c, U_c, Y_c, \mathtt{set}_c, \mathtt{get}_c, \mathtt{step}_c \rangle$$

where

- $S_c$ represents the state space
- $U_c$ and $Y_c$ the set of input and output variables, respectively
- $\mathtt{set}_c: S_c \times U_c \times \mathcal{V}_\mathcal{E} \to S_c$
    
    - Function to set the inputs
- $\mathtt{get}_c: S_c \times Y_c \to \mathcal{V}_\mathcal{E}$
    
    - Function to get the outputs
- $\mathcal{V}_\mathcal{E}$ set of values exchanged between input / output variables
    
    - Type is tuple $\langle t, \mathcal{V} \rangle$ where $\mathcal{V}$ denotes the value obtained at a given output port at timestamp $t$ of SU $c$  
- $\mathrm{step}_c : S_c \times \mathbb{R}_{\geq 0} \to S_c \times \mathbb{R}_{\geq 0}$
    
    - Function that instructs the SU to compute its state after a given time duration
    - If an SU is in state $s_c^{(t)}$ at time $t$, $\left( s_c^{(t+h)}, h \right) = \mathrm{step}_c\left( s_c^{(t)}, H \right)$ approximates the state of the corresponding model at the time $t+h$, where $h\leq H$
        
- State of SU $A$ at time $t$ is denoted as $s_A^{(t)}$
- Assume that the last value set on an input/output port can be inspected
- Function $\mathtt{step}_c$ returns a step size because come SUs implement error estimation and may conclude that taking a step size of $H$ will result in an intolerable error, meaning SU takes a smaller step

**Definition 2: Scenario**

A scenario is a structure

$$S = \langle C, L, M, F, R, D \rangle$$

where:

- each identifier $c \in C$ is associated with an SU
- $L(u) = y$ describes the connection of input $u$ with output $y$
- subset $M$ of units that can do error estimations / step rejection
- sets $R$ and $D$ that characterize whether inputs are treated as reactive or delayed
    
    - Reactive components: step function assumed the input for that components come from an SU that has advanced forward relative to SU $c$
    - Delayed components: step function assumed that the input comes from an SI that is at the same time as the SU $c$
- the set $F$ of feedthrough dependencies
    
    - inputs $u_c$ feeds through to output $y_c$
    

**Algebraic Loop Variables**

- Couplings of SUs and feedthrough can introduce algebraic loops
- Port variables in that scenario form a cyclic dependency, requiring that all their values are being set at the same time instant
- Set of port variables involved in algebraic loops are the port variables of non-trivial SCCs in the step operation graph
    
    $$\mathrm{algebraic}_S
    \triangleq
    \{\, s \mid s \in \mathrm{SCC}_S \land s \in U \cup Y \,\}$$
    

**Simple Scenario**

- No unit performs error estimation and no algebraic loop exists
    
    $$M = \emptyset \land \mathrm{algebraic}_S = \emptyset$$
    

**Complex Scenario**

- Any scenario that is not simple
- simple = no rollback / step negotiation and no algebraic loop
- complex = algebraic loop and/or step rejection capability is present