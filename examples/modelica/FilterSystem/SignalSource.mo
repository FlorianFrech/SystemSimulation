within FilterSystem;

model SignalSource
  // Constants
  import Modelica.Constants.pi;
  
  // Output connector
  Modelica.Blocks.Interfaces.RealOutput U_in(unit="V");
  
  // Parameters (matching Python MODULE PARAMETERS)
  parameter Real A1(unit="V") = 60;
  parameter Real A2(unit="V") = 5;
  parameter Real f1(unit="Hz") = 0.159;
  parameter Real f2(unit="Hz") = 7.96;
  
  // Internal variables
  Real s1(unit="V");
  Real s2(unit="V");
  
equation
  // Generate the two sine waves (matching Python signal_generator function)
  s1 = A1 * sin(2 * pi * f1 * time);
  s2 = A2 * sin(2 * pi * f2 * time);
  
  // Output is the sum of the signals (s1 + s2)
  U_in = s1 + s2; 
end SignalSource;