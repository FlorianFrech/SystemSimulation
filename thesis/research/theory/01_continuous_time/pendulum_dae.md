## Hidden Constraints and Differentiation Index of the Cartesian Pendulum

Consider the Cartesian pendulum model with position variables $(q_x, q_y)$, velocity variables $(v_x, v_y)$, and constraint force $F$. The rigid rod imposes the constraint

$$
0 = q_x^2 + q_y^2 - L^2.
$$

This constraint makes the system a differential-algebraic equation (DAE). Its hidden constraints appear by differentiating the position-level constraint with respect to time.

---

### Position-Level Constraint

The pendulum bob must remain on a circle of radius $L$:

$$
0 = q_x^2 + q_y^2 - L^2.
$$

This is the original algebraic constraint.

---

### First Differentiation: Velocity-Level Constraint

Differentiate the constraint once with respect to time:

$$
0 = \frac{d}{dt}\left(q_x^2 + q_y^2 - L^2\right)
  = 2 q_x \dot{q}_x + 2 q_y \dot{q}_y.
$$

Substituting

$$
\dot{q}_x = v_x, \qquad \dot{q}_y = v_y,
$$

gives

$$
\boxed{0 = q_x v_x + q_y v_y.}
$$

This is the **velocity-level hidden constraint**. It states that the velocity must be tangential to the circular path.

---

### Second Differentiation: Acceleration-Level Constraint

Differentiate the velocity constraint:

$$
0 = \frac{d}{dt}(q_x v_x + q_y v_y)
  = \dot{q}_x v_x + q_x \dot{v}_x + \dot{q}_y v_y + q_y \dot{v}_y.
$$

Substitute

$$
\dot{q}_x = v_x, \qquad \dot{q}_y = v_y,
$$

and the equations of motion

$$
\dot{v}_x = -\frac{q_x}{mL}F, \qquad
\dot{v}_y = -\frac{q_y}{mL}F - g.
$$

Then

$$
0 = v_x^2 + q_x\left(-\frac{q_x}{mL}F\right)
    + v_y^2 + q_y\left(-\frac{q_y}{mL}F - g\right).
$$

Expanding gives

$$
0 = v_x^2 + v_y^2 - \frac{F}{mL}(q_x^2 + q_y^2) - g q_y.
$$

Using the original constraint \(q_x^2 + q_y^2 = L^2\), this simplifies to

$$
\boxed{0 = v_x^2 + v_y^2 - \frac{FL}{m} - g q_y.}
$$

Hence the constraint force can be written explicitly as

$$
\boxed{F = \frac{m}{L}\left(v_x^2 + v_y^2 - g q_y\right).}
$$

This is the **acceleration-level hidden constraint**.

---

### Third Differentiation: ODE for the Constraint Force

Differentiate the explicit expression for $F$ with respect to time:

$$
F = \frac{m}{L}\left(v_x^2 + v_y^2 - g q_y\right).
$$

Thus,

$$
\dot{F} = \frac{m}{L}\left(2 v_x \dot{v}_x + 2 v_y \dot{v}_y - g \dot{q}_y\right).
$$

Substitute

$$
\dot{v}_x = -\frac{q_x}{mL}F, \qquad
\dot{v}_y = -\frac{q_y}{mL}F - g, \qquad
\dot{q}_y = v_y,
$$

to obtain

$$
\dot{F}
= \frac{m}{L}\left(
2 v_x \left(-\frac{q_x}{mL}F\right)
+ 2 v_y \left(-\frac{q_y}{mL}F - g\right)
- g v_y
\right).
$$

Expanding yields

$$
\dot{F}
= \frac{m}{L}\left(
-\frac{2 v_x q_x F}{mL}
-\frac{2 v_y q_y F}{mL}
- 2 g v_y
- g v_y
\right).
$$

Factor the first two terms:

$$
\dot{F}
= \frac{m}{L}\left(
-\frac{2F}{mL}(q_x v_x + q_y v_y)
- 3 g v_y
\right).
$$

Using the velocity-level constraint

$$
q_x v_x + q_y v_y = 0,
$$

the first term vanishes, and therefore

$$
\boxed{\dot{F} = -\frac{3mg}{L} \, v_y.}
$$

---

### Interpretation

The original Cartesian pendulum model contains the algebraic constraint

$$
q_x^2 + q_y^2 - L^2 = 0,
$$

which must be differentiated repeatedly to obtain an explicit evolution equation for the algebraic variable $F$. Since three differentiations are required to reach an ordinary differential equation, the Cartesian pendulum is a **DAE of differentiation index 3**.

The differentiated constraints are:

- **position level**
  $$
  q_x^2 + q_y^2 - L^2 = 0
  $$

- **velocity level**
  $$
  q_x v_x + q_y v_y = 0
  $$

- **acceleration level**
  $$
  v_x^2 + v_y^2 - \frac{FL}{m} - g q_y = 0
  $$

- **ODE level**
  $$
  \dot{F} = -\frac{3mg}{L} v_y
  $$

These are the hidden constraints that reveal the index-3 structure of the model.
