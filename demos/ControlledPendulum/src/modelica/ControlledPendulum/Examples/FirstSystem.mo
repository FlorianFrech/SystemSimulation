within ControlledPendulum.Examples;

model FirstSystem
  
  // Components
  Trajectories.SineAngleSetPoint reference;
  
  // old pid + old drive -> good control
  //Controllers.PID_Continuous pid(Nd=10, Td=0.2, Ti=0.1, k=30);
  //Actuators.Drive drive;
  
  // old pid + new drive
  Controllers.PID_Continuous pid(Nd=10, Td=0.2, Ti=0.1, k=30);
  Actuators.DriveDynamic drive;
  
  // new pid + old drive
  //Controllers.PIDContinuous pid;
  //Actuators.Drive drive;

  // new pid + new drive
  //Controllers.PIDContinuous pid;
  //Actuators.DriveDynamic drive;
  
  
  Plants.Pendulum pendulum;

equation
  // Connect reference and pendulum to controller and sensor
  connect(reference.theta_ref, pid.theta_ref);
  connect(pendulum.theta, pid.theta_meas);
  
  // Connect PID output u_control to drive
  connect(pid.u, drive.u_control);
  
  // Connect drive and Pendulum
  connect(drive.torque, pendulum.tau);
  connect(drive.omega, pendulum.omega);
  
  pid.resetI = false;
  
  annotation(
    experiment(StartTime = 0, StopTime = 10, Interval = 0.001)
  );

end FirstSystem;
