from ngsolve import Det, Grad, Id, Trace, Inv


class NeoHookeanMaterial:
    def __init__(self, E, nu):
        self.E = E
        self.nu = nu
        self.lmbda = (E * nu) / ((1 + nu) * (1 - 2 * nu))
        self.mu = E / (2 * (1 + nu))

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
