within ControlledPendulum;

model PendulumWithWallContinuous 
  // Imports
  import Modelica.Constants.pi;
  
  Pendulum            pendulum(q0=0);
  ImpactWall          wall(k=1e10, q_wall=0, sense=-1, J_eq=pendulum.inertia);
  
  Modelica.Blocks.Interfaces.RealInput torque(unit="N.m");
  
  Modelica.Blocks.Interfaces.RealOutput q(unit="rad");
  Modelica.Blocks.Interfaces.RealOutput omega(unit="rad/s");
  Modelica.Blocks.Interfaces.RealOutput alpha(unit="rad/s2");
  //Modelica.Blocks.Interfaces.BooleanOutput contact;

protected
  Modelica.Blocks.Math.Add torqueSum(k1=1, k2=1);
  
equation
  // Wall connections (reads state, returns contact torque)
  connect(pendulum.q,   wall.q);
  connect(pendulum.omega, wall.omega);

  // Torque summation: drive torque + wall torque -> pendulum
  connect(torque, torqueSum.u1);
  connect(wall.torque, torqueSum.u2);
  connect(torqueSum.y, pendulum.torque);
  
  // Output equations
  q = pendulum.q;
  omega = pendulum.omega;
  alpha = pendulum.alpha;
  //contact = wall.contact;
    
  annotation(
    experiment(StartTime = 0, StopTime = 2, Interval = 0.001)
  );

end PendulumWithWallContinuous;