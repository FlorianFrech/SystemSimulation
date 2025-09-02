within ControlledPendulum;

model DemoModel
  /* 
  A model of a controlled pendulum system consisting of:
   - Reference trajectory generator
   - Sensors for reference and state
   - PID controller
   - Drive system
   - Pendulum dynamics
  */
  import SI = Modelica.Units.SI;

  // Components
  ReferenceTrajectory reference;
  
  Sensor              sensor_ref;
  Sensor              sensor_state;
  
  PID_Cont            pid;
  
  Drive               drive;
  
  Pendulum            pendulum;

equation
  // Connect reference and pendulum to sensors
  connect(reference.q_ref, sensor_ref.q);
  connect(pendulum.q_state, sensor_state.q);
  
  //connect(sensor_ref.U_q, pid_sensors.reference);
  connect(sensor_ref.U_q, pid.ref);
  connect(sensor_state.U_q, pid.y);
  
  // Connect PID output u_control to drive
  connect(pid.u, drive.u_control);
  
  // Connect drive and Pendulum
  connect(drive.torque, pendulum.torque);
  connect(drive.omega, pendulum.omega_state);
  
  annotation(
    experiment(StartTime = 0, StopTime = 20, Interval = 0.001)
  );

end DemoModel;