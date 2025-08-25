within ControlledPendulum;

model Pendulum
  import Modelica.Constants.pi;
  import Modelica.Constants.g_n;
  import SI = Modelica.Units.SI;

  // Parameters
  parameter SI.Mass m = 1 "Pendulum mass";
  parameter SI.Length L = 1 "Pendulum length";

  // States
  Real q(unit="rad", start = -pi/2 + pi/9) "Angle from vertical";
  Real omega(unit="rad/s", start = 0) "Angular velocity";

  // Input torque at the pivot
  Modelica.Blocks.Interfaces.RealInput tau(unit="N.m") "Control torque";

  // Outputs
  Modelica.Blocks.Interfaces.RealOutput q_out(unit="rad") = q;
  Modelica.Blocks.Interfaces.RealOutput omega_out(unit="rad/s") = omega;

equation
  der(q)    = omega;
  der(omega) = -(g_n / L) * sin(q) + tau/(m * L^2);
end Pendulum;
