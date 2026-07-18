"""Plane-stress hyperelastic material laws used by the FEM pendulum.

The :class:`HyperelasticMaterial` base captures everything the two concrete
laws share — the plane-stress Lamé parameters, the right Cauchy-Green tensor,
and the derived Cauchy / von Mises stresses. Each concrete law only has to
supply its strain-energy density ``psi`` and second Piola-Kirchhoff stress
``PK2``. All quantities are NGSolve coefficient functions of the displacement
grid function ``u``.
"""

from abc import ABC, abstractmethod

from ngsolve import Det, Grad, Id, Inv, Trace, sqrt


class HyperelasticMaterial(ABC):
    """Abstract base for 2D plane-stress hyperelastic materials.

    Args:
        E: Young's modulus in Pa.
        nu: Poisson's ratio.

    Attributes:
        mu: Shear modulus ``E / (2 (1 + nu))``.
        lmbda: Plane-stress effective first Lamé parameter
            ``E nu / (1 - nu^2)`` (enforces ``sigma_zz = 0``).
    """

    def __init__(self, E: float, nu: float):
        self.E = E
        self.nu = nu
        self.mu = E / (2 * (1 + nu))
        # Plane-stress effective first Lamé parameter (σ_zz = 0)
        self.lmbda = E * nu / (1 - nu * nu)

    # ---- Kinematics (shared) ----
    def C(self, u):
        """Right Cauchy-Green deformation tensor C = Fᵀ F."""
        F = Id(u.dim) + Grad(u)
        return F.trans * F

    def E_gl(self, u):
        """Green-Lagrange strain tensor E = ½(C - I)."""
        return 0.5 * (self.C(u) - Id(u.dim))

    # ---- Constitutive law (subclass-specific) ----
    @abstractmethod
    def psi(self, C, u):
        """Strain-energy density ψ as a function of the Cauchy-Green tensor."""

    @abstractmethod
    def PK2(self, u):
        """Second Piola-Kirchhoff stress S."""

    # ---- Derived stresses (shared) ----
    def PK1(self, u):
        """First Piola-Kirchhoff stress: P = F S."""
        F = Id(u.dim) + Grad(u)
        return F * self.PK2(u)

    def cauchy_stress(self, u):
        """True (Cauchy) stress in the current configuration: σ = (1/J) F S Fᵀ."""
        F = Id(u.dim) + Grad(u)
        J = Det(F)
        S = self.PK2(u)
        return (1 / J) * F * S * F.trans

    def von_mises(self, u):
        """Von Mises stress assuming plane stress (σ_zz = σ_xz = σ_yz = 0).

        σ_vM = sqrt(σ_xx² + σ_yy² - σ_xx·σ_yy + 3·σ_xy²)
        """
        sigma = self.cauchy_stress(u)
        sxx, syy, sxy = sigma[0, 0], sigma[1, 1], sigma[0, 1]
        return sqrt(sxx * sxx + syy * syy - sxx * syy + 3 * sxy * sxy)


class SVKMaterial(HyperelasticMaterial):
    """Saint Venant-Kirchhoff material — linear elasticity at finite strains.

    Strain energy: ψ = (λ/2) tr(E)² + μ tr(E²)
    where E = ½(C - I) is the Green-Lagrange strain tensor.

    Suitable for large-rotation / small-strain problems like a stiff pendulum.
    """

    def psi(self, C, u):
        """Strain energy density for SVK."""
        E = 0.5 * (C - Id(u.dim))
        trE = Trace(E)
        return 0.5 * self.lmbda * trE * trE + self.mu * Trace(E * E)

    def PK2(self, u):
        """2nd Piola-Kirchhoff stress: S = λ tr(E) I + 2μ E."""
        E = self.E_gl(u)
        return self.lmbda * Trace(E) * Id(u.dim) + 2 * self.mu * E


class NeoHookeanMaterial(HyperelasticMaterial):
    """Compressible Neo-Hookean material with plane-stress Lamé parameters."""

    def psi(self, C, u):
        return (
            0.5
            * self.mu
            * (
                Trace(C - Id(u.dim))
                + (2 * self.mu / self.lmbda) * Det(C) ** (-self.lmbda / 2 / self.mu)
                - 1
            )
        )

    def PK2(self, u):
        """2nd Piola-Kirchhoff stress: S = μ (I - det(C)^(-λ/(2μ)) C⁻¹)."""
        CC = self.C(u)
        return self.mu * (Id(u.dim) - Det(CC) ** (-self.lmbda / (2 * self.mu)) * Inv(CC))
