from ngsolve import Id, Grad, Trace, Det, Sym, InnerProduct, log, sqrt

# Hyperelastic material model: Neo-Hookean   
def C(self, u):
    F = Id(u.dim) + Grad(u)
    return F.trans * F
        
def neo_hooke (self, C, mu, lam):    
    return 0.5*mu*(Trace(C-Id(self._u.dim)) + 2*mu/lam*Det(C)**(-lam/2/mu)-1)    
    
def sigma_neo_hooke(self, u, lam, mu):
    d = u.dim
    F = Id(d) + Grad(u)
    J = Det(F)
    C = F.trans * F
        
    # Psi = mu/2*(I1 -d) - mu*ln(J) + lam/2*ln(J)^2
    I1 = Trace(C)
    Psi = mu/2 * (I1 - d) - mu * log(J) + lam/2 *log(J)**2
    
        # Second Piola-Kirchhoff stress
    C_var = C.MakeVariable()
    Psi_var = mu/2 * (Trace(C_var) - d) - mu * log(Det(F)) + lam/2 * log(Det(F))**2
    S = Psi_var.Diff(C_var)
        
    # Cauchy stress
    sigma = 1.0 / J * F * S * F.trans
    return sigma    
    
def von_mises_2d(self, sig):
    sxx, syy, sxy = sig[0,0], sig[1,1], sig[0,1]
    return sqrt(sxx*sxx - sxx*syy + syy*syy + 3.0*sxy*sxy)

# Linear elastic material model
def eps(self, u):
    return Sym(Grad(u))
    
def linear_elastic(self, eps, mu, lam):
    return 0.5*lam*Trace(eps)**2 + mu*InnerProduct(eps, eps)
    
def sigma_linear(self, eps, u, lam, mu):
    return lam*Trace(eps)*Id(u.dim) + 2*mu*eps