within ControlledPendulum.Plants;

model PendulumWithCompliantWall
  extends PendulumBase;

  // Parameters
  parameter Boolean with_contact(start=true)
    "Boolean flag for contact simulation";

  // Components
  ImpactWallCompliant wall(k=1e10,
                           theta_wall=0,
                           sense=-1,
                           J_eq=J) if with_contact;

  // Outputs
  Modelica.Blocks.Interfaces.BooleanOutput contact;

equation
  if with_contact then
    connect(theta, wall.theta);
    connect(omega, wall.omega);
    tau_total = tau + wall.torque;
    contact = wall.contact;
  else
    tau_total = tau;
    contact = false;
  end if;

  annotation(
    experiment(StartTime = 0, StopTime = 2, Interval = 0.001)
  );
end PendulumWithCompliantWall;
