omola_anderson_1990

## Introduction

- Omola: language for representing models of dynamic systems
- Outcome from a larger project in computer aided control enginerring (CACE)
- Problem:
    
    - Models play an essential role in engineering and design of control systems
    - Most simulation languages and model representations are too specialized and unflexible to be used for general modeling
- Requirements for the modeling language:
    
    - Mathematical and logical frameworks for representing model behavior: DAEs, transfer functions, state space descriptions, discrete events and qualitative behavior
    - Concepts for structuring large models
    - Modular: Support the reuse of model in other models

## Languages for Dynamic Models and Simulation

- Simulated systems: mechanical, chemical, electrical
- Non-technical: economical, ecological, sociological
- Simulations are based on model which represent the system we want to study
- Models are usually based on a mathematical framework such as differential equations
- Model typically describes parallel activities:
    
    - Set of differntial equations describing a continuous time system, are valid at all times
    - Equations need to be sorted and translated in order to be evaluated (pre-processor)

## Combined discrete event and continuous time systems

- Most systems are naturally represented by combined continuous time and discrete event models
- Model equation describes a fact about the model that is true at all times
- Assignments in an imperative language are evaluated in a well defined sequence, and interpreted as equations, they are only valid directly after evaluation
- Model equations are evaluated in any order decided by the integration algorithm in the simulator
- Sampled and discrete models are more naturally described by a sequence of assignments that are executed in sequence at every sample instance

## Events and Actions

- Discrete Event Dynamical Systems: systems where all state changes occur at specific instances in time called events.
- Time instances are usually not known in advance
- Many real systems show behavior that is a combination of continuous time and discrete event dynamics.
    
    - Industrial plant with batch processing
    - Intelligent or rule-based control
    - Supervisory control