within ControlledPendulum.Examples.NoContact;

model Example_AdvancedDrive
  // Type definitions
  type RealOutput = Modelica.Blocks.Interfaces.RealOutput;
  
  // Components
  Trajectories.SineAngleSetPoint       set_point;
  Sensors.AnglePotentiometerADC        angle_sensor(nBits=12);
  Sensors.AnglePotentiometerADCDecoder angle_decoder(nBits=12);
  Controllers.PIDContinuous            pid(Kd=0.05, Ki=5, Kp=5);
  Actuators.DriveAdvanced              drive;
  Plants.Pendulum                      pendulum;

  // FMUCompoent observables
  RealOutput theta_ref(unit="rad") "Reference angle from set point";
  RealOutput theta_meas(unit="rad") "Measured angle from sensor";
  RealOutput theta(unit="rad") "Measured angle from pendulum";
  RealOutput omega(unit="rad/s") "Measured angle from pendulum"; 
  RealOutput alpha(unit="rad/s2") "Measured angle from pendulum";  
  RealOutput u_control(unit="1") "Control input from PID";
  RealOutput tau(unit="N.m") "Torque from drive";

equation
  // Connections
  connect(set_point.theta_ref, pid.theta_ref);
  connect(pendulum.theta, angle_sensor.theta);
  connect(angle_sensor.v_out, angle_decoder.v_in);
  connect(angle_decoder.theta, pid.theta_meas);
  connect(pid.u, drive.u_control);
  
  // Connect drive and Pendulum
  connect(drive.torque, pendulum.tau);
  connect(pendulum.theta, drive.phi);
  connect(pendulum.omega, drive.omega);
  connect(pendulum.alpha, drive.alpha);
  
  pid.resetI = false; // No contact - reset not required

  // Observables
  theta_ref = set_point.theta_ref;
  theta_meas = angle_decoder.theta;
  theta = pendulum.theta;
  omega = pendulum.omega;
  alpha = pendulum.alpha;
  u_control = pid.u;
  tau = drive.torque;
  
  annotation(
    experiment(StartTime = 0, StopTime = 10, Interval = 0.001)
  );

end Example_AdvancedDrive;