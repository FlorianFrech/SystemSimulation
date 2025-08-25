within ControlledPendulum;

model Sensor
  import Modelica.Constants.pi;
  
  // Typedefs
  type Voltage = Real(unit="V");
  type Resistance = Real(unit="Ohm");
  type Angle = Real(unit="rad");
  
  // Parameters
  parameter Voltage U_0_pot = 5;
  parameter Voltage U_ADC = 3;
  parameter Resistance R3 = 80e3;
  parameter Resistance R4 = 20e3;
  parameter Angle alpha_max = 3/4 * 2 * pi;
  parameter Integer nBits = 8;
  
  parameter Angle q_min = -pi/2 - pi/9;
  parameter Angle q_max = -pi/2 + pi/9;
  
  // Input
  Modelica.Blocks.Interfaces.RealInput q(unit="rad");
  
  // Outputs
  output Voltage U_a;
  output Voltage U_q;
  
  protected
  Angle alpha;
  Integer levels;
  Voltage delta;

algorithm
  // Potentiometer mapping
  alpha := q - (q_min + q_max) / 2 + alpha_max/2;
  U_a := U_0_pot * (0.8 - alpha / alpha_max);
  
  // Uniform quantizer:
  levels := integer(2.0^nBits - 1);
  delta := U_ADC / levels;
  
  // Round to nearest code and map back to volts
  U_q := delta*integer(U_a / delta);
end Sensor;