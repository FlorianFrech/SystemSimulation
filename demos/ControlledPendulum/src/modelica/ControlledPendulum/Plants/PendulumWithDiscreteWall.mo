within ControlledPendulum.Plants;

model PendulumWithDiscreteWall
  /*
  Event-driven contact model for a 1-DOF pendulum.
  */

  extends PendulumBase;

  // Parameters
  parameter Real theta_wall(unit="rad") = 0;
  parameter Integer sense = -1;
  parameter Real restitution = 1 "Coefficient of restitution";

  // Components
  ImpactWallDiscrete wall(theta_wall=theta_wall, sense=sense);

  // Outputs
  Modelica.Blocks.Interfaces.BooleanOutput contact;

initial equation
  contact = wall.contact;

equation
  tau_total = tau;
  connect(theta, wall.theta);
  connect(omega, wall.omega);
  contact = wall.contact;

  when contact and not pre(contact) then
    reinit(omega, -restitution*omega);
  end when;

  annotation(
    experiment(StartTime = 0, StopTime = 10, Interval = 0.002)
  );
end PendulumWithDiscreteWall;
