within Tests;

model Test_PID_Continuous
  // Test Component
  ControlledPendulum.PID_Continuous controller(uMin=-1, uMax=1);
  
  // Stimulus
  Modelica.Blocks.Sources.Step refStep(height=1, startTime=0.5);
  Modelica.Blocks.Sources.Constant stateSrc(k=0);
  
  // Outputs for plotting
  Modelica.Blocks.Interfaces.RealOutput ref = refStep.y;
  Modelica.Blocks.Interfaces.RealOutput state = stateSrc.y;
  Modelica.Blocks.Interfaces.RealOutput u = controller.u;
 
equation
  connect(refStep.y, controller.ref);
  connect(stateSrc.y, controller.y);
  
  annotation(
    experiment(StartTime = 0, StopTime = 3, Interval = 0.01)
  );
end Test_PID_Continuous;