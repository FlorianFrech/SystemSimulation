within ControlledPendulum.Plants;

model ImpactWallDiscrete
  "Event-driven contact detection for a rigid wall"

  // Parameters
  parameter Real theta_wall(unit="rad") = 0 "Wall angle";
  parameter Integer sense = -1 "(+1: contact for theta>theta_wall, -1: contact for theta<theta_wall)";

  // Inputs
  Modelica.Blocks.Interfaces.RealInput theta(unit="rad");
  Modelica.Blocks.Interfaces.RealInput omega(unit="rad/s");

  // Outputs
  Modelica.Blocks.Interfaces.BooleanOutput contact;

protected
  Real x(unit="rad");

equation
  // Oriented gap (positive -> penetration)
  x = sense * (theta - theta_wall);
  contact = (x > 0) and (sense * omega < 0);
end ImpactWallDiscrete;
