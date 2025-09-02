within ControlledPendulum;

model ImpactWall
  // Imports
  import Modelica.Constants.pi;

  // Parameters
  parameter Real q_wall(unit="rad") = pi/6 "Angular position of the wall";
  parameter Real e(min=0, max=1) = 0.75 "Restitution coefficient";
  parameter Real k(unit="N.m/rad") = 5e4 "Contact stiffness";
  parameter Real c(unit="N.m.s/rad")=50 "Contact damping while compressing";
  parameter Real eps(unit="rad")=0 "If > 0, use smooth ReLU for penetration with smooth eps";
    
  // Inputs
  Modelica.Blocks.Interfaces.RealInput q(unit="rad");
  Modelica.Blocks.Interfaces.RealInput omega(unit="rad/s");
  
  // Outputs
  Modelica.Blocks.Interfaces.RealOutput tau(unit="N.m") "Contact torque";
  Modelica.Blocks.Interfaces.BooleanOutput contact "True when penetration > 0";
  Modelica.Blocks.Interfaces.RealOutput penetration(unit="rad");
  Modelica.Blocks.Interfaces.RealOutput omega_plus(unit="rad/s");
  
protected
  Real pen "penetration (>=0)";
  Real v_n "normal velocity when compressing";

equation
  // Penetration when q beyond q_wall
  if eps <= 0 then
    pen = max(q-q_wall, 0);
  else
    // Smooth ReLU to reduce event chatter
    pen = 0.5*((q - q_wall) + sqrt((q - q_wall)^2 + eps^2)) - 0.5*eps;
  end if;
  
  penetration = pen;
  
  // Only damp while compressing the wall (omega > 0) and in contact
  v_n = if pen > 0 then max(omega, 0) else 0;
  
  // Compliant contact torque
  tau = -k * pen - c * v_n;
  
  // Set contact flag
  contact = q > q_wall;
  
  // Post impact velocity for the master using a restitution flip
  omega_plus = if(q >= q_wall and omega > 0) then -e * omega else omega;
end ImpactWall;