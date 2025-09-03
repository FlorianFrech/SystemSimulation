within ControlledPendulum;

model ImpactWall
  /*
  The model implements the effect of an impact wall for the 1-DOF pendulum.
  The wall causes an impact at the angle q_wall.
  The impact is defined by
    - q_wall: angular position of the wall
    - e: restitution coefficient
    - k: angular contact stiffness
    - c: angular contact damping
    - eps: parameter for relaxation of the penetration strictness (reduced for chattering minimization)
  */
  
  // Imports
  import Modelica.Constants.pi;

  // Parameters
  parameter Real q_wall(unit="rad") = 0 "Angular position of the wall";
  parameter Real e(min=0, max=1) = 0.75 "Restitution coefficient";
  parameter Real k(unit="N.m/rad") = 5e4 "Contact stiffness";
  parameter Real c(unit="N.m.s/rad")=50 "Contact damping while compressing";
  parameter Real eps(unit="rad")=1e-4 "If > 0, use smooth ReLU for penetration with smooth eps";
    
  // Inputs
  Modelica.Blocks.Interfaces.RealInput q(unit="rad");
  Modelica.Blocks.Interfaces.RealInput omega(unit="rad/s");
  
  // Outputs
  Modelica.Blocks.Interfaces.RealOutput torque(unit="N.m") "Contact torque";
  Modelica.Blocks.Interfaces.BooleanOutput contact "True when penetration > 0";
  Modelica.Blocks.Interfaces.RealOutput penetration(unit="rad");
  Modelica.Blocks.Interfaces.RealOutput omega_plus(unit="rad/s");
  
protected
  Real pen "penetration (>=0)";
  Real v_n "normal velocity component for compressing";

equation
  // Smooth penetration calculation
  pen = 0.5*((q - q_wall) + sqrt((q - q_wall)^2 + eps^2)) - 0.5*eps;
  
  penetration = pen;

  // Contact detection based on meaningful penetration
  contact = pen > 0.1*eps;
  
  // Damping velocity: only during compression phase
  v_n = if pen > 0.1*eps then max(omega, 0) else 0;
  
  // Compliant contact torque (Hunt-Crossley model)
  torque = -k * pen - c * v_n;

  // Post impact velocity (only when actually impacting)
  omega_plus = if contact and omega > 0 then -e * omega else omega;
  
end ImpactWall;