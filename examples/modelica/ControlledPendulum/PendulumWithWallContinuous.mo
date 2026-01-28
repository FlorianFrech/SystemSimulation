within ControlledPendulum;

model PendulumWithWallContinuous 
  // Imports
  import Modelica.Constants.pi;
  
  Pendulum            pendulum(q0=1);
  
  ImpactWall          wall(q_wall=0, sense=-1);
  
equation
  // Wall connections (reads state, returns contact torque)
  connect(pendulum.q_state,   wall.q);
  connect(pendulum.omega_state, wall.omega);

  // Torque summation: drive torque + wall torque -> pendulum
  connect(wall.torque,        pendulum.torque);
  
  annotation(
    experiment(StartTime = 0, StopTime = 2, Interval = 0.001)
  );

end PendulumWithWallContinuous;