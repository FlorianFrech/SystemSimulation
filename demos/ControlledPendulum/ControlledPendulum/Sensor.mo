within ControlledPendulum;

model Sensor
  import Modelica.Constants.pi;

  // Parameters
  parameter Real U_0_pot(unit="V") = 5;
  parameter Real U_ADC(unit="V") = 3;
  parameter Real R3(unit="Ohm") = 80e3;
  parameter Real R4(unit="Ohm") = 20e3;
  parameter Real alpha_max(unit="rad") = 3/4 * 2 * pi;
  parameter Integer nBits = 8;
  
  parameter Real q_min(unit="rad") = -pi/9;
  parameter Real q_max(unit="rad") = pi/9;
  
  // Input
  Modelica.Blocks.Interfaces.RealInput q(unit="rad");
  
  // Outputs
  Modelica.Blocks.Interfaces.RealOutput U_q(unit="V");
  
  protected
  Real alpha(unit="rad");
  Integer levels;
  Real delta(unit="V");
  Real U_a(unit="V") ;

algorithm
  // Potentiometer mapping
  alpha := q - (q_min + q_max) / 2 + alpha_max/2;
  U_a := U_0_pot * (1 - R4/(R3+R4) - (alpha_max - alpha) / alpha_max);
  
  // Uniform quantizer:
  levels := integer(2.0^nBits - 1);
  delta := U_ADC / levels;
  
  // Round to nearest code and map back to volts
  U_q := delta*integer(U_a / delta);
end Sensor;