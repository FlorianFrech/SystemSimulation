within ControlledPendulum;

model Drive
  /*
  Model implements an electric drive which takes a control signal u_control and
  an angular velocity of the shaft as input and computes the output torque at the shaft.
  */
  
  // Imports
  import Modelica.Constants.pi;
  
  // Parameter
  parameter Real U_M(unit="V") = 16;
  
  // Constants
  constant Real U_rated(unit="V") = 48;
  constant Real R_M(unit="Ohm") = 0.151;
  constant Real L_M(unit="H") = 121e-6;
  constant Real n_0(unit="1/min") = 12916;
  constant Real k_M(unit="N.m/A") = 0.03;
  constant Integer i_M = 60;
  constant Real eta_M = 0.85;
  constant Real k_n(unit="(1/min)/V") = n_0/U_rated;
  
  // Inputs
  Modelica.Blocks.Interfaces.RealInput u_control;
  Modelica.Blocks.Interfaces.RealInput omega(unit="rad/s");
  
  // Outputs
  Modelica.Blocks.Interfaces.RealOutput torque(unit="N.m", start=0, fixed=true);

protected
  // Internal Constants
  

  
  // Internal Parameters
  Real I(unit="A", start=0);
  Real U(unit="V", start=0);
  Real n(unit="1/min", start=0);

equation
  // Electrical input based on u_control
  U = U_M * u_control;
  
  // Meachanical speed in rpm (omega_m is in rad/s)
  n = i_M * omega * 30 / pi;
  
  // Current dynamics and torque
  der(I) = (U - R_M * I - n/k_n) / L_M;
  torque = eta_M * i_M * k_M * I;
  
end Drive;