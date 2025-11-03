within ControlledPendulum;

model Pendulum
  /*
  The model represents a simple 1-DOF pendulum model with a head with mass m at
  a radial distance of L relative to the hinge joint center. The connection between
  joint and head is considered as massless.
  The state angle q_state is 0 for vertical alignment between head and joint center.
  */
  
  // Imports
  import Modelica.Constants.pi;

  // Parameters
  parameter Real m(unit="kg") = 40;
  parameter Real L(unit="m") = 0.6732;
  parameter Real q0(unit="rad") = 0;
  parameter Real omega0(unit="rad/s") = 0;
  parameter Real g(unit="m/s2") = 9.81;

  // Input torque at the pivot
  Modelica.Blocks.Interfaces.RealInput torque(unit="N.m");

  // Outputs
  Modelica.Blocks.Interfaces.RealOutput q(unit="rad");
  Modelica.Blocks.Interfaces.RealOutput omega(unit="rad/s");
  Modelica.Blocks.Interfaces.RealOutput alpha(unit="rad/s2") = der(omega);

initial equation
  q = q0;
  omega = omega0;

equation
  der(q)    = omega;
  der(omega) = -(g / L) * sin(q) + torque/(m * L^2);
end Pendulum;
