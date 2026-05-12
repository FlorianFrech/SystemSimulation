within ControlledPendulum.Trajectories;

model SetPoint
  "Sine-wave angle setpoint with configurable offset, phase, and start time"

  import Modelica.Constants.pi;

  // Output
  Modelica.Blocks.Interfaces.RealOutput theta_ref(unit="rad") "Reference angle";

  // Parameters
  parameter Real offset(unit="rad") = 0 "Mean angle";
  parameter Real amplitude(unit="rad") = pi/9 "Peak amplitude in rad";
  parameter Real frequency(unit="Hz") = 3 "Sine frequency";
  parameter Real phase(unit="rad") = 0 "Phase at t = startTime";

protected
  parameter Real omega(unit="rad/s") = 2 * pi * frequency;

equation
  theta_ref = offset + amplitude * sin(omega * time + phase);

end SetPoint;
