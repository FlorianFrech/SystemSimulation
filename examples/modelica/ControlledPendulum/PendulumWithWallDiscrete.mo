within ControlledPendulum;

model PendulumWithWallDiscrete  
  // Extensions
  extends ControlledPendulum.Pendulum;
  
  // imports
  import Modelica.Constants.pi;
  
  // Parameters
  parameter Real q_wall(unit="rad") = pi/4 "Wall position angle";
  parameter Real e(min=0, max=1) = 0.8 "Restitution coefficient (0=plastic, 1=elastic)";
  
  // State variable to track contact
  Boolean contact "True when pendulum is in contact with wall";

equation
  // Detect contact: pendulum angle exceeds wall position
  contact = q > q_wall;
  
  // When contact occurs, reverse and reduce velocity
  when contact then
    reinit(omega, -e * pre(omega));
  end when;
  
  annotation(
    experiment(StartTime = 0, StopTime = 5, Tolerance = 1e-6, Interval = 0.001),
  );

end PendulumWithWallDiscrete;