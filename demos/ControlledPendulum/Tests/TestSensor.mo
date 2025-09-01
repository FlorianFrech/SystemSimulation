within Tests;

model TestSensor
  // Instantiate submodels
  ControlledPendulum.ReferenceTrajectory ref;
  ControlledPendulum.Sensor sensor(nBits=8);
equation
  connect(ref.q_ref, sensor.q);
  annotation(
    experiment(StartTime = 0, StopTime = 10, Interval = 0.002)
    );
end TestSensor;