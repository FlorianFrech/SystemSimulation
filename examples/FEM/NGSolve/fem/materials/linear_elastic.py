from ngsolve import Sym, Grad, Trace, Det, InnerProduct, log, sqrt, Id

class LinearElasticMaterial:
    def __init__(self, E, nu):
        self.E = E
        self.nu = nu
        self.lmbda = (E * nu) / ((1 + nu) * (1 - 2 * nu))
        self.mu = E / (2 * (1 + nu))
        
    def eps(self, u):
        return Sym(Grad(u))
    
    def energy_density(self, eps):
        return 0.5*self.lmbda*Trace(eps)**2 + self.mu*InnerProduct(eps, eps)
    
    def sigma(self, eps, u):
        return self.lmbda*Trace(eps)*Id(u.dim) + 2*self.mu*eps