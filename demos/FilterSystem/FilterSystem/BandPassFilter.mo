within FilterSystem;
model BandPassFilter
  Modelica.Blocks.Interfaces.RealInput U_in(unit="V");
  Modelica.Blocks.Interfaces.RealOutput I(unit="A");
  Modelica.Blocks.Interfaces.RealOutput IL(unit="A");
  parameter Real R(unit="Ohm") = 100;
  parameter Real C(unit="F") = 1e-06;
  parameter Real L(unit="H") = 0.01;
  parameter Real IL0(unit="A") = 0;
  Real I_R(unit="A");
  Real I_C(unit="A");
initial equation
  IL = IL0;
equation
  I_R = (U_in / R);
  I_C = (C * der(U_in));
  der(IL) = (U_in / L);
  I = ((I_R + I_C) + IL);
end BandPassFilter;