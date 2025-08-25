within ControlledPendulum;

model DemoModel
  import SI = Modelica.Units.SI;

  // Components
  ReferenceTrajectory reference;
  Sensor              sensor;
  PIDController       pid(Kp=100, Ki=500, Kd=30, dt=0.01, uMin=-1, uMax=1);
  Drive               drive;
  Pendulum            plant;

  // Measured angle reconstructed from ADC output U_q (rad)
protected 
  SI.Angle q_meas;

equation
  connect(plant.q_out, sensor.q);
  q_meas = sensor.alpha_max * (0.8 - sensor.U_q/sensor.U_0_pot)
           - sensor.alpha_max/2 + (sensor.q_min + sensor.q_max)/2;

  // --- PID reference and feedback (angles in rad) ---
  connect(reference.ref, pid.reference);
  pid.state = q_meas;

  // --- Drive command and plant coupling ---
  connect(pid.u_control, drive.u);
  connect(plant.omega_out, drive.omega_m);
  connect(drive.M, plant.tau);

end DemoModel;
