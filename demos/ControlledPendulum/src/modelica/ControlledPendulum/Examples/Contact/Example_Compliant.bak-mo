within ControlledPendulum.Examples.Contact;

model Example_Compliant
  // Parameters
  parameter Boolean useReset(fixed=false, start=true);
  
  // Components
  Trajectories.SineAngleSetPoint       set_point;
  Sensors.AnglePotentiometerADC        angle_sensor(nBits=12);
  Sensors.AnglePotentiometerADCDecoder angle_decoder(nBits=12);
  Controllers.PIDContinuous            pid(Kd=0.05, Ki=5, Kp=5);
  Actuators.DriveDynamic               drive;
  Plants.PendulumWithCompliantWall     pendulum;

protected
  discrete Boolean contact(start=false) "Current contact state";
  discrete Boolean contactRisingEdge(start=false) "Rising edge detector for contact";

equation
  // Connections
  connect(set_point.theta_ref, pid.theta_ref);
  connect(pendulum.theta, angle_sensor.theta);
  connect(angle_sensor.v_out, angle_decoder.v_in);
  connect(angle_decoder.theta, pid.theta_meas);
  connect(pid.u, drive.u_control);
  connect(drive.torque, pendulum.tau);
  connect(drive.omega, pendulum.omega);
  
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
    experiment(StartTime = 0, StopTime = 10, Interval = 0.001)
  );

end Example_Compliant;