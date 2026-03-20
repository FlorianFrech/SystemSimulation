SystemDynamics_Karnopp

# Introduction

- Development and understanding of dynamic physical systems
- Type of systems are described by the term mechatronic
    
    - while elements of the system are mehcanical in general
    - electronic control is also involved

**Dynamic System**

- Assumed to be an entity separable from the rest of the universe (the environment of the systems) by means of a physical, conceptual boundary.
- Boundary is physical or spatial
- System is composed of interacting parts
- System modeling has to do with the construction of a model complex enough to represent the relevant aspects of the real system but not so complex as to be unwidely
- Each component part itself is a system
- Dynamic systems: behavior as a function of time
- Static analysis can be misleading, steady state might be never achieved, thus dynamic system analysis is important

## Models of Systems

- Model of the system: to study the dynamics of a real system
    
    - simplified and abstracted constructs are used to predict behavior
- Scaled physical model:
    
    - wind tunnel models of aircrafts, structural models of metal parts in photoelastic stress analysis
    - only partial features of the system are reflected in the model
    - Assumption that some aspects of the reall system are not important to detremine the interested behavior
- Mathematical model:
    
    - used to predict only certain aspects of the system response to inputs
    - Model must be a simplification of reality
    - Variety of system models of varying complexity are required to find the simplest model capable of answering questions about the system
- Bond graphs:
    
    - Can express models based on diverse branches of engineering science
    - are based on energy and information flow
    - allows the study of structure of the system model
    - Standard techniques allow the transformation into differential equations

## Systems, Subsystems, and Components

- Modeling a system requires to break it up into smaller parts that can be modeled and perhaps studied experimantally and then to assemble the system model from the parts
    
    - Subsystems: Major parts of a system
    - Components: primitive parts of subsystems
    - Elements: most primitive level
    - Hierarchy of systems, subsystems, and components can never be absolute
    - Subsystem and component categories are in many engineering applications obvious
- Subsystem is a part of a system that will be modeled as a system itself
- Subsystem will be broken into interacting components parts
- A component is modeled as a unit and not thought of as composed of simples parts
- Required to know how the components interact whith each other
- It is possible to treat some of the subsystems as components if their interactuons with the rest of the system can be specified without knowledge of the internal construction of the subsystem
- Skilled and expiremnt system engineer makes a judgement on the appropriate detail of modeling of a subsystem on intuitive basis

## State-Determined Systems

- Mathematical models for systems: state-determined system
- System model is described by a set of ordinary differential equations in terms of state variables and a set of algebraic equations that relate other system variables of interest to the state variables
- Future of all the variables associated with a state determined system can be predicted if
    
    - the state variables are known at some initial time
    - the future time history of input quantities from the external environment is known
- Implications:
    
    - Events in the future do not affect the present of the system
    - Time runs in one direction (past to future)
- All past history of a state-determined system is summed up in the present values of its state variables
    
    - Means that many past histories could have resulted in the same present value of state variables and hence the same future of the system
    - If one can bring the state variables to some particular values, then the future response is determined by the future inputs and nothing is important about the past expcept that the state variables were brought to this values
- State determined systems
    
    - state variable are properly initialized -> experiment is repeatable
    - not repeatable -> some state variable was not monitored and initialized properly or an unrecognized input influences the system.

## Inputs, Outputs, Signals

- In performing experiments on a subsystem, the notions of input and output, or, equivalently, excitation and response, arise
- same concepts carry over when mathematical models of subsystems are assembled into a system model
- At each port, an effort and flow variable exist, and one control either one but not both of these variables simulatneously

Example: Steady state characteristics of a dc motor

- dynamometer sets the speed of the motor regardless of the torque delivered by the motor
- speed $\omega$ is then an input variable to the motor
- torque being delivered by the motor is then measured by a torque gauge, torque is thus an output variable of the motor
- It is not possible to adjust the dynamometer such that both torque and speed have arbitrary values
- Nature of the experiment is to discover what the motor torque is at a given speed
- Block diagram: lines with arrows indicate directions of signals
- If either the effort or flow variable is an input, the other must be an output
- Bond graphs: causal stroke defines input and outputs

[image]

### Signal Flow

- Multiports transmit finite power when interconnected
- Both an effort and flow variable exist when coupled
- Systems are interconnected by the matching of a pair of signals representing the power variables
- Systems are often designed, such that only one of the power variables is important: a single signal is transmitted btween tow subsystems
- Example: electric amplifier reacts to a voltage but the current drawn has now effect on the circuit (ideal ammeter, ideal voltmeter do not disturb the other)