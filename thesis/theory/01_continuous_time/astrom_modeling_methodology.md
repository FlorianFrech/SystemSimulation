astrom_modeling_methodology

- Modeling of large and complex systems benefits of using different representations of the system that captures essential features and hide irrelevant details
- Common practice to use some graphical description of system called schematic diagrams to get an overall view of the system and to identify the individual components and their interconnections

Block Diagrams

- Purpose is to emphasize the information flow and to hide details of the system
- different process elements are shown as boxes
- Each box has inputs denoted by lines with arrows pointing towards the box and outputs denoted by lines with arrows going out of the box
- Inputs denote the variables that influence a process
- Outputs denote the signals that we are interested in or signals that influence other subsystems
- Block diagrams can be organized in hierarchies, where individual blockss may themselves contain more detailed block diagrams
- Overall dynamics of the system is decomposed into a series of interconnected subsystems or blocks
- Each ob the blocks in the diagram can be itself a complicated subsystem
- Choice of the level of detail of the blocks and what elements to separate into differnt blocks depend on experience and on the question that one wants to answer unsig the model
- Powerful feature: ability to hide information about the details of a system that may not be needed to gain an understaning of the essential dynamics of the system

Algebraic Loops

- Differential equations are needed to simulate and analyze a system described by a block diagram
- Equations are obtained by combining the differential equations that describe each subsystem and substituting variables
    
    - This procedure cannot be used when there are closed loops of subsystems that all have a direct connection between inputs and outputs, known as Algebraic Loop
    - A direct connection (direct feedthrough) means that a change in the input $u$ gives an instantaneous change in the output $y$

Example:

- First order non-linear system with a proportional controller
    
    $$\frac{dx}{dt} = f(x,u), \quad y = h(x)$$
    
- and a proportional controller described by $u=-ky$
    
    - There is no direct function $h$ that does not depend on $u$
    - In that case we can obtain the equation for the closed loop system simply by replacing $u$ by $-ky=-kh(x)$ to give
        
        $$\frac{dx}{dt} = f(x, -kh(x), \quad y = h(x)$$
        
    - This is an ordinary differental equation
- More complicated if there is a direct connection: if $y=h(x,u)$, the replacing $u$ by $-ky$ gives
    
    $$\frac{dx}{dt} = f(x, -ky), y = h(x, -ky)$$
    
    - To obtain a differential equation for $x$, the algebraic equation $y=h(x, -ky)$ must first be solved to give $y= \alpha(x)$ which is in genarl a complicated task
        
- When algebraic loops are present, it is necessary to solve algebaric equations to obtain the differential equations for the complete system
- Resulting model becomes a set of differential algebaric equations
- Resolving algebraic loops is a nontrivial problem , because it requires the symbolic solution of algebaric equations
- Most block diagram oriented modeling languages cannot handle algebraic loops
- Modelica uses several sophisticated methods to resolve algebraic loops