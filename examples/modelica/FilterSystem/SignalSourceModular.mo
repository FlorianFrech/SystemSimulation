within FilterSystem;

model SignalSourceModular "Composite sine wave signal generator using standard blocks"
  import Modelica.Blocks.Sources;
  import Modelica.Blocks.Math;
  
  // Parameters
  parameter Real A1(unit="V") = 60 "Amplitude of first sine wave";
  parameter Real A2(unit="V") = 5 "Amplitude of second sine wave";
  parameter Real f1(unit="Hz") = 0.159 "Frequency of first sine wave";
  parameter Real f2(unit="Hz") = 7.96 "Frequency of second sine wave";
  
  // Output connector
  Modelica.Blocks.Interfaces.RealOutput Uin(unit="V") "Output voltage signal";
  
  // Internal components
  Sources.Sine sineWave1(
    amplitude=A1,
    freqHz=f1,
    phase=0,
    offset=0,
    startTime=0) "First sine wave generator";
    
  Sources.Sine sineWave2(
    amplitude=A2,
    freqHz=f2,
    phase=0,
    offset=0,
    startTime=0) "Second sine wave generator";
    
  Math.Add add "Adder for combining the two sine waves";
  
equation
  // Connect the sine wave generators to the adder
  connect(sineWave1.y, add.u1);
  connect(sineWave2.y, add.u2);
  
  // Connect the adder output to the model output
  connect(add.y, Uin);

end SignalSourceModular;
