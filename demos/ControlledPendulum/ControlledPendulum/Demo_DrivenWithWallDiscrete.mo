within ControlledPendulum;

model Demo_DrivenWithWallDiscrete
  /* 
  A model of a controlled pendulum system consisting of:
   - Reference trajectory generator
   - Sensors for reference and state
   - PID controller
   - Drive system
   - Pendulum dynamics
  */

  // Components
  Reference           reference(frequency=0.25);
  
  AngleEncoder        sensor_ref( q_min = -reference.amplitude,
                                  q_max =  reference.amplitude);
  
  AngleEncoder        sensor_state( q_min = -reference.amplitude,
                                    q_max =  reference.amplitude);
  
  PID_Continuous      pid;
  
  Drive               drive;
  
  PendulumWithWallDiscrete            pendulum;

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
    experiment(StartTime = 0, StopTime = 10, Interval = 0.001)
  );

end Demo_DrivenWithWallDiscrete;