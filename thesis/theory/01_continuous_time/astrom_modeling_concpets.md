astrom_modeling_concpets

# Modeling Concepts

- Model as precise representation of a systems dynamics to answer questions via simulation / analysis
- Multiple models for a single dynamical system with different level of fidelity depending on the question of interest
- Model is a mathematcial representation of a physical, biological, or information system
- Allow to reason about a system and make predictions about the system behavior
- Models of dynamical systems describing the input/output behavior
- Models as approximation of underlying system
- Dynamical systems: effects of actions do not occur immediately (car needs time to accelerate, temperature change)
- State of a dynamical system: a collection of variables that capture the past motion of a system for the purpose of predicting the future (state space = set of all possible states)

### Mechanical Heritage

- Common class of mathematical models for dynamical systems are ordinary differential equations (ODEs), spring-mass damper in mechanics
- Second order system has two states combined in the state vector:
    
    $x = (q, \dot q)$
    
- Time plot: shows the values of the individual states as a function of time
- Phase portrait: shows the traces of some of the states from different initial conditions (possible for 2nd order system, problematic for higher order)
- Autonomus system has no external influences
- Effects of external disturbances or controlled forces on the subsystems are obtained by introducing a force term $u$:  
    $m\ddot q + c(\dot q) +kq = u$
- The rate of change of the state can be influenced by the input
- Leads to controlled differential equation: allows to examine the influence of external disturbances or how the system can be steered the system from one point in the state space to another by manipulating the input variable

### Electrical Heritage

- Input/output model can be viewed as a table of input and output values, given input $u(t)$ over some time the model should produce $y(t)$
- Input/output framework is used in many engineering disciplines since it allows us to decompose systems into individual components connected through their inputs and outputs (simplification of complex systems)
- Input / output view is particularyl useful for the special case of linear time-invariant systems
- Linear: superposition / addition of two inputs yields an output that is teh sum of the outputs that would correspond to the individual inputs beeing applied separately
- Time-invariant: output-response for a given input does not depend on when that input is applied
- LTI very dominant in electrical engineering
- Step response: describes the relationship between an input that changes from zero to a constant value apruptly and the corresponding output (characterizing the performance of a dynamical system)
- Frequency response: response to sinusoidal input signals (based on theory of complex variables and Laplace transforms), allows the complete characterization of a system by its steady state resposne to sinusoidal inputs

### Control View: State Space Representation of input/output systems

$$\frac{dx}dt = f(x,u), \quad y = h(x,u)$$

- $x$ is a vector of state variables
- $u$ is a vector of control signals
- $y$ is a vector of measurements
- $\frac{dx}{dt}$ represents the derivative of the vector $x$ w.r.t. time
- $f$ and $h$ are possibly nonlinear mappings
- Control formulation models dynamics as first order differential equation systems
- Requires the appropriate definition of state and the maps $f$ and $h$
- Reachability: Can the possible states $x$ be reached withe the proper inputs $u$?
- Observability: Do the measurements $y$ contain enough information to reconstruct the state?
- Disturbance and model unceratinity: modeling disturbances as random signals (gives connection between prediction and control)
- Dual view of input/output representation and state space representation are useful when modeling systems with uncertainity (uncertainities are easier to describe using input / output models)

### Multidomain Modeling

- modeling traditions and methods differ between individual disciplines (mechanical vs. electrical vs. control)
- Challenge: system engineerings deals with heterogeneous systsms from may different domains
- Multidomain systems are partitioned into smaller subsystems
- Each subsystem is represented by a balance equations for mass, energy, momentum, or by appropriate descriptions of information processing in the subsystem
- behavior of the interfaces is captured by describing how the variables of the subsystems are interconnected
- Interfaces equations constrain involved variables to be equal
- Complete model is obtained by combining the descriptions of the subsystems and the interfaces
- State models or ordinary differential equations are not suitable for component-based modeling since states may disapear when components are connected (two capacitators in parallel in an electric ciruit, two inertias coupled by a rigid shaft)
- The internal description of a component may change when it is connected to other components
- Difficulty can be avoided by replacing differential equations by differential algebraic equations, which have the form
    
    $$F(z, \dot z) = 0$$
    
    - where $z \in \mathbb{R}^n$
- Simple special case:
    
    $$\dot x = f(x, y), \quad g(x,y) = 0$$
    
    - where $z = (x,y)$ and $F =(\dot x - f(x,y), g(x,y))$
    - Key property: derivative $\dot z$ is not given explicitly and there may be pure algebraic relations between the component of the vector $z$
- Modeling using differential algebraic equation is also called equation-based modeling, acausal modeling, or behavioral modeling
- Example: if two capacitators are connected, the algebraic equation is added that the voltages across the capacitators are the same.
- Modelica: language that has been developed to support component-based modeling
    
    - Differential algebraic equations are used as the basic descriptions
    - Object-oriented programming is used to structure the models
    - Used to model the dynamical of technical systems in domains such as mechanical, electrical, thermal, hydraulic, thermofluid, and control subsystems
    - Intended to serve as standard format so that models arising in different domains can be exchanged between tools and users
    - Brings a large set of free and commercial Modelica component libraries

### Finite State Machines and Hybrid Systems

- Developed within the computer-controlled system community
- Hybrid system (cyber-physical system) combines continuous dynamics with discrete logic
- Discrete: logical variables that reside within a compute (mode of a system)
- Discrete state dynamics are represented using a finite state machine
- Consists of a finite state $\alpha \in \mathbb Q$
    
    - $\alpha$: Mode of the system
- Dynamics of a finite state machine are defined in terms of transition between states
- Guarded Transition System:
    
    $$g_i(\alpha, \beta) \to \alpha^\prime = r_i(\alpha), \quad i = 1, \ldots, N$$
    
    - $g$ is a boolean function that depends on the current system mode $\alpha$ and input $\beta$ which might represent an environmental event
    - if the guard $g_i$ is true then the system transitions from the current state $\alpha$ to the new state $\alpha^\prime$, determined by the transition rule $r_i$
- Hybrid system: combining systems that have a continuous state whith those having a discrete states
    
    - continuous dynamcis are governed by an ordinary differential equation that may depend on the system mode $\alpha$
    - discrete transition system is also influenced by the continous state
    - guards and rules depend on the continuous state
- Tools: Matlab/StateFlow, Modelica, Ptolemy

**Model Uncetrainity**

- Left out because my model is purely deterministic
- I do not introduce noise and statistics