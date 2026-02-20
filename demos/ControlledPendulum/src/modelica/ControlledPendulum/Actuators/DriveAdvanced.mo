within ControlledPendulum.Actuators;

model DriveAdvanced 
  // Imports
  import Modelica.Constants.pi;
  import Modelica.Mechanics.Rotational.Components;
  
  // Electrical Drive Parameters (datasheet-facing)
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
  
  // Mechanical Parameters
  parameter Real J_motor(unit="kg.m2") = 5.6e-6 "Motor-side inertia";
  parameter Real J_interface(unit="kg.m2") = 0.10 "Interface inertia";
  parameter Real c(unit="N.m/rad") = 1e5 "Spring constant";
  parameter Real d(unit="N.m.s/rad") = 100 "Damping constant";
  
  // Control input from PID
  Modelica.Blocks.Interfaces.RealInput u_control;
  
  // Prescribed joint motion from Pendulum
  Modelica.Blocks.Interfaces.RealInput phi(unit="rad");
  Modelica.Blocks.Interfaces.RealInput omega(unit="rad/s");
  Modelica.Blocks.Interfaces.RealInput alpha(unit="rad/s2");
  
  // Output reaction torque
  Modelica.Blocks.Interfaces.RealOutput torque(unit="N.m");

  // Internal electrical parameters and variables
  parameter Real k_n(unit="(1/min)/V") = n_0/V_rated;
  parameter Real k_e(unit="V.s/rad") = 60 / (2 * pi * k_n);
  Real I(unit="A", start=0);
  Real U(unit="V");
  Real omega_m(unit="rad/s");
  Real E(unit="V") "Back EMF Voltage";
  Real dI(unit="A/s") "dI/dt internal for current limit";

  
  // Rotational components
  Modelica.Mechanics.Rotational.Components.Inertia      iniertia_motor(J=J_motor);
  Modelica.Mechanics.Rotational.Components.Inertia      iniertia_interface(J=J_interface);
  Modelica.Mechanics.Rotational.Components.SpringDamper springDamper(c=c, d=d);
  Modelica.Mechanics.Rotational.Components.IdealGear    gear(ratio=gearRatio);
  Modelica.Mechanics.Rotational.Components.Damper       viscousDamper(d=b_viscous);
  Modelica.Mechanics.Rotational.Components.Fixed        fixed;
  Modelica.Mechanics.Rotational.Sources.Torque          motorTorque;
  Modelica.Mechanics.Rotational.Sensors.TorqueSensor    torqueSensor;
  Modelica.Mechanics.Rotational.Sources.Move            prescribedMotion;

equation
  // Electrical input based on u_control
  U = V_supply * u_control;
  
  // Motor-side speed and back-EMF
  omega_m = iniertia_motor.w;
  E = k_e * omega_m;
  
  // Current dynamics and torque mapping
  dI = (U - R_arm * I - E) / L_arm;
  der(I) = if noEvent(I > I_max and dI > 0) then 0
           elseif noEvent(I <= -I_max and dI < 0) then 0
           else dI;
  motorTorque.tau = eta * k_t * I;
  
  // Connect rotational drive train
  connect(motorTorque.flange, iniertia_motor.flange_a);
  connect(iniertia_motor.flange_b, gear.flange_a);
  connect(gear.flange_b, springDamper.flange_a);
  connect(springDamper.flange_b, iniertia_interface.flange_a);
  connect(iniertia_interface.flange_b, torqueSensor.flange_a);
  connect(torqueSensor.flange_b, prescribedMotion.flange);
  connect(iniertia_interface.flange_b, viscousDamper.flange_a);
  connect(viscousDamper.flange_b, fixed.flange);
  
  // Prescribed Motion from Pendulum
  connect(phi, prescribedMotion.u[1]);
  connect(omega, prescribedMotion.u[2]);
  connect(alpha, prescribedMotion.u[3]);
  
  // Output reaction torque at interface
  torque = torqueSensor.tau;
  
  annotation(
    experiment(StartTime = 0, StopTime = 5, Interval = 0.1)
  );
  
end DriveAdvanced;
