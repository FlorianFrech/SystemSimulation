gomes_semantics_co_simulation_2019

Gomes, C., Lúcio, L., & Vangheluwe, H. (2019). Semantics of Co-simulation Algorithms with Simulator Contracts. *2019 ACM/IEEE 22nd International Conference on Model Driven Engineering Languages and Systems Companion (MODELS-C)*, 784–789. [https://doi.org/10.1109/MODELS-C.2019.00124](https://doi.org/10.1109/MODELS-C.2019.00124)

# Background

- Co-Simulation is the behavior trace of a coupled system, produced by the coordination of simulation units (SU)
- Behavior trace: function mapping time to values, representing the time stamped outputs of each SU
- FMU:
    
    - executable software entity, responsible for simulating a part of the system
    - implements the FMI standard, allows the master algorithm to communicate with it
- Main functionality of an FMU is encoded in three main C functions
    
    - function to set inputs
    - function to perform a step with a given step size
    - function to get outputs
- Master: software component that sets/gets inputs/outputs of each SU and asks it to estimate the state of its allocated subsystem at a future time
    
    - SU might perform multiple time steps
    - SU may employ an input approximation scheme
    - Computation is hidden from the master
- Co-Simulation scenario or just scenario
    
    - description of how the SU are interconnected
    - configuration of the co-simulation, e.g., step size

1. **Input Approximations**
    
    - between communication points, SU performs approximation of its inputs
    - Error in approximations translates into errors in the internal state approximations, translates into errors in the output produced
    - Larger communication steps, larger input approximation error
    - Growth rate of error is dominated by growth rate of step size (cite: Kübler and Schiehjlen, 2000; Arnold, Clauß, Schierz 2014)
    - Apply only to continuous co-simulation
2. **Event Detection**
    
    - Hybrid co-simulation: comprise continuous, discrete, and hybrid SUs
    - Hybrid: continuous interleaved with discrete changes
    - When discrete change happen in SU in between communication points, other SUs need to know about the change, as it can affect their inputs
    - If they only know about it in the next communication point, that the error might be so big that it renders the results useless
    - Require correct synchronization of discrete event simulator with a continuous simulator

# Formalization

## Simulation Unit

- Setting of an input changes the internal state of an SU
    
    $$s_c^{(1)} = \mathtt{set}_c \left( s_c^{ (0) }, u_u, v \right)$$
    
    - Input value $v$ has been recorded for input variable $u_u$
- Internal state index $(0), (1), \ldots$ is independent of the co-simulation time
    
    - state can undergo multiple transformations at the same co-simulation time
- Stepping function computes a new state, representing the internal state after $H$ units of time
    
    - It approximates the behavior of the corresponding model at time $t+H$
    - Result of approximation is encoded in the state
    - Continuous model: SU will approximate the evolution of the input

## Scenario

- structure $\langle C, L \rangle$ where each identifier $c\in C$ is associated with an SU
- $L(u) = y$: output $y$ is connected to input $u$
- Let $U = \bigcup_{c\in C} U_c$ and $Y =\bigcup_{c \in C} Y_c$ then $L: U \to Y$

## Co-Simulation Step

- Given a scenario $\langle C, L \rangle$, a co-simulation step is a finite order sequence of SU calls $(f_i)_{i\in \mathbb{N}} = f_0, f_1, \ldots $ with $f_i \in F = \bigcup_{c \in C} \{ \mathtt{set}c, \mathtt{get}c, \mathtt{step}_c \}$ and $i$ denoting the order of the function call

## Initialization

- Given a scenario $\langle C, L \rangle$, we define the initialization procedure $(I_i)_{i\in \mathbb{N}}$ in the same way as a step, with $I_i$ $\in F$

## Master Algorithm

- Given a scenario $\langle C, L \rangle$, a step size $H$, a step $(f_i)_{i\in \mathbb{N}}$, an an initialization procedure $(I_i)_{i\in \mathbb{N}}$, a master algorithm is a structure defined as
    
    $$\mathcal{A} = \langle C, L, H, (I_i)_{i\in \mathbb{N}}, (f_i)_{i\in \mathbb{N}} \rangle$$
    

## Feed-through

- The input $U_ c$ $\in U$ feed through to output $y \in Y_c$, that is $(u_c, y_c) \in D_c$ when there exists $v_1, v2 \in V$ and $s_c \in S_c$ such that
    
    $$\mathtt{get}_c
    (\mathtt{set}_c(s_c, u_c, v_1), y_c)
    \not =
    \mathtt{get}_c
    (\mathtt{set}_c(s_c, u_c, v_2), y_c)$$
    

## Reactivity

- For a given SU $c$ with input $u_c \in U_c, R_c(u_u) = true$ if the function $\mathtt{step}_c$ assumes that input $u_u$ comes from an FMU that has advanced forward relative to SU $c$

# Co-Simulation Semantics

## Scenario

- A scenario is given by a list of SUs
- A list of connections
- A SU is defined by its identifier, a list of input ports, and a list of output ports
- Each port has an identifier and a contract
    
    - Contract of input port relates to its reactivity
    - Contract of an output port is the list of input ports that it depends instantaneously on

## Co-Simulation State

- State of a co-simulation is given by a list of the state of each SU
- State of an SU is the list of each of its ports, and the timestamp of its internal state
- State of each port comprises the timestamp of the port value, and whether it has been defined at this timestamp
- Values for time stamps are $t$ or $t\cdot H$

## Output Computation

- represents the calculation of output of an SU
- Checks whether all inputs that feed-through to the output have the same timestamp

## Input Computation

- represents the setting of input of an SU
- Checks whether all outputs connected to the input are defined and have the same timestamp

## Step Computation

- Represents the advancement in time of an SU
- If the the SU contains an input port that is delayed, then the sate of that port must be defined at timestamp $t$
- If the SU contains an input port that is reactive, must be defined at timestamp t+H