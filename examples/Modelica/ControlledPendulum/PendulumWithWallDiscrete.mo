within ControlledPendulum;

model PendulumWithWallDiscrete  
  // Extensions
  extends ControlledPendulum.Pendulum;
  
  // imports
  import Modelica.Constants.pi;
  
  // Parmeters
  parameter Real q_wall(unit="rad") = 0;
  parameter Real e = 0.8 "Restitution coefficient";
    
protected
  // Internal constants
  constant Real eps = 1e-4 "Prevent chattering for q_state close to q_wall";

equation
  when {q_state > q_wall} then
    reinit(omega_state, -e * pre(omega_state));
  end when;
  
  annotation(
    experiment(StartTime = 0, StopTime = 2, Interval = 0.001)
  );

end PendulumWithWallDiscrete;