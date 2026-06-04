cellier_combined_1986

# Combined Continuous/Discrete Simulation

## Introduction

- Combined simulation = Hybrid simulation

## Modeling of Discontinuous Functions

- Continuous system simulation languages (CSSL) offer sets of discontinuous functions such as
    
    - Limiter function
    - hysteresis function
    - dead-space function
- Most of these languages provide a no-sort option and/or procedural sections
    
    - Constructs such as If statements can be employed to model discontinuous functions
    - Discontinuous mechanisms are needed
- Discontinuities can be accurately located by exploiting numerical integration algorithms that operate on polynomial extrapolations
    
    - Polynomials never exhibit any discontinuity
    - Extrapolation around a discontinuity must be an error
    - Accuracy of the numerical integration is controlled by comparing the result obtained from different integration algorithm
    - Step size is reduced if the results disagree and step will be repeated with smaller step size
    - Different polynomial approximations have no reason to agree when integrated through a  discontinuity, and thus, the step size control mechanism of the integration algorithm can be used to locate the discontinuity rather accurately

## Generator Functions and Scheduled Events

- One type of discontinuities that can take place in an otherwise continuous model is a discontinuous input function
    
    - May be desirable to drive a model with a square wave generator
    - Can be described by assigning an initial value and by scheduling two initial time events to take place at times $t_0$ and $t_1$
    - Each event description schedules a new event of the same type to happen $T$ time units into the future
    - We are able to tell the simulation program explicitly about the forthcoming discontinuity
    - Last step before getting to the next discontinuity can be automatically reduced to hit the discontinuity accurately
    - No unnecessary repetition of integration steps is going to take place
    - Following the discontinuity, the integration algorithm can be restarted from scratch avoiding an integration through the discontinuity altogether

## State Events and State Conditions

- Not all discontinuities can be resolved by scheduling events ahead of time
- Discontinuities may depend on another time-dependent variable of the model such as the limited functions
- Simulation per-processor is expected to translate convenient if-then statements into code that automatically checks so-called state-conditions
- State conditions decide whether the model is about to switch from one branch of the discontinuous function to another
- If so,
    
    1. iterate to hit the discontinuity with a prescribed accuracy,
    2. then execute immediately a so-called state-event that performs the switch over,
    3. finally restart the integration algorithm from scratch thereafter.
- Combined simulation program can be viewed as a discrete event simulation program in which a continuous simulation takes place between any two consecutive event times

## Modeling of Sampled Data Systems

- Represent sampled data systems by a way of combined continuous/discrete simulation
- Discrete controller is simply represented as a self-generating time-event
- dz represents the rate by which the discrete state variable z is to be changed at each sampling point (calls for initial condition)
- Multi-rate sampling does not pose any problems here
    
    - Group all variables that use the same sampling interval and sampling times together into one state event
    - All other are specified in other state events
    - This guarantees the appropriate handling by the integration algorithm (integration will be automatically restarted after any sampling has taken place)

## Modeling Variable Structure Systems

- Model a system that changes its structure entirely at event times
    
    - Number of differential equations may change
- Such problems are more complicated to handle and do not occur so frequently in practice