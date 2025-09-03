within ControlledPendulum;

model AngleEncoder
  /*
  Model represents a potentiometer-like angule encoder.
  Analog voltage from potentiometer is quantized using an ADC with nBits and a maximum output voltage of U_ADC.
  The mean of the reference trajectory angle is mapped to half of the available ADC voltage.
  */
  
  // Imports
  import Modelica.Constants.pi;
  
  // Input
  Modelica.Blocks.Interfaces.RealInput q(unit="rad");
  
  // Outputs
  Modelica.Blocks.Interfaces.RealOutput U_q(unit="V");
  
  // Public Parameters
  parameter Real nBits = 8 "ADC resolution [bits]";
  parameter Real q_min(unit="rad") = -pi/9;
  parameter Real q_max(unit="rad") = pi/9;
  
protected
  // Constants
  constant Real U_0_pot(unit="V") = 5;
  constant Real U_ADC(unit="V") = 3;
  constant Real R3(unit="Ohm") = 80e3;
  constant Real R4(unit="Ohm") = 20e3;
  constant Real alpha_max(unit="rad") = 3/4 * 2 * pi;
  
  // Internal Parameters
  parameter Real levels = (2^nBits - 1);
  parameter Real delta(unit="V") = U_ADC / levels;
  
  // Internal Variables
  Real alpha(unit="rad");
  Real U_a(unit="V") ;

algorithm
  // Potentiometer mapping
  alpha := q - (q_min + q_max) / 2 + alpha_max/2;
  U_a := U_0_pot * (1 - R4 / (R3 + R4) - (alpha_max - alpha) / alpha_max);
  
  // Round to nearest code and map back to volts
  U_q := delta*integer(U_a / delta);
end AngleEncoder;