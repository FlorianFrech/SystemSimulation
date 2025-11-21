within ControlledPendulum;

model Pendulum
  /*
  The model represents a simple 1-DOF pendulum model with:
   - m: haead point mass in kg
   - L: distance head to joint in m
   - inertia: moment of inertia of the Pendulum
   - q0: initial position in rad
   - omega0: initial angular velocity in rad/s
  */
  
  // Imports
  import Modelica.Constants.pi;

  // Parameters
  parameter Real m(unit="kg") = 41.70369562497543;
  parameter Real L(unit="m") = 0.6055028481722639;
  parameter Real q0(unit="rad") = 0;
  parameter Real omega0(unit="rad/s") = 0;
  parameter Real g(unit="m/s2") = 9.81;
  parameter Real inertia(unit="kg.m2") = 18.90035177381065;

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
  der(omega) = -(m * g * L / inertia) * sin(q) + torque / inertia;
end Pendulum;
