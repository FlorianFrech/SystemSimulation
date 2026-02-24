within ControlledPendulum.Examples.NoContact;

model Baseline
  // Type definitions
  type RealOutput = Modelica.Blocks.Interfaces.RealOutput;

  // Components
  Trajectories.SetPoint     set_point;
  Controllers.PIDController pid;
  Actuators.DriveDynamic    drive;
  Plants.Pendulum           pendulum;

  // FMUCompoent observables
  RealOutput theta_ref(unit="rad") "Reference angle from set point";
  RealOutput theta(unit="rad") "Measured angle from pendulum";
  RealOutput omega(unit="rad/s") "Measured angle from pendulum"; 
  RealOutput alpha(unit="rad/s2") "Measured angle from pendulum";  
  RealOutput u_control(unit="1") "Control input from PID";
  RealOutput tau(unit="N.m") "Torque from drive";

equation
  // Connections
  connect(set_point.theta_ref, pid.theta_ref);
  connect(pendulum.theta, pid.theta_meas);
  connect(pid.u, drive.u_control);
  connect(drive.torque, pendulum.tau);
  connect(drive.omega, pendulum.omega);
    
  // Observables
  theta_ref = set_point.theta_ref;
  theta = pendulum.theta;
  omega = pendulum.omega;
  alpha = pendulum.alpha;
  u_control = pid.u;
  tau = drive.torque;  
  
  annotation(
    experiment(StartTime = 0, StopTime = 2, Interval = 0.001)
  );

end Baseline;