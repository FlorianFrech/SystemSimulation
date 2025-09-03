within Tests;

model Test_Sensor
  // Imports
  import Modelica.Constants.pi;

  // Instantiate submodels
  ControlledPendulum.Reference ref(
                                mean=0,
                                amplitude=pi/4,
                                frequency=1);
  
  ControlledPendulum.AngleEncoder sensor(
                                     q_min=ref.mean - ref.amplitude,
                                     q_max=ref.mean + ref.amplitude,
                                     nBits=6);

equation
  connect(ref.q_ref, sensor.q);
  annotation(
    experiment(StartTime = 0, StopTime = 1, Interval = 0.002)
    );
end Test_Sensor;