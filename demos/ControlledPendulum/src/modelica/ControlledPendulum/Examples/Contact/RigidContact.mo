within ControlledPendulum.Examples.Contact;

model RigidContact
  // Type definitions
  type RealOutput = Modelica.Blocks.Interfaces.RealOutput;
  
  // Parameters
  parameter Boolean useReset(start=false, fixed=false);
  
  // Components
  Trajectories.SineAngleSetPoint       set_point;
  Sensors.AnglePotentiometerADC        angle_sensor;
  Sensors.AnglePotentiometerADCDecoder angle_decoder;
  Controllers.PIDContinuous            pid;
  Actuators.DriveDynamic               drive;
  Plants.PendulumWithDiscreteWall      pendulum;
  
  // FMUCompoent observables
  RealOutput theta_ref(unit="rad") "Reference angle from set point";
  RealOutput theta_meas(unit="rad") "Decoded angle from decoder";
  RealOutput theta(unit="rad") "Measured angle from pendulum";
  RealOutput omega(unit="rad/s") "Measured angle from pendulum"; 
  RealOutput alpha(unit="rad/s2") "Measured angle from pendulum";  
  RealOutput u_control(unit="1") "Control input from PID";
  RealOutput tau(unit="N.m") "Torque from drive";

protected
  discrete Boolean contact(start=false, fixed=false) "Current contact state";
  discrete Boolean contactRisingEdge(start=false, fixed=false) "Rising edge detector for contact";

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
 
  // Observables
  theta_ref = set_point.theta_ref;
  theta_meas = angle_decoder.theta;
  theta = pendulum.theta;
  omega = pendulum.omega;
  alpha = pendulum.alpha;
  u_control = pid.u;
  tau = drive.torque; 
  
  annotation(
    experiment(StartTime = 0, StopTime = 5, Interval = 0.001)
  );

end RigidContact;