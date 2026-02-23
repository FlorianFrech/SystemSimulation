model PendulumDiscreteContact  
  // Imports
  import Modelica.Constants.pi;

  // Parameters
  parameter Real m(unit="kg") = 40;
  parameter Real L(unit="m") = 0.6;
  parameter Real theta0(unit="rad") = 0;
  parameter Real omega0(unit="rad/s") = 0;
  parameter Real g(unit="m/s2") = 9.81;
  parameter Real inertia(unit="kg.m2") = 20;
  parameter Real theta_wall (unit="rad") = 0;
  parameter Integer sense = -1; 
  parameter Real restitution = 1 "Coefficient of restitution";
  parameter Real gap_tol(unit="rad") = 0 "Contact tolerance (>=0)";

  // Input torque at the pivot
  Modelica.Blocks.Interfaces.RealInput torque(unit="N.m");

  // Outputs
  Modelica.Blocks.Interfaces.RealOutput theta(unit="rad");
  Modelica.Blocks.Interfaces.RealOutput omega(unit="rad/s");
  Modelica.Blocks.Interfaces.RealOutput alpha(unit="rad/s2") = der(omega);
  Modelica.Blocks.Interfaces.BooleanOutput contact;
  
protected
  Real x(unit="rad");

initial equation
  theta = theta0;
  omega = omega0;

equation
  der(theta) = omega;
  der(omega) = -(m * g * L / inertia) * sin(theta) + torque / inertia;
  x = sense * (theta - theta_wall);
  contact = (x >= -gap_tol);
  
  when contact and not pre(contact) then
    reinit(omega, -restitution * omega);
    reinit(theta, theta_wall);
  end when;
  
end PendulumDiscreteContact;
