kunkel_dae

# Differential Algebraic Equations

- Physical processes are usually modeled via differential equations
- If the states of the physical system are in some ways constrained (by conservation Laws such as Kirchhoff’s law in electrical networks) then the mathematical model also contains algebraic equations to describe these constraints
- Such systems, containing both differential and algebraic equations, are called differential-algebraic systems
- Most general form of a differential algebraic eqaution is
    
    $$F(t, x, \dot x) = 0, \quad
    \text{with} \quad F: \mathbb I \times \mathbb D_x \times \mathbb D_{\dot x} \to \mathbb C^m$$
    
    - where $\mathbb I \underline{\subset} \mathbb R$ is a compact interval
    - $\mathbb D_x, \mathbb D_{\dot x} \underline{\subset} \mathbb C^n are open
    - $m,n \in \mathbb N$
    - $\dot x$ denotes the derivative of a differentiable function $x: \mathbb I \to \mathbb C^n$ w.r.t $t$
    - $\dot x$ is used as independent variable of $F$
    - We want $F$ to determine a differentiable function $x$ that solves the equation
- Uniqueness of solutions in the context of initial value problems with $x(t_0) = x_0$
- Boundary value problems: $b(x(\underline t), x(\bar t))=0$
    
    - Propertirs of differential-algebraic equations reflect the properties of differenrial equations as well as the properties of algebraic equations, but also that other phenomena occur which results from the mixture of these different types
- DAE became important for modeling and simulation of dynamical systems
- Implicit systems of the above form were ususally transformed into ODEs $\dot y = g(t,y)$ via analytical transformations
- Linear differential-algebraic equation with constant coefficients:
    
    $$E\dot x = Ax + f(t) $$
    
- Method 1:
    
    - Achieved by explicitly solve the constraint equations analytically in order to reduce the given differential-algebraic equation to an ordinary differtial equation in fewer variables
    - approach relies heavily on transformations by hand or symbolic computation software (both not feasible for medium or large sclae systems)
- Method 2:
    
    - differentiate the algebraic constraint in order to get an ordinary differential equation in the same number of variables
    - Requires the use of the implicit function theorem (approach is difficult to perform)
    - Resulting variables may have no physical meaning
    - Observed that the numerical solution may drift off from the constraint manifold after a few integration steps
    - Stabilizatiuon techniques in the field of simulation of mechanical multi-body systems were developed to adress this difficulty
    - It is in general preferable to develop methods that operate directly on the given differential-algebaric equation
- Summary
    
    - DAEs are important because they arise naturally in modern modeling tools that generate subsystem models and connect them across constraints
    - This is especially relevant for component based multi-domain modeling
    - DAE systems are harder than pure ODE system because their analytical and numerical properties are more complicated.
    - Coupled and switched problems make the problem even more difficult.

## Solvability Concepts

- To develop a theoretical analysis for differential-algebraic systems, one needs to specify the kind of solution one is interested in
    
    - Function space in which the solution should lie
- Concepts discussed:
    
    - Classical continuous differentiable solutions
    - Weak distributions solutions

### Definition Solvability:

[image]

- Problem is called solvable if it has at least one solution
- Solvability is mostly used for systems which have a unique solution when initial conditions are provided
- Solution of the initial value problem is not unique in the context of control problems

## Index Concepts

- Linear differential-algebraic systems with constant coefficients: all properties of the system can be dtermined by computing the invariants of the associated matrix pair $(A, E)$ under equivalence transformations
- Index: Size of the largest Jordan block to an infinite eigenvalue in the associated Kronecker canonical form
- Index plays a major role in the analysis and determines the smoothness that is needed for the inhomogenity $f$ to gurantee the existence of a classical solution
- Differntiation index: Minimum number of times that all part of the differential-algebraic equations must be differentiated w.r.t. $t$ in order to determine $\dot x$ as a continuous function of $t$ and $x$
    
    - Motivated by transforming the implicit system to an ordinary differential equation
    - Not suited for over- and under-determined systems since it based on solvavbility concept that requires unique solvability
    - Determine how far the differential-algebraic equation is away from the ordinary diefferntial equation
- Strangeness Index: Generalized the differntiation indey to over- and underdetermined systems
- Index is introduced to classify different types of differential-algebraic equations w.r.t. the difficulty to solve them
- Does not make sense to turn a a uniquely solveable classical linear system $Ax = b$ into a differential equation

## Applications

### Electrical Circuit Simulation

- Mathematical model for the charging of a capacitator $C$  via a resistor $R$, and voltage source $U$
- Potential is associated with each node of the circuit
- Kirchhoff’s law: sum of currents vanishes in each node leads to a differential algebraic system
- Differentiation index one

### Physical Pendulum

- Pendulum is modeled by the movement of a point mass with mass m in cartesian coordinates $(x,y)$ under the influence of gravity, in a distance $l$ around the origin
- Via kinetic and potential energy and the constraint $x^2 + y^2 -l = 0$ we obtain the lagrange function wihb Lagrange parameter $\lambda$
- One obtains a differential algebraic system wit hdifferentiation index three