within ControlledPendulum;

model Demo_Driven_Coupled
  /* 
  A model of a controlled pendulum system consisting of:
   - Reference trajectory generator
   - Sensors for reference and state
   - PID controller
   - Drive system
   - Pendulum dynamics
  */

  // Components
  Reference           reference;
  
  AngleEncoder        sensor_ref( q_min = -reference.amplitude,
                                  q_max =  reference.amplitude);
  
  AngleEncoder        sensor_state( q_min = -reference.amplitude,
                                    q_max =  reference.amplitude);
  
  PID_Continuous        pid;
  
  Drive_Coupled       drive;
  
  Pendulum            pendulum;

equation
  // Connect reference and pendulum to sensors
  connect(reference.q_ref, sensor_ref.q);
  connect(pendulum.q, sensor_state.q);
  
  //connect(sensor_ref.U_q, pid_sensors.reference);
  connect(sensor_ref.U_q, pid.ref);
  connect(sensor_state.U_q, pid.y);
  
  // Connect PID output u_control to drive
  connect(pid.u, drive.u_control);
  
  // Connect drive and Pendulum
  connect(drive.torque, pendulum.torque);
  connect(pendulum.q, drive.phi);
  connect(pendulum.omega, drive.omega);
  connect(pendulum.alpha, drive.alpha);
  
  pid.resetI = false;
    
  annotation(
    experiment(StartTime = 0, StopTime = 10, Interval = 0.01)
  );

end Demo_Driven_Coupled;