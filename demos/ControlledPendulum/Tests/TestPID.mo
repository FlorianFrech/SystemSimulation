within Tests;

model TestPID
  // Test Component
  ControlledPendulum.PIDController controller(
    Kp=2, Ki=1, Kd=0.5, dt=0.01, uMin=-1, uMax=1
  );
  
  // Stimulus
  Modelica.Blocks.Sources.Step refStep(height=1, startTime=0.5);
  Modelica.Blocks.Sources.Constant stateSrc(k=0);
  
  // Outputs for plotting
  Modelica.Blocks.Interfaces.RealOutput ref = refStep.y;
  Modelica.Blocks.Interfaces.RealOutput state = stateSrc.y;
  Modelica.Blocks.Interfaces.RealOutput u = controller.u_control;
 
equation
  connect(refStep.y, controller.reference);
  connect(stateSrc.y, controller.state);
  
  annotation(
    experiment(StartTime = 0, StopTime = 3, Interval = 0.01)
  );
end TestPID;