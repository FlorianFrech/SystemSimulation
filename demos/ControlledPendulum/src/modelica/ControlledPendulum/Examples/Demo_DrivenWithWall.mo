within ControlledPendulum.Examples;

model Demo_DrivenWithWall
  /* 
  A model of a controlled pendulum system with integrator reset on wall contact.
  */
  
  // Parameters
  parameter Boolean useReset(start=false, fixed=false);

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
  
  Controllers.PIDContinuous      pid(Kp=10, Ki=16.6667, Kd=0.5, Td=0.05, Nd=10);
  
  Actuators.Drive               drive;
  
  Plants.PendulumWithWall    pendulum;
 
protected
  discrete Boolean contact(start=false) "Current contact state";
  discrete Boolean contactRisingEdge(start=false) "Rising edge detector for contact";

equation
  // Sensors
  connect(reference.theta_ref, pid.theta_ref);
  connect(pendulum.theta, sensor_state.theta);
  
  connect(sensor_state.v_out, sensor_decode.v_in);
  connect(sensor_decode.theta, pid.theta_meas);
  
  // PID -> Drive
  connect(pid.u, drive.u_control);
  
  // Drive <-> Pendulum
  connect(drive.omega, pendulum.omega);
  connect(drive.torque, pendulum.tau);
  
  // Rising edge detection using when clause
  when pendulum.contact and not pre(contact) then
    contactRisingEdge = true;
    contact = true;
  elsewhen not pendulum.contact then
    contactRisingEdge = false;
    contact = false;
  end when;
  
  // Reset integrator on wall impact
  if useReset then
    pid.resetI = contactRisingEdge;
  else
    pid.resetI = false;
 end if;
  
  annotation(
    experiment(StartTime = 0, StopTime = 10, Interval = 0.01)
  );

end Demo_DrivenWithWall;
