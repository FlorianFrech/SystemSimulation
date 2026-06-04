kunkel_nonlinear_dae

# Nonlinear differential-alegbaric equations

General nonlinear systems of differential algebraic equations of the form

$$F(t, x, \dot x) =0$$

- For convenience we switch to real-valued problems
- Complex-valued problems require to analyze real and imaginary part of the equation and unknown separately
- First case: $m=n$ number of equations equal the number of unknowns
- We consider  $F \in C (\mathbb I \times \mathbb D_x \times \mathbb D_{\dot x}, \mathbb R^n)$ with $\mathbb D_x, D_{\dot x} \underline \subset \mathbb R^n$
    
    - $F$: function / mapping its domain into real-valued space
    - $\mathbb I$: Time interval
    - $\mathbb D_x$: domain of the state variable $x(t)$
    - $\mathbb D_{\dot x}$: domain of the derivative $\dot x(t)$
- Initial condition: $x(t_0) = x_0$

# Structured Problem of Non-Linear DAE

- Applications modeled by differential-algebraic equations lead often to special structures like the pendulum in in Cartesian coordinates
- Making use of this structure usually leads to a simplified analysis
- All structured problems that we will discuss in the sequel are semi-explicit
    
    $$\dot x = f(x_1, x_2), 0 = g (x_1, x_2)$$
    
    - with different assumptions of functions $f$ and $g$