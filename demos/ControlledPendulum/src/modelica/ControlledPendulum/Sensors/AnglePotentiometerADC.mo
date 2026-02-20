within ControlledPendulum.Sensors;

model AnglePotentiometerADC
  "Potentiometer + ADC angle measurement with saturation"

  import Modelica.Constants.pi;

  // Input
  Modelica.Blocks.Interfaces.RealInput theta(unit="rad") "Measured angle";

  // Output
  Modelica.Blocks.Interfaces.RealOutput v_out(unit="V") "Quantized ADC voltage";

  // Public parameters
  parameter Integer nBits(min=8) = 10 "ADC resolution [bits]";
  parameter Real theta_min(unit="rad") = -1.3 * pi/9 "Minimum measurable angle";
  parameter Real theta_max(unit="rad") = 1.3 * pi/9 "Maximum measurable angle";

  parameter Real v_pot(unit="V") = 5 "Potentiometer supply voltage";
  parameter Real v_adc(unit="V") = 3 "ADC reference voltage";
  parameter Real r_top(unit="Ohm") = 80e3 "Top resistor of divider";
  parameter Real r_bottom(unit="Ohm") = 20e3 "Bottom resistor of divider";
  parameter Real pot_range(unit="rad") = 3/4 * 2 * pi "Mechanical pot range";

  parameter Boolean useNoise = false "Enable external noise input";
  parameter Real samplePeriod(unit="s") = 0.01 "Sampling period";

  // Optional external noise input (additive)
  Modelica.Blocks.Interfaces.RealInput noise(unit="V") if useNoise;

protected
  // Quantizer settings
  parameter Integer levels = integer(2^nBits - 1);
  parameter Real delta(unit="V") = v_adc / levels "LSB size";

  // Internal signals
  Real theta_sat(unit="rad");
  Real pot_angle(unit="rad");
  Real v_pot_wiper(unit="V");
  Real v_adc_in(unit="V");
  Real v_adc_noisy(unit="V");
  Integer code;
  Real v_quant(unit="V");
  Real noise_val(unit="V");
  discrete Real v_hold(unit="V", start=0);

equation
  // Saturate angle to sensor limits
  theta_sat = min(max(theta, theta_min), theta_max);

  // Map angle to potentiometer rotation (centered)
  pot_angle = theta_sat - (theta_min + theta_max) / 2 + pot_range / 2;

  // Potentiometer divider mapping
  v_pot_wiper = v_pot * (1 - r_bottom / (r_top + r_bottom)
                   - (pot_range - pot_angle) / pot_range);

  // Clamp to ADC input range
  v_adc_in = min(max(v_pot_wiper, 0), v_adc);

  // Add optional external noise and clamp again
  noise_val = if useNoise then noise else 0;
  v_adc_noisy = min(max(v_adc_in + noise_val, 0), v_adc);

  v_out = v_hold;

algorithm
  when initial() then
    code := min(max(integer((v_adc/2 + v_adc_noisy) / delta + 0.5), 0), levels);
    v_quant := code * delta;
    v_hold := v_quant;
  end when;

  when sample(0, samplePeriod) then
    code := min(max(integer(v_adc_noisy / delta + 0.5), 0), levels);
    v_quant := code * delta;
    v_hold := v_quant;
  end when;

  annotation(
    experiment(StartTime = 0, StopTime = 10, Interval = 0.002));
end AnglePotentiometerADC;
