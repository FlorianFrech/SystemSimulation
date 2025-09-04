within ControlledPendulum;

model Reference
  /*
  Model creates the reference trajectory which the pendulum tries to follow.
  */
  
  // Constants
  import Modelica.Constants.pi; 
  
  // Output
  Modelica.Blocks.Interfaces.RealOutput q_ref(unit="rad");
  
  // Parameters
  parameter Real mean(unit="rad") = 0;
  parameter Real amplitude(unit="rad") = pi/4;
  parameter Real frequency(unit="Hz") = 0.25;

equation
  q_ref = mean + amplitude * sin(2 * pi * frequency * time);
  
  annotation(
    experiment(StartTime = 0, StopTime = 10, Interval = 0.002)
  );

end Reference;