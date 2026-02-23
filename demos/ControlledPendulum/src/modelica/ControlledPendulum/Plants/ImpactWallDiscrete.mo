within ControlledPendulum.Plants;

model ImpactWallDiscrete
  "Event-driven contact detection for a rigid wall"

  // Parameters
  parameter Real theta_wall(unit="rad") = 0 "Wall angle";
  parameter Integer sense = -1 "(+1: contact for theta>theta_wall, -1: contact for theta<theta_wall)";
  parameter Real gap_tol(unit="rad") = 0 "Contact tolerance (>=0)";

  // Inputs
  Modelica.Blocks.Interfaces.RealInput theta(unit="rad");

  // Outputs
  Modelica.Blocks.Interfaces.BooleanOutput contact;

equation
  // Oriented gap (positive -> penetration)
  contact = (sense * (theta - theta_wall) >= -gap_tol);
end ImpactWallDiscrete;
