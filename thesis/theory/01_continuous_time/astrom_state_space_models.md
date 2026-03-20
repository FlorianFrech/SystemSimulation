astrom_state_space_models

# State Space Models

## Ordinary Differential Equations

- State: collection of variables that summarize the past of a system for the purpose of predicting the future
- Pyhsical system: state is composed of pyhsical variables (mass, momentum, energy)
- State variables are gathered in a state vector $x \in \mathbb R^n$
- Control variables are represented by $u \in \mathbb R^p$
- Measured signal vector $y \in \mathbb R ^q$
- State space model: system represented by differential equations
    
    $$\frac{dx}{dt} = f(x,y), \quad y = h(x,u),$$
    
    - $f: \mathbb R ^n \times \mathbb R^p \to \mathbb R^n$
    - $h : \mathbb R^n \times \mathbb R^p \to \mathbb R^q$
- order of the model: dimension of state vector
- Time invariant: mappings do not explicitly on time
- $f$ gives the rate of change of the state vector
- $h$ gives the measured values as functions of state and control input
- Linear state space model if the functions f and h are linear in x and u
    
    $$\frac{dx}{dt} = Ax + Bu, \quad y = Cx + Du,$$
    
    - $A, B, C, D$ are constant matrices $\to$ LTI model
    - $A$ danymics matrix
    - $B$ control matrix
    - $C$ sensor matrix
    - $D$ direct term
- Also: reachable canonical form