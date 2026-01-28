within ControlledPendulum;

model Drive_QStat
  /*
  Model implements a quasistatic electric drive which takes a control signal u_control and
  an angular velocity of the shaft as input and computes the output torque at the shaft.
  */
  
  // Imports
  import Modelica.Constants.pi;
  
  // Parameter
  parameter Real U_M(unit="V") = 16;
  parameter Real U_rated(unit="V") = 48;
  parameter Real R_M(unit="Ohm") = 0.151;
  parameter Real L_M(unit="H") = 121e-6;
  parameter Real k_M(unit="N.m/A") = 0.03;
  parameter Real n_0(unit="1/min") = 12916;  
  parameter Real i_M = 60;
  parameter Real eta_M = 0.85;

  // Derived Parameter
  parameter Real k_n(unit="(1/min)/V") = n_0/U_rated;
  parameter Real k_e(unit="V.s/rad") = 60 / (2 * pi * k_n);
  
  // Inputs
  Modelica.Blocks.Interfaces.RealInput u_control;
  Modelica.Blocks.Interfaces.RealInput omega(unit="rad/s");
  
  // Outputs
  Modelica.Blocks.Interfaces.RealOutput torque(unit="N.m", start=0);

  // Internal Variables
  Real U(unit="V");
  Real omega_m(unit="rad/s");
  Real E(unit="V") "Back EMF Voltage";

equation
  // Electrical input based on u_control
  U = U_M * u_control;
  
  // Motor-side speed and back-EMF
  omega_m = i_M * omega;
  E = k_e * omega_m;
  
  //Quasistatic torque
  torque = eta_M * i_M * k_M / R_M * (U - E);
  
  annotation(
    experiment(StartTime = 0, StopTime = 5, Interval = 0.1)
  );
  
end Drive_QStat;