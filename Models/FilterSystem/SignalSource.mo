within FilterSystem;
model SignalSource
  Modelica.Blocks.Interfaces.RealOutput Uin(unit="V");
  Real A1(unit="V") = 60;
  Real A2(unit="V") = 5;
  Real f1(unit="Hz") = 0.159;
  Real f2(unit="Hz") = 7.96;
  Real s1(unit="V");
  Real s2(unit="V");
equation
  s1 = (A2 * sin((((2.0 * 3.141592653589793) * f1) * time)));
  s2 = (A1 * sin((((2.0 * 3.141592653589793) * f2) * time)));
end SignalSource;