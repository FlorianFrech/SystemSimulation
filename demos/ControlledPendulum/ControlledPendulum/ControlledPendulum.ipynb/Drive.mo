within ControlledPendulum;

model Drive
  // Constants
  import Modelica.Constants.pi;
  
  // Parameters
  parameter Real U_M(unit="V") = 16;
  parameter Real U_rated(unit="V") = 48;
  parameter Real R_M(unit="Ohm") = 0.151;
  parameter Real L_M(unit="H") = 121e-6;
  parameter Real n_0(unit="1/min") = 12916;
  parameter Real k_M(unit="N.m/A") = 0.03;
  parameter Integer i_G = 60;
  parameter Real eta_G = 0.85;
  parameter Real k_n(unit="(1/min)/V") = n_0/U_rated;
  
  // Inputs
  Modelica.Blocks.Interfaces.RealInput u;
  Modelica.Blocks.Interfaces.RealInput omega_m(unit="rad/s");
  
  // Outputs
  Modelica.Blocks.Interfaces.RealOutput M(unit="N.m");

protected
  Real I(unit="A", start=0);
  Real U(unit="V");
  Real n(unit="1/min");

equation
  // Electrical input
  U = U_M * max(-1, min(u,1));
  
  // Meachanical speed in rpm (omega_m is in rad/s)
  n = i_G * omega_m * 30 / pi;
  
  // Current dynamics and torque
  der(I) = (U - R_M*I - n/k_n) / L_M;
  M = eta_G * i_G * k_M * I;

end Drive;