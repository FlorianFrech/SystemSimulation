Kružík, M., & Roubíček, T. (2019). *Mathematical Methods in Continuum Mechanics of Solids*. Springer International Publishing. [https://doi.org/10.1007/978-3-030-02065-1](https://doi.org/10.1007/978-3-030-02065-1)

# Hyperelastic Materials

- An elastic material is called hyperelastic if there is a stored energy function
- A hyperelastic material model and its relevancy cannot be proven
- It emphasizes reversibility of deformations and the idea that energy can be stored in the material and used later without losses to do work.
- In this sense, hyperelastic materials are conservative
- First hyperelastic material models were developed by Rivilin and Mooney
- Frame indifference of hyperelastic material means that for all rotations $R$ and $F\in \text{GL}^+(d)$ it holds: $\phi(x, RF) = \phi(X, F)$

## Geometrically Nonlinear Lamé Material (St. Venant--Kirchhoff Material)

The St. Venant--Kirchhoff material is a geometrically nonlinear elastic material model.
It uses the Green--Lagrange strain tensor

$$
E = \frac{1}{2}(F^\top F - I)
$$

and defines the second Piola--Kirchhoff stress response as

$$
\tilde{S}(F) = \lambda \, \mathrm{tr}(E) I + 2 G E .
$$

Here, $\lambda$ and $G$ are the Lamé constants.
The constant $G > 0$ is the shear modulus.
It is often denoted by $\mu$, but the notation $G$ may be used to avoid conflicts with other meanings of $\mu$.

The bulk modulus $K$ measures the resistance of the material to hydrostatic pressure and is related to the Lamé constants by

$$
K = \lambda + \frac{2}{d}G ,
$$

where $d$ is the spatial dimension.

For isotropic elasticity, the material can also be described by Young's modulus $E_{\mathrm{Young}}$ and Poisson's ratio $\nu$.
Young's modulus describes the stress response under uniaxial elongation.
Poisson's ratio describes the relative transverse contraction under such loading.

The bulk modulus and shear modulus can be expressed as

$$
K = \frac{E_{\mathrm{Young}}}{3(1 - 2\nu)}
$$

and

$$
G = \frac{E_{\mathrm{Young}}}{2(1+\nu)} .
$$

The physical dimensions of $\lambda$, $K$, $G$, and $E_{\mathrm{Young}}$ are Pascal:

$$
\mathrm{Pa} = \frac{\mathrm{J}}{\mathrm{m}^3} = \frac{\mathrm{N}}{\mathrm{m}^2}.
$$

Poisson's ratio $\nu$ is dimensionless.

The corresponding strain-energy density is

$$
\varphi(F)
=
\frac{\lambda}{2}\left(\mathrm{tr}\,E\right)^2
+
G |E|^2,
\qquad
E = \frac{1}{2}(F^\top F - I).
$$

This energy density produces the St. Venant--Kirchhoff stress law by differentiation with respect to the strain tensor.
The model is suitable for finite rotations with small elastic strains, but it is not intended for strongly nonlinear material behavior at large strains.

## Compressible Mooney--Rivlin Material

The compressible Mooney--Rivlin material is a hyperelastic material model.
Its stored energy density has the form

$$
\varphi(x,F)
=
a(x)|F|^2
+
b(x)|\operatorname{Cof}F|^2
+
\gamma(\det F),
$$

where $F$ is the deformation gradient, $\operatorname{Cof}F$ is the cofactor of $F$, and $\det F$ describes the local volume change.

The material parameters satisfy

$$
a,b > 0,
$$

and the volumetric part is commonly written as

$$
\gamma(\delta)
=
c_1 \delta^2
-
c_2 \log \delta,
\qquad
c_1,c_2 > 0.
$$

For small strains, this energy can be expanded in terms of the Green--Lagrange strain tensor

$$
E = \frac{1}{2}(C-I),
\qquad
C = F^\top F,
$$

and takes the form

$$
\varphi(F)
=
\frac{\lambda}{2}(\operatorname{tr}E)^2
+
G|E|^2
+
R(E),
$$

where

$$
R(E)=\mathcal{O}(|E|^3)
\qquad \text{for } E \to 0.
$$

Thus, for small strains, the compressible Mooney--Rivlin material has the same quadratic leading-order behavior as the St. Venant--Kirchhoff material.
The constants $\lambda$ and $G$ are the Lamé constants.
The remaining term $R(E)$ collects higher-order nonlinear strain terms.

Given $\lambda$ and $G$, the constants $a$, $b$, $c_1$, and $c_2$ must satisfy compatibility relations so that the small-strain limit matches the desired Lamé constants.
In particular,

$$
c_2 = \lambda + 2G,
$$

and

$$
2a + 2b = G,
\qquad
4b + 4c_1 = \lambda.
$$