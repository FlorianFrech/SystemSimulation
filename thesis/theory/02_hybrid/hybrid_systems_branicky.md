hybrid_systems_branicky

# Simulation of Hybrid Systems

## Introduction

- Hybrid system contains the combination of continuous and discrete
    
    - inputs
    - outputs
    - states
    - dynamic equations
- Melding of the analog and digital world
- Arise due to variety of applications of automated and controlled phenomena
- Autonomous case:
    
    - abrupt changes in continuous dynamics (switching) or continuous states (jumps or resets)
- Controlled case:
    
    - simple finite state machine may be used to regulate a physical process (simple thermostat)
- Combination of autonomous and controlled phenomena may be present
- Real world examples:
    
    - power electronics with state dependent circuit switching
    - motion control (disk drives, transmission, stepper motors, position encoders)
    - robotics (constrained robots, flexible manufacturing, interacting agents)
    - intelligent transportation systems
    - aerospace
- Challenge: Accurate simulation because of the sophisticated need for mixed continuous/discrete simulation in a timely manner
- Definition:
    
    ```
    Hybrid system consists of a finite automaton or discrete-event system which is "supervising" the action of a collection of ODEs or DAEs by giving commands for when to switch between them, and how to update variables upon switching.
    ```
    

## Hybrid Dynamical Systems

- Hybrid systems involve both continuous-valued and discrete variables.
- System equations contain mixtures of
    
    - logic
    - discrete-valued or digital dynamics,
    - continuous-variable or analog dynamics
- Continuous dynamics is in general given by differential equations
- Discrete-variable dynamics of hybrid system is governed by a digital automaton, or input-output transition system with a countable number of states
- Continuous and discrete dynamics interact at event or trigger times when continuous state hits certain prescribed sets in the continuous state space
- Hybrid control systems: involve continuous and discrete dynamics and continuous and discrete controls
- Continuous dynamics is modeled by a differential equation

## Classification of discrete phenomena:

1. Autonomous switching: discontinuous change in the state when the state hits certain boundaries
2. Autonomous impulse: state jumps discontinuously on hitting prescribed regions of the state-space
3. Controlled switching: derivative changes abruptly in response to a control command
4. Controlled impulse: state changes discontinuously in response to a control command

## Detecting State-Dependent Events:

- If there are no implicit equations RKF45 is used, else an implicit Runge-Kutta Scheme, Radau5, is used
- For general DAEs, DASSL is used
- All boolean event conditions which refer ro values of continuous variables are translated so that they occur on zero crossing
    
    $$x > x_\text{max} \to x - x_\text{max}$$
    
- Compound conditions are dealt with by introducing multiple event conditions
- Assume that purely discrete event conditions can be dealt with effectively
- Continuous-time event conditions must be evaluated along with the continuous solution
- Root finding program DASSRT is used in conjunction with DASSL to find the zero-crossings associated with these
- If a zero-crossing is present in an interval, standard bisection and secant algorithm are used to locate the root precisely