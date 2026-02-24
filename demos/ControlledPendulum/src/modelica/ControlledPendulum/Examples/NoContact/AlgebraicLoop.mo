within ControlledPendulum.Examples.NoContact;

model AlgebraicLoop
  // Type definitions
  type RealOutput = Modelica.Blocks.Interfaces.RealOutput;
  
  // Components
  Trajectories.SetPoint     set_point;
  Sensors.AngleSensor       angle_sensor;
  Sensors.AngleDecoder      angle_decoder;
  Controllers.PIDController pid;
  Actuators.DriveAdvanced   drive;
  Plants.Pendulum           pendulum;

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
  
  // Observables
  theta_ref = set_point.theta_ref;
  theta_meas = angle_decoder.theta;
  theta = pendulum.theta;
  omega = pendulum.omega;
  alpha = pendulum.alpha;
  u_control = pid.u;
  tau = drive.torque;
  
  annotation(
    experiment(StartTime = 0, StopTime = 2, Interval = 0.001)
  );

end AlgebraicLoop;