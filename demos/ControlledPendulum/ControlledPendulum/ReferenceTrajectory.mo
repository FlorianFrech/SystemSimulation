within ControlledPendulum;

model ReferenceTrajectory
  // Constants
  import Modelica.Constants.pi; 
  
  // Output
  Modelica.Blocks.Interfaces.RealOutput q_ref(unit="rad");
  
  // Parameters
  parameter Real mean(unit="rad") = 0;
  parameter Real amplitude(unit="rad") = pi/4;

equation
  q_ref = mean + amplitude * sin(time);
  
  annotation(
    experiment(StartTime = 0, StopTime = 10, Interval = 0.002)
  );

end ReferenceTrajectory;