within Tests;

model Test_Pendulum
  
  ControlledPendulum.Pendulum pendulum;
  
  Modelica.Blocks.Sources.Sine torqueSrc(
    amplitude = 1,
    f = 1
    );
  
equation
  
  connect(torqueSrc.y, pendulum.torque);
  
  annotation(
    experiment(StartTime = 0, StopTime = 5, Interval = 0.01)
  );

end Test_Pendulum;