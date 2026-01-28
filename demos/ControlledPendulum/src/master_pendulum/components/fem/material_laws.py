from ngsolve import Det, Grad, Id, Trace


class NeoHookeanMaterial:
    def __init__(self, E, nu):
        self.E = E
        self.nu = nu
        self.lmbda = (E * nu) / ((1 + nu) * (1 - 2 * nu))
        self.mu = E / (2 * (1 + nu))

    def C(self, u):
        F = Id(u.dim) + Grad(u)
        return F.trans * F

    def energy_density(self, C, u):
        return (
            0.5
            * self.mu
            * (
                Trace(C - Id(u.dim))
                + 2 * self.mu / self.lmbda * Det(C) ** (-self.lmbda / 2 / self.mu)
                - 1
            )
        )

    def sigma(self, C, u):
        return 2 * self.mu * (C - Id(u.dim)) + self.lmbda * Trace(C - Id(u.dim)) * Id(2)
