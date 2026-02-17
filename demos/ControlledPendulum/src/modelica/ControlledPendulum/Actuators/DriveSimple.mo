within ControlledPendulum.Actuators;

model DriveSimple  
  // Imports
  import Modelica.Constants.pi;
  
  // Parameters (datasheet-facing)
  parameter Real V_supply(unit="V") = 16 "Available DC supply voltage";
  parameter Real V_rated(unit="V") = 48 "Rated voltage (datasheet)";
  parameter Real n_0(unit="1/min") = 12916 "No-load speed at V_rated (datasheet)";
  parameter Real R_arm(unit="Ohm") = 0.151 "Armature resistance";
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
  Real U(unit="V");
  Real omega_m(unit="rad/s");
  Real E(unit="V") "Back EMF Voltage";
  Real I(unit="A") "Quasi-static armature current";

equation
  // Electrical input based on u_control
  U = V_supply * u_control;
  
  // Motor-side speed and back-EMF
  omega_m = gearRatio * omega;
  E = k_e * omega_m;
  
  // Quasi-static current with limit
  I = min(max((U - E) / R_arm, -I_max), I_max);

  // Quasi-static torque with viscous loss
  torque = eta * gearRatio * k_t * I - b_viscous * omega;
  
  annotation(
    experiment(StartTime = 0, StopTime = 5, Interval = 0.1)
  );
  
end DriveSimple;
