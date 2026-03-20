DAE_Simulink

# Solve Differential Algebraic Equations (DAEs) - MATLAB & Simulink

## Differential Algebraic Equations

- Type of differential equations where one or more derivatives of dependent variables are not present in the quations
- Variables that appear in equations without their derivatives are called algebraic
- Presence of algebraic varaibles means that you cannot write down the equations in explicit form $y^\prime = f(t,y)$
- Insetad you can solve DAEs with these forms, semi-explicit DAEs of the form
    
    $$\begin{align}
    y^\prime &= f(t,y,z) \\
    0 &= g(t,y,z)
    \end{align}$$
    
- Presence of algebraic variables leads to a singular mass matrix
- Fully implicit form:
    
    $$f(t, y, y^\prime) = 0$$
    
    - Presence of algebraic variables leads to singular jacobian matrix
    - Reason: at least one of the columns in the matrix is guaranteed to contain all zeros, since the derivative of that variables does not appear in the equations
- DAE arise in a wide variety of systems beacuse physical conservation laws often have froms like $x+y+z=0$
    
    - Fi $x$ and $y$ are explicitly defined in equations, then this conservation equation is sufficient to solve for $z$ without having an expression for $z$

## Consistent Initial Conditions

- When solving a DAE, you can specify initial conditions for $y^\prime_0$ and $y_o$
- Possible that the specified initial conditions do not agree with the equations trying to be solved
- If no initial conditions for the the derivative are specified, solver automatically computes consistent initial conditions based on the initial condition for $y$

## Differential Index

- DAEs are characterized by the differential index
- Measure of the singularity
- By differentiating equations algebraic variables can be eliminated
- If this is done often enough, the equations take the form of  explicit ODEs
- Index of a system of DAE is the number of derivatives you must take to express the system as an equivalent system of explicit ODEs
- ODEs have differential index of 0