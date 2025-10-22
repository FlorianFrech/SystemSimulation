within ControlledPendulum;

model Demo_UndrivenWithWall
  // Imports
  import Modelica.Constants.pi;
  // Components
  Pendulum pendulum(q0= -pi / 6);
  ImpactWall wall(q_wall= 0);

equation
  // Angular pendulum position and velocity as inputs for ImpactWall ModelicaServices
  connect(pendulum.q_state, wall.q);
  connect(pendulum.omega_state, wall.omega);
  
  // Torque at impact acts back on Pendulum
  connect(wall.torque, pendulum.torque);
  
  annotation(
    experiment(StartTime = 0, StopTime = 10, Interval = 0.002)
  );

end Demo_UndrivenWithWall;