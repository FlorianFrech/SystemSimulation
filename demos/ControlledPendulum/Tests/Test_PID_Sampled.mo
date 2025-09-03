within Tests;

model Test_PID_Sampled
  // Test Component
  ControlledPendulum.PID_Sampled controller(
    Kp=1, Ki=0.5, Kd=0.1, dt=0.01, uMin=-1, uMax=1, derivativeOnMeasurement=true
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
  connect(stateSrc.y, controller.measurement);
  
  annotation(
    experiment(StartTime = 0, StopTime = 3, Interval = 0.01)
  );
end Test_PID_Sampled;