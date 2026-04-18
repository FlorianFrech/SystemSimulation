from ngsolve import Det, Grad, Id, Trace, Inv, sqrt

class SVKMaterial:
    """Saint Venant-Kirchhoff material — linear elasticity at finite strains.
    
    Strain energy: ψ = (λ/2) tr(E)² + μ tr(E²)
    where E = ½(C - I) is the Green-Lagrange strain tensor.
    
    Suitable for large-rotation / small-strain problems like a stiff pendulum.
    """

    def __init__(self, E, nu):
        self.E = E
        self.nu = nu
        self.mu = E / (2 * (1 + nu))
        # Plane-stress effective first Lamé parameter (σ_zz = 0)
        self.lmbda = E * nu / (1 - nu * nu)

    def C(self, u):
        F = Id(u.dim) + Grad(u)
        return F.trans * F

    def E_gl(self, u):
        """Green-Lagrange strain tensor E = ½(C - I)."""
        return 0.5 * (self.C(u) - Id(u.dim))

    def psi(self, C, u):
        """Strain energy density for SVK."""
        E = 0.5 * (C - Id(u.dim))
        trE = Trace(E)
        return 0.5 * self.lmbda * trE * trE + self.mu * Trace(E * E)

    def PK2_svk(self, u):
        """2nd Piola-Kirchhoff stress: S = λ tr(E) I + 2μ E."""
        E = self.E_gl(u)
        return self.lmbda * Trace(E) * Id(2) + 2 * self.mu * E

    def PK1_svk(self, u):
        """1st Piola-Kirchhoff stress: P = F * S."""
        F = Id(2) + Grad(u)
        return F * self.PK2_svk(u)
    
    def cauchy_stress(self, u):
        """True (Cauchy) stress in the current configuration: σ = (1/J) F S F^T"""
        F = Id(2) + Grad(u)
        J = Det(F)
        S = self.PK2_svk(u)
        return (1 / J) * F * S * F.trans

    def von_mises(self, u):
        """Von Mises stress assuming plane stress (σ_zz = σ_xz = σ_yz = 0).

        σ_vM = sqrt(σ_xx² + σ_yy² - σ_xx·σ_yy + 3·σ_xy²)
        """
        sigma = self.cauchy_stress(u)
        sxx, syy, sxy = sigma[0, 0], sigma[1, 1], sigma[0, 1]
        return sqrt(sxx * sxx + syy * syy - sxx * syy + 3 * sxy * sxy)


class NeoHookeanMaterial:
    def __init__(self, E, nu):
        self.E = E
        self.nu = nu
        self.mu = E / (2 * (1 + nu))
        # Plane-stress effective first Lamé parameter (σ_zz = 0)
        self.lmbda = E * nu / (1 - nu * nu)

    def C(self, u):
        F = Id(u.dim) + Grad(u)
        return F.trans * F

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

    def PK2_neo_hookean(self, u):
        """2nd Piola-Kirchhoff stress for the Neo-Hookean model.
        
        S = mu * (I - det(C)^(-lam/(2*mu)) * C^{-1})
        """
        CC = self.C(u)
        return self.mu * (Id(2) - Det(CC)**(-self.lmbda / (2 * self.mu)) * Inv(CC))

    def PK1_neo_hookean(self, u):
        """1st Piola-Kirchhoff stress: P = F * S."""
        F = Id(2) + Grad(u)
        return F * self.PK2_neo_hookean(u)
    
    def cauchy_stress(self, u):
        """True Cauchy stress in the current (deformed) configuration.
        
        σ = (1/J) F S F^T
        """
        F = Id(2) + Grad(u)
        J = Det(F)
        S = self.PK2_neo_hookean(u)      # or self.PK2_neo_hookean(u) for Neo-Hookean
        return (1 / J) * F * S * F.trans

    def von_mises(self, u):
        """Von Mises stress assuming plane stress (σ_zz = σ_xz = σ_yz = 0).

        σ_vM = sqrt(σ_xx² + σ_yy² - σ_xx·σ_yy + 3·σ_xy²)
        """
        sigma = self.cauchy_stress(u)
        sxx, syy, sxy = sigma[0, 0], sigma[1, 1], sigma[0, 1]
        return sqrt(sxx * sxx + syy * syy - sxx * syy + 3 * sxy * sxy)
