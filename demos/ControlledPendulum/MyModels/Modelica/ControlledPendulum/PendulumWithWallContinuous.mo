within ControlledPendulum;

model PendulumWithWallContinuous 
  // Imports
  import Modelica.Constants.pi;
  
  Pendulum            pendulum(q0=1);
  ImpactWall          wall(q_wall=0, sense=-1);
  
  // Add outputs for FMU usage
  Modelica.Blocks.Interfaces.RealOutput q(unit="rad");
  Modelica.Blocks.Interfaces.RealOutput omega(unit="rad/s");
  Modelica.Blocks.Interfaces.RealOutput alpha(unit="rad/s2");
  
equation
  // Wall connections (reads state, returns contact torque)
  connect(pendulum.q,   wall.q);
  connect(pendulum.omega, wall.omega);

  // Torque summation: drive torque + wall torque -> pendulum
  connect(wall.torque,        pendulum.torque);
  
  // Output equations
  q = pendulum.q;
  omega = pendulum.omega;
  alpha = pendulum.alpha;
    
  annotation(
    experiment(StartTime = 0, StopTime = 2, Interval = 0.001)
  );

end PendulumWithWallContinuous;