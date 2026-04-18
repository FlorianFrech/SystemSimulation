## Theory Chapter — Concepts to Introduce

These are **general, model-independent** concepts that any FEM dynamics problem requires. A reader should understand them before seeing any specific implementation.

### 1. Kinematics (from `1_modeling_elasticity.ipynb`)
The foundational building blocks every subsequent concept depends on:
- Deformation map $\phi$, displacement $\mathbf{u} = \phi(\mathbf{X}) - \mathbf{X}$
- Deformation gradient $\mathbf{F} = \mathbf{I} + \nabla\mathbf{u}$
- Right Cauchy-Green tensor $\mathbf{C} = \mathbf{F}^T\mathbf{F}$
- Green-Lagrange strain $\mathbf{E} = \frac{1}{2}(\mathbf{C} - \mathbf{I})$
- Feasibility condition $J = \det\mathbf{F} > 0$

### 2. Hyperelastic constitutive theory
- Concept of strain energy density $W(\mathbf{C})$
- Isotropy and the Rivlin-Ericksen theorem (invariants $I_1, I_2, I_3$)
- Derivation of PK2 from energy: $\mathbf{S} = 2\frac{\partial W}{\partial \mathbf{C}}$
- The material model hierarchy: **Linear elastic → SVK → Neo-Hookean**, and *why* each step is needed (the large-rotation argument you already discussed)

### 3. Stress measures and their relationships
Introduce all four and their exact transformations — this is pure continuum mechanics and belongs in theory:

$$\mathbf{S} \xrightarrow{\mathbf{F}\cdot} \mathbf{P} \xrightarrow{\frac{1}{J}(\cdot)\mathbf{F}^T} \boldsymbol{\sigma} \xrightarrow{\text{deviatoric}} \sigma_\text{vM}$$

Which configuration each stress lives in, and which is physically measurable (Cauchy).

### 4. Variational formulation and equilibrium
- Total energy functional $J(\mathbf{u}) = \int_\Omega W(\mathbf{C}) \,d\mathbf{X} - \int_\Omega \mathbf{f}\cdot\mathbf{u}\,d\mathbf{X} - \int_{\Gamma_N}\mathbf{g}\cdot\mathbf{u}\,ds$
- Principle of stationary energy / virtual work
- Strong form: $\operatorname{div}\mathbf{P} = -\mathbf{f}$, boundary conditions
- The pull-back/push-forward to the deformed configuration yielding the Cauchy equilibrium

### 5. Elastodynamics and Newmark time integration
This is the core temporal framework, fully general — explain it in theory:
- Equations of motion: $\rho\ddot{\mathbf{u}} = \operatorname{div}\mathbf{P} + \mathbf{f}$
- Newmark scheme (as in `4_elasto_dynamics.ipynb`):

$$\frac{\mathbf{u}^{n+1} - \mathbf{u}^n}{\tau} = \frac{\mathbf{v}^n + \mathbf{v}^{n+1}}{2}, \qquad \frac{\mathbf{v}^{n+1} - \mathbf{v}^n}{\tau} = \frac{\mathbf{a}^n + \mathbf{a}^{n+1}}{2}$$

- The substitution that turns the time-discrete system into a **purely displacement-driven nonlinear problem** at each step — this is the key insight that connects dynamics to the static solver
- Conservation properties (energy, symplecticity) and why Newmark is preferred over explicit schemes for stiff structural problems

### 6. Nonlinear solution: Newton's method
- Linearization of the residual $\mathbf{R}(\mathbf{u}) = 0$
- Tangent stiffness matrix $\mathbf{K}_T = \frac{\partial \mathbf{R}}{\partial \mathbf{u}}$
- Newton iteration and convergence properties
- Why `NewtonMinimization` (energy minimization) vs. `Newton` (residual root-finding) — brief conceptual note

---

## Case Study Chapter — Pendulum-Specific Implementation Details

These concepts are **application-specific** or **implementation choices** that would clutter the theory chapter. They belong in the case study as "here is how the general theory is applied and extended."

### 1. Geometric setup and mesh
- The 2D plane-stress pendulum geometry (rod + head + hole), thickness parameter, OCCGeometry construction — purely specific to this problem

### 2. Mixed FE space with Lagrange multipliers for the pivot constraint
- `VectorH1 × NumberSpace²` — the rotation constraint at the pivot boundary is a pendulum-specific kinematic constraint, not general elastodynamics

### 3. Distributed torque traction and the moment-arm calculation
- The linear/bipolar weight distributions for applying torque as a surface traction — this is an engineering modeling choice specific to this pendulum, not general FEM theory

### 4. Rigid-body proxy for extracting $\theta$, $\omega$, $\alpha$
- Using the deformed displacement field to extract a scalar angle by integration — a pendulum-specific post-processing step

### 5. Contact mechanics (penalty method)
- `ContactBoundary`, incremental gap function, penalty energy — this is an advanced and self-contained topic. Mention it exists in theory if you like, but the penalty formulation details belong in the case study

### 6. Stress computation and von Mises visualization
- The *specific* push-forward $\boldsymbol{\sigma} = \frac{1}{J}\mathbf{F}\mathbf{S}\mathbf{F}^T$ in NGSolve, `Interpolate` vs. `Set`, the `_gf_sigma_norm_history` recording — these are implementation details building on the theory already established

### 7. Adaptive micro-stepping near contact
- The gap-distance-based time step reduction is an algorithmic implementation decision, not a theoretical concept

---

## Recommended Chapter Structure at a Glance

```
Theory Chapter
├── 1. Kinematics (F, C, E, J)
├── 2. Hyperelastic constitutive theory (W, S, SVK vs. Neo-Hookean)
├── 3. Stress measures (PK1, PK2, Cauchy, von Mises)
├── 4. Variational formulation & equilibrium
├── 5. Elastodynamics + Newmark scheme
└── 6. Newton linearization

Case Study Chapter (FEM Pendulum)
├── 1. Geometry and mesh (OCC, rod/head/hole)
├── 2. Mixed FE space + pivot constraint (Lagrange multipliers)
├── 3. Torque application (distributed traction)
├── 4. Rigid-body proxy (θ, ω, α extraction)
├── 5. Contact mechanics (penalty method, gap detection)
├── 6. Stress post-processing (Cauchy push-forward, von Mises)
└── 7. Adaptive time stepping near contact
```

The **key dividing principle**: if a concept appears verbatim in `4_elasto_dynamics.ipynb` or `5_nonlinearelasticity.ipynb` with a generic geometry, it belongs in theory. If it only makes sense because there is a pivot, a wall, or a swinging angle, it belongs in the case study.