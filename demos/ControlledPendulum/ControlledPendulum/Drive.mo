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
  parameter Integer i_M = 60;
  parameter Real eta_M = 0.85;
  parameter Real k_n(unit="(1/min)/V") = n_0/U_rated;
  
  // Inputs
  Modelica.Blocks.Interfaces.RealInput u_control;
  Modelica.Blocks.Interfaces.RealInput omega(unit="rad/s");
  
  // Outputs
  Modelica.Blocks.Interfaces.RealOutput torque(unit="N.m", start=0, fixed=true);

protected
  Real I(unit="A", start=0);
  Real U(unit="V", start=0);
  Real n(unit="1/min", start=0);

equation
  // Electrical input
  U = U_M * u_control;
  
  // Meachanical speed in rpm (omega_m is in rad/s)
  n = i_M * omega * 30 / pi;
  
  // Current dynamics and torque
  der(I) = (U - R_M * I - n/k_n) / L_M;
  torque = eta_M * i_M * k_M * I;

end Drive;