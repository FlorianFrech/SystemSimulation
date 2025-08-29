within ControlledPendulum;

model DemoModel
  import SI = Modelica.Units.SI;

  // Components
  ReferenceTrajectory reference;
  
  Sensor              sensor_ref;
  Sensor              sensor_state;
  
  //PIDController       pid_sensors(Kp=2, Ki=50, Kd=0.5, dt=0.01);
  PID_Cont            pid;
  
  Drive               drive;
  
  Pendulum            pendulum;

equation
  // Connect reference and pendulum to sensors
  connect(reference.q_ref, sensor_ref.q);
  connect(pendulum.q_state, sensor_state.q);
  
  //connect(sensor_ref.U_q, pid_sensors.reference);
  //connect(sensor_state.U_q, pid_sensors.state);
  connect(sensor_ref.U_q, pid.ref);
  connect(sensor_state.U_q, pid.y);
  
  // Connect PID output u_control to drive
  //connect(pid_sensors.u_control, drive.u_control);
  connect(pid.u, drive.u_control);
  
  // Connect drive and Pendulum
  connect(drive.torque, pendulum.torque);
  connect(drive.omega, pendulum.omega_state);
  
  annotation(
    experiment(StartTime = 0, StopTime = 20, Interval = 0.001)
  );

end DemoModel;