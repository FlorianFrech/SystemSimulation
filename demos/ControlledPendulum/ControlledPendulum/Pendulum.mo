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
  import Modelica.Constants.g_n;

  // Parameters
  parameter Real m(unit="kg") = 80*0.2;
  parameter Real L(unit="m") = 0.4;
  parameter Real q0(unit="rad") = -pi/6;
  parameter Real omega0(unit="rad/s") = 0;

  // Input torque at the pivot
  Modelica.Blocks.Interfaces.RealInput torque(unit="N.m") "Control torque";

  // Outputs
  Modelica.Blocks.Interfaces.RealOutput q_state(unit="rad");
  Modelica.Blocks.Interfaces.RealOutput omega_state(unit="rad/s");

protected
  // Internal constants
  constant Real g(unit="m/s2") = 9.81;

initial equation
  q_state = q0;
  omega_state = omega0;
   
equation
  der(q_state)    = omega_state;
  der(omega_state) = -(g / L) * sin(q_state) + torque/(m * L^2);
end Pendulum;
