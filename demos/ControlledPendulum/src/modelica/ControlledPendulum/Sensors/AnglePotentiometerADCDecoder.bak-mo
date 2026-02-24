within ControlledPendulum.Sensors;

model AnglePotentiometerADCDecoder
  "Inverse mapping from ADC voltage back to quantized angle"

  import Modelica.Constants.pi;

  // Input
  Modelica.Blocks.Interfaces.RealInput v_in(unit="V") "ADC voltage";

  // Output
  Modelica.Blocks.Interfaces.RealOutput theta(unit="rad") "Quantized angle";

  // Parameters (must match encoder)
  parameter Integer nBits(min=8) = 10 "ADC resolution [bits]";
  parameter Real theta_min(unit="rad") = -1.3 * pi/9 "Minimum measurable angle";
  parameter Real theta_max(unit="rad") = 1.3 * pi/9 "Maximum measurable angle";

  parameter Real v_pot(unit="V") = 5 "Potentiometer supply voltage";
  parameter Real v_adc(unit="V") = 3 "ADC reference voltage";
  parameter Real r_top(unit="Ohm") = 80e3 "Top resistor of divider";
  parameter Real r_bottom(unit="Ohm") = 20e3 "Bottom resistor of divider";
  parameter Real pot_range(unit="rad") = 3/4 * 2 * pi "Mechanical pot range";
  parameter Real samplePeriod(unit="s") = 0.01 "Sampling period";

protected
  parameter Integer levels = integer(2^nBits - 1);
  parameter Real delta(unit="V") = v_adc / levels "LSB size";
  parameter Real divider_offset = r_bottom / (r_top + r_bottom);

  Real v_clamped(unit="V");
  Integer code;
  Real v_quant(unit="V");
  Real pot_angle(unit="rad");
  Real theta_raw(unit="rad");
  discrete Real theta_hold(unit="rad", start=0);

equation
  // Clamp to ADC range
  v_clamped = min(max(v_in, 0), v_adc);

  theta = theta_hold;

algorithm
  when initial() then
    // Force initial output to zero rad
    theta_hold := 0;
  end when;

  when sample(0, samplePeriod) then
    code := min(max(integer(v_clamped / delta + 0.5), 0), levels);
    v_quant := code * delta;
    pot_angle := pot_range * (v_quant / v_pot + divider_offset);
    theta_raw := pot_angle + (theta_min + theta_max) / 2 - pot_range / 2;
    theta_hold := min(max(theta_raw, theta_min), theta_max);
  end when;

  annotation(
    experiment(StartTime = 0, StopTime = 10, Interval = 0.002));
end AnglePotentiometerADCDecoder;
