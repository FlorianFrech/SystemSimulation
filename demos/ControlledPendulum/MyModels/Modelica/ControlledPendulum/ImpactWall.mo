within ControlledPendulum;

model ImpactWall
  /*
    Compliant impact wall for a 1-DOF pendulum angle q.

    - Wall at angle q_wall.
    - Smooth penetration pen ≈ max(q - q_wall, 0) using a differentiable approximation
      to avoid events and chattering in co-simulation.
    - Hunt–Crossley style damping for compression: torque_d ∝ pen * max(dpen/dt, 0).

    Notes:
    - This is a compliant (continuous) contact. No explicit restitution coefficient is used.
    - For an event-driven, perfectly inelastic/elastic impact, create a separate discrete model.
  */
  
  // Imports
  import Modelica.Constants.pi;

  // Parameters
  parameter Real q_wall(unit="rad") = 0 "Angular position of the wall";
  parameter Real k(unit="N.m/rad") = 1e10 "Contact stiffness";
  parameter Real eps(unit="rad")=1e-4 "If > 0, use smooth ReLU for penetration with smooth eps";
  parameter Boolean autoEps = true "Scale smoothing with stiffness";
  parameter Real tauTol(unit="N.m") = 50 "Acceptable pre-contact torque bias";
  
  parameter Boolean autoDamp = true "If true, set damping from k and J_eq";
  parameter Real zeta = 0.7 "Damping ratio when damping = true";
  parameter Real J_eq(unit="kg.m2") = 1 "Refelected inertia ar the joint";
  parameter Real c = 0 "If manual damping is used (autoDamp = false)";
  parameter Real c_eff = if autoDamp then 2*zeta*sqrt(k*J_eq) else c;
  
  
  // Effective smoothing used
  parameter Real eps_eff(unit="rad") = if autoEps then min(eps, 2*tauTol/max(1e-12,k)) else eps;

  parameter Real penEps(unit="rad") = 1e-8 "Contact on/off threshold for boolean output";
  parameter Integer sense = +1 "(+1: contact for q>q_wall, -1: contact for q<q_wall)";
    
  // Inputs
  Modelica.Blocks.Interfaces.RealInput q(unit="rad");
  Modelica.Blocks.Interfaces.RealInput omega(unit="rad/s");
  
  // Outputs
  Modelica.Blocks.Interfaces.RealOutput torque(unit="N.m") "Contact torque";
  Modelica.Blocks.Interfaces.BooleanOutput contact "True when penetration > 0";
  Modelica.Blocks.Interfaces.RealOutput penetration(unit="rad");
  
protected
  Real x(unit="rad") "Gap: positive mean penetration";
  Real root(unit="rad") "sqrt(x^2 + eps^2)";
  Real H "Smooth Heaviside in [0,1]";
  Real pen(unit="rad") "Smoothed penetration";
  Real pen_dot(unit="rad/s") "Time derivative of penetration (smoothed)";
  Real comp(unit="rad/s") "Compression rate = max(pen_dot,0)";

equation
  // Oriented gap
  x    = sense * (q - q_wall);
  root = sqrt(x*x + eps_eff*eps_eff);

  // Smooth ReLU (nonnegative, zero far before contact); no offset
  pen = 0.5*(x + root);
  penetration = pen;
  
  // Penetration rate and compression
  H       = 0.5*(1 + x/root);
  pen_dot = H * sense * omega;
  comp    = noEvent(max(pen_dot, 0));
  
  // Hunt–Crossley-like compliant torque
  torque = -sense * ( k*pen + c_eff*pen*comp );
  
  // Boolean Contact Indicator
  contact = pen > penEps;
end ImpactWall;