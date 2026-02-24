within ControlledPendulum.Plants;

model PendulumWithDiscreteWall
  /*
  Event-driven contact model for a 1-DOF pendulum.
  */

  extends PendulumBase;

  // Parameters
  parameter Real theta_wall(unit="rad") = 0;
  parameter Integer sense = 1;
  parameter Real restitution = 1 "Coefficient of restitution";

  // Outputs
  Modelica.Blocks.Interfaces.BooleanOutput contact(start=false, fixed=true);

equation
contact = sense * (theta - theta_wall) < 0;
  when contact then
    reinit(omega, -omega);  
  end when;
  
  tau_total = tau;

  annotation(
    experiment(StartTime = 0, StopTime = 10, Interval = 0.002)
  );
end PendulumWithDiscreteWall;
