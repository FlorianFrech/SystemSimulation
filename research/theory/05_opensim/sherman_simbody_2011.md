Sherman, M. A., Seth, A., & Delp, S. L. (2011). Simbody: Multibody dynamics for biomedical research. *Procedia IUTAM*, *2*, 241–261. [https://doi.org/10.1016/j.piutam.2011.04.023](https://doi.org/10.1016/j.piutam.2011.04.023)

# Simbody: Multibody dynamics for biomedical research

## Introduction

- Analogy between engineered mechanical systems and evolved biomechanical system is imprecise
- Problem: Multibody mechanics tools designed for engineers can be difficult to apply to study the dynamics of biological structures
- Examples:
    
    - biomechanical joints may comprise several moving parts, no simple rotation abot fixed axes
    - contact between soft tissues with significant deformation
    - redundant actuation of joints is common
    - parameterization data is not directly measurable
    - measurements tend to contain large errors and inconsitencies
- Challenges:
    
    - Segment masses properties and muscle path geometry are hard to measure
    - body segement kinematics estaimated from marker are not consistent with accelerations determined from external force measurements (ground reaction forces)
    - Concepts such as generalized coordinates and moment arms are not so simple for musculoskletal systems

## Simbody Overview

- System:
    
    - Encapsulates the components of a model (bodies, joints, force elements) and the code necessary to perform computations with that model
    - Defines a model’s parameterization
    - Is itself stateless and remains unchanged during a study
- State
    
    - Complete set of values for each of the System’s parameters is called a “state” for that System
    - Such sets are maintained in separate State objects constructed to be compatible with that System
    - State refers to software object, state refers to set of numerical values
    - Everything variable about a system
- Study
    
    - Couples a System and one or more States
    - Represents a computational experiment intended to reveal something about the system
    - result of any Study can be expressed as a state or a series of states that states satisfies some pre-specified criteria
- Trajectory: series of states

## Handling of State

- Many quantities derived from the state are expensive to compute, Simbody stores them in a realization chache inside a state object
- Realizing the state means presenting a State to the System so the system computes the physical consequence of that state
- Computations are organized in a strict sequence of stages:
    
    1. Topology (= system)
    2. Model
    3. Instance
    4. Time
    5. Position
    6. Velocity
    7. Force
    8. Acceleration
- Stage structure reflects the dependecy order:
    
    - Positions before velocities
    - Velocities before forces
    - forces before accelerations
- Simbody invalidates a chache entries automatically at that stage and above
- Example: Changing a speed, invalidates velocity, force, and acceleration results, but not already computed positions

## Formulation of dynamic equations as seen by the time stepper

- The time stepper sees a **simplified formulation** of the model, not the full internal multibody formulation.
- Simbody presents three equation groups to the time stepper:
    
    - **differential equations** for the continuous state
    - **algebraic constraints**
    - **event detection functions**.
- In this formulation:
    
    - $t$ is time
    - $y$ is the vector of continuous state variables
    - $d$ is the set of discrete state variables.
- The differential equations form an **ODE** in $y$.
- The algebraic constraints represent things like:
    
    - loop closures
    - coordinate couplers
    - prescribed motion
    - contact conditions.
- The ODEs plus algebraic constraints together define the continuous system as a **DAE**.
- Event functions detect discontinuities by **changing sign / crossing zero**.
- Examples of event triggers include:
    
    - signed distance between objects
    - a reaction force reaching a limit where the model must change.
- More precisely, Simbody formulates the continuous system as a **differential equation on a manifold (DEM)**.
- In a DEM, if the constraints are satisfied, their **time derivatives are satisfied automatically**.
- This is important because a DEM is **easier to solve than a general DAE** and allows the use of conventional ODE integrators, with added constraint and event handling.