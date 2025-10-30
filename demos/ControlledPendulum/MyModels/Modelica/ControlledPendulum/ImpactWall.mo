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
  parameter Real k(unit="N.m/rad") = 5e4 "Contact stiffness";
  parameter Real c(unit="N.m.s/rad")=50 "Contact damping while compressing";
  parameter Real eps(unit="rad")=1e-4 "If > 0, use smooth ReLU for penetration with smooth eps";
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
  Real pen_raw(unit="rad");
  Real pen(unit="rad") "Smoothed penetration";
  Real pen_dot(unit="rad/s") "Time derivative of penetration (smoothed)";
  Real comp(unit="rad/s") "Compression rate = max(pen_dot,0)";

equation
  // Oriented, smooth gap and helper
  x    = sense * (q - q_wall);
  root = sqrt(x*x + eps*eps);
  
  // Smooth Heaviside and smooth ReLU (soft penetration)
  H   = 0.5*(1 + x/root);
  pen_raw = 0.5*(x + root);
  pen = pen_raw - 0.5 * eps;
  penetration = max(pen, 0);
  
  // Penetration rate: dpen/dx = H, so dpen/dt = H * dq/dt
  pen_dot = H * sense * omega;

  // Compression-only rate (noEvent to avoid superfluous events)
  comp = noEvent( max(pen_dot, 0) );
  
  // Hunt–Crossley-like compliant torque (n=1): k*pen + c*pen*comp
  // Negative sign: torque resists penetration (acts to reduce q when x>0)
  torque = -sense * ( k*pen + c*pen*comp );

  // Boolean contact flag without generating events
  contact = noEvent( x > 0 );

end ImpactWall;