within ControlledPendulum.Actuators;

model DriveDynamic
  /*
  Model implements an electric drive which takes a control signal u_control and
  an angular velocity of the shaft as input and computes the output torque at the shaft.
  */
  
  // Imports
  import Modelica.Constants.pi;
  
  // Parameters (datasheet-facing)
  parameter Real V_supply(unit="V") = 16 "Available DC supply voltage";
  parameter Real V_rated(unit="V") = 48 "Rated voltage (datasheet)";
  parameter Real n_0(unit="1/min") = 12916 "No-load speed at V_rated (datasheet)";
  parameter Real R_arm(unit="Ohm") = 0.151 "Armature resistance";
  parameter Real L_arm(unit="H") = 121e-6 "Armature inductance";
  parameter Real k_t(unit="N.m/A") = 0.03 "Torque constant";
  parameter Real gearRatio = 60 "Gear ratio (motor to output)";
  parameter Real eta = 0.85 "Gear efficiency";

  // Limits and losses
  parameter Real I_max(unit="A") = 10 "Current limit (driver/thermal)";
  parameter Real b_viscous(unit="N.m.s/rad") = 0.01 "Output viscous friction";

  // Derived Parameter
  parameter Real k_n(unit="(1/min)/V") = n_0/V_rated;
  parameter Real k_e(unit="V.s/rad") = 60 / (2 * pi * k_n);
  
  // Inputs
  Modelica.Blocks.Interfaces.RealInput u_control "Normalized control input [-1, 1]";
  Modelica.Blocks.Interfaces.RealInput omega(unit="rad/s");
  
  // Outputs
  Modelica.Blocks.Interfaces.RealOutput torque(unit="N.m", start=0);

  // Internal Variables
  Real I(unit="A", start=0);
  Real U(unit="V");
  Real omega_m(unit="rad/s");
  Real E(unit="V") "Back EMF Voltage";
  Real I_lim(unit="A") "Limited armature current";

equation
  // Electrical input based on u_control
  U = V_supply * u_control;
  
  // Motor-side speed and back-EMF
  omega_m = gearRatio * omega;
  E = k_e * omega_m;
  
  // Current dynamics and torque mapping
  der(I) = (U - R_arm * I - E) / L_arm;
  I_lim = min(max(I, -I_max), I_max);
  torque = eta * gearRatio * k_t * I_lim - b_viscous * omega;
  
  annotation(
    experiment(StartTime = 0, StopTime = 5, Interval = 0.1)
  );
  
end DriveDynamic;
