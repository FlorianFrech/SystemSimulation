within ControlledPendulum;

model Drive_Coupled 
  // Imports
  import Modelica.Constants.pi;
  import Modelica.Mechanics.Rotational.Components;
  
  // Electrical Drive Parameters
  parameter Real U_M(unit="V") = 16;
  parameter Real U_rated(unit="V") = 48;
  parameter Real R_M(unit="Ohm") = 0.151;
  parameter Real L_M(unit="H") = 121e-6;
  parameter Real k_M(unit="N.m/A") = 0.03;
  parameter Real n_0(unit="1/min") = 12916;  
  parameter Real i_M = 60;
  parameter Real eta_M = 0.85;
  
  // Mechanical Parameters
  parameter Real J1(unit="kg.m2") = 0.05 "Motor-side inertia";
  parameter Real J2(unit="kg.m2") = 0.10 "Interface inertia";
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
  parameter Real k_n(unit="(1/min)/V") = n_0/U_rated;
  parameter Real k_e(unit="V.s/rad") = 60 / (2 * pi * k_n);
  Real I(unit="A");
  Real U(unit="V");
  Real omega_m(unit="rad/s");
  Real E(unit="V") "Back EMF Voltage";
  
  // Rotational components
 Modelica.Mechanics.Rotational.Components.Inertia      inertia1(J=J1);
 Modelica.Mechanics.Rotational.Components.Inertia      inertia2(J=J2);
 Modelica.Mechanics.Rotational.Components.SpringDamper springDamper(c=c, d=d);
 Modelica.Mechanics.Rotational.Sources.Torque          motorTorque;
 Modelica.Mechanics.Rotational.Sensors.TorqueSensor    torqueSensor;
 Modelica.Mechanics.Rotational.Sources.Move            prescribedMotion;

initial equation
  der(I) = 0;

equation
  // Electrical input based on u_control
  U = U_M * u_control;
  
  // Motor-side speed and back-EMF
  omega_m = i_M * omega;
  E = k_e * omega_m;
  
  // Current dynamics and torque mapping
  der(I) = (U - R_M * I - E) / L_M;
  motorTorque.tau = eta_M * i_M * k_M * I;
  
  // Connect rotational drive train
  connect(motorTorque.flange, inertia1.flange_a);
  connect(inertia1.flange_b, springDamper.flange_a);
  connect(springDamper.flange_b, inertia2.flange_a);
  connect(inertia2.flange_b, torqueSensor.flange_a);
  connect(torqueSensor.flange_b, prescribedMotion.flange);
  
  // Prescribed Motion from Pendulum
  connect(phi, prescribedMotion.u[1]);
  connect(omega, prescribedMotion.u[2]);
  connect(alpha, prescribedMotion.u[3]);
  
  // Output reaction torque at interface
  torque = torqueSensor.tau
  
  annotation(
    experiment(StartTime = 0, StopTime = 5, Interval = 0.1)
  );
  
end Drive_Coupled;