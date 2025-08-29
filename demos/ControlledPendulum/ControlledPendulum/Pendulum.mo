within ControlledPendulum;

model Pendulum
  import Modelica.Constants.pi;
  import Modelica.Constants.g_n;
  import SI = Modelica.Units.SI;

  // Parameters
  parameter Real m(unit="kg") = 80*0.2;
  parameter Real L(unit="m") = 0.4;
  parameter Real g(unit="m/s2") = 9.81;
  parameter Real q0(unit="rad") = -pi/2;

  // States
  Real q(unit="rad", start = 0);
  Real omega(unit="rad/s", start = 0);

  // Input torque at the pivot
  Modelica.Blocks.Interfaces.RealInput torque(unit="N.m") "Control torque";

  // Outputs
  Modelica.Blocks.Interfaces.RealOutput q_state(unit="rad") = q;
  Modelica.Blocks.Interfaces.RealOutput omega_state(unit="rad/s") = omega;

initial equation
  der(q) = 0;
  der(omega) = 0;
equation
  der(q)    = omega;
  der(omega) = -(g / L) * sin(q) + torque/(m * L^2);
end Pendulum;
