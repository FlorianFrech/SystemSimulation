within FilterSystem;
model LowPassFilter
  Modelica.Blocks.Interfaces.RealInput U_in(unit="V");
  Modelica.Blocks.Interfaces.RealOutput U_out(unit="V");
  parameter Real R(unit="Ohm") = 1000;
<<<<<<< HEAD
  parameter Real C(unit="F") = 0.001;
=======
  parameter Real C(unit="F") = 1e-06;
>>>>>>> 8fed97d8a9bd031674551c9b94bb385c5bfcb165
  parameter Real U0(unit="V") = 0;
initial equation
  U_out = U0;
equation
  der(U_out) = ((U_in - U_out) / (R * C));
end LowPassFilter;