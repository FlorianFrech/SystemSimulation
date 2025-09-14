within ControlledPendulum;

model Demo_UndrivenWallDiscrete
  /*
  The model extends the 1-DOF pendulum model by a wall
  which causes the Pendulum   head to bounce against the wall.
  The contat causes a discrete event which reinitializes
  the continuous state variable of the Pendulum.
  */
  
  // Extensions
  extends ControlledPendulum.Pendulum;
  
  // imports
  import Modelica.Constants.pi;
  
  // Parmeters
  parameter Real q_wall(unit="rad") = 0;
  parameter Real e = 0.8 "Restitution coefficient";
  
protected
  // Internal constants
  constant Real eps = 1e-3 "Prevent chattering for q_state close to q_wall";

equation
  when {q_state > q_wall} then
    reinit(omega_state, -e * pre(omega_state));
  end when;
  
  annotation(
    experiment(StartTime = 0, StopTime = 10, Interval = 0.002)
  );

end Demo_UndrivenWallDiscrete;