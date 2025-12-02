within ControlledPendulum;

model Demo_Driven
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
  
  PID_Continuous       pid(k=10, Ti=0.01, Td=0.75, Nd=10);
  
  Drive               drive;
  
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
  connect(drive.omega, pendulum.omega);
  
  //pid.freezeI = false;
  
  annotation(
    experiment(StartTime = 0, StopTime = 10, Interval = 0.001)
  );

end Demo_Driven;