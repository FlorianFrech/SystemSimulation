model VoltageSource
  import Modelica.Constants.pi;

  Modelica.Electrical.Analog.Interfaces.PositivePin p;
  Modelica.Electrical.Analog.Interfaces.NegativePin n;

  parameter Real A1 = 60 "Amplitude 1 [V]";
  parameter Real A2 = 5  "Amplitude 2 [V]";
  parameter Real f1 = 0.159 "Frequency 1 [Hz]";
  parameter Real f2 = 7.96  "Frequency 2 [Hz]";
  parameter Real phase1 = 0 "Phase 1 [rad]";
  parameter Real phase2 = 0 "Phase 2 [rad]";

protected
  Real v1, v2;

equation
  v1 = A1*sin(2*pi*f1*time + phase1);
  v2 = A2*sin(2*pi*f2*time + phase2);

  p.v - n.v = v1 + v2;
  0 = p.i + n.i;

end VoltageSource;