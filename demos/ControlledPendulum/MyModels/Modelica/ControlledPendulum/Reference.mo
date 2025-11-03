within ControlledPendulum;

model Reference 
  // Constants
  import Modelica.Constants.pi; 
  
  // Output
  Modelica.Blocks.Interfaces.RealOutput q_ref(unit="rad");
  
  // Parameters
  parameter Real mean(unit="rad") = 0;
  parameter Real amplitude(unit="rad") = pi/9;
  parameter Real frequency(unit="Hz") = 0.25;

equation
  q_ref = mean + amplitude * sin(2 * pi * frequency * time);
  annotation(
    experiment(StartTime = 0, StopTime = 10, Interval = 0.002),
  Icon(graphics = {Rectangle(origin = {-3, 0}, extent = {{-51, 60}, {51, -60}}), Text(origin = {-2, 0}, extent = {{-22, 12}, {22, -12}}, textString = "Reference Signal")}));

end Reference;