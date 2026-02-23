within ControlledPendulum.Plants;

partial model PendulumBase
  // Parameters
  parameter Real m(unit="kg") = 10.8429606 "Pendulum mass";
  parameter Real L(unit="m") = 0.181650853 "Pendulum length";
  parameter Real J(unit="kg.m2") = 0.442268222 "Moment of inertia about pivot";
  parameter Real g(unit="m/s2") = 9.81 "Gravitational acceleration";
  parameter Real theta_start(unit="rad") = 0 "Initial angle";
  parameter Real omega_start(unit="rad/s") = 0 "Initial angular velocity";

  // Friction parameters
  parameter Real b_viscous(unit="N.m.s/rad") = 0.0 "Viscous friction";
  parameter Real tau_c(unit="N.m") = 0 "Coulomb friction";
  parameter Real omega_eps(unit="rad/s") = 1e-3 "Smoothing for Coulomb friction";

  // Input torque at the pivot
  Modelica.Blocks.Interfaces.RealInput tau(unit="N.m") "Applied torque";

  // Outputs
  Modelica.Blocks.Interfaces.RealOutput theta(unit="rad");
  Modelica.Blocks.Interfaces.RealOutput omega(unit="rad/s");
  Modelica.Blocks.Interfaces.RealOutput alpha(unit="rad/s2") = der(omega);

protected
  Real tau_total(unit="N.m");
  Real tau_fric(unit="N.m");

initial equation
  theta = theta_start;
  omega = omega_start;

equation
  // Friction torque
  tau_fric = b_viscous * omega + tau_c * Modelica.Math.tanh(omega / omega_eps);

  // Pendulum dynamics
  der(theta) = omega;
  der(omega) = -(m * g * L / J) * sin(theta) + (tau_total - tau_fric) / J;
end PendulumBase;
