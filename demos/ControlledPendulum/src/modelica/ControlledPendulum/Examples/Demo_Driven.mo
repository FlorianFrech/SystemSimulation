within ControlledPendulum.Examples;

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
  Trajectories.SineAngleSetPoint reference;
  
  Sensors.AnglePotentiometerADC sensor_state( theta_min = -reference.amplitude,
                                              theta_max =  reference.amplitude);
  Sensors.AnglePotentiometerADCDecoder sensor_decode(
    nBits = sensor_state.nBits,
    theta_min = sensor_state.theta_min,
    theta_max = sensor_state.theta_max,
    v_pot = sensor_state.v_pot,
    v_adc = sensor_state.v_adc,
    r_top = sensor_state.r_top,
    r_bottom = sensor_state.r_bottom,
    pot_range = sensor_state.pot_range);
  
  Controllers.PIDContinuous       pid(Kp=30, Ki=300, Kd=6, Td=0.2, Nd=10);
  
  Actuators.Drive               drive;
  
  Plants.Pendulum            pendulum;

equation
  // Connect reference and pendulum to controller and sensor
  connect(reference.theta_ref, pid.theta_ref);
  connect(pendulum.theta, sensor_state.theta);
  
  connect(sensor_state.v_out, sensor_decode.v_in);
  connect(sensor_decode.theta, pid.theta_meas);
  
  // Connect PID output u_control to drive
  connect(pid.u, drive.u_control);
  
  // Connect drive and Pendulum
  connect(drive.torque, pendulum.tau);
  connect(drive.omega, pendulum.omega);
  
  pid.resetI = false;
  
  annotation(
    experiment(StartTime = 0, StopTime = 10, Interval = 0.001)
  );

end Demo_Driven;
