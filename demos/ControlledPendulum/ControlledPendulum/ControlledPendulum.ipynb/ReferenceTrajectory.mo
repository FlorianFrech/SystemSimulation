within ControlledPendulum;

model ReferenceTrajectory
  import Modelica.Constants.pi;  
  Modelica.Blocks.Interfaces.RealOutput ref(unit="rad");
equation
  ref = -pi/2 + pi/9 * cos(time);
end ReferenceTrajectory;