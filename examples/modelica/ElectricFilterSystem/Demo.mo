within ElectricFilterSystem;

model Demo
 Sources.VoltageSource SRC;
 
 Modelica.Electrical.Analog.Basic.Resistor R1(R=1000);
 Modelica.Electrical.Analog.Basic.Resistor R2(R=1000);
 Modelica.Electrical.Analog.Basic.Resistor R3(R=1000);
 
 Modelica.Electrical.Analog.Basic.Capacitor C1(C=1e-6);
 Modelica.Electrical.Analog.Basic.Capacitor C2(C=1e-6);
 Modelica.Electrical.Analog.Basic.Capacitor C3(C=1e-6);
 
 Modelica.Electrical.Analog.Basic.Inductor L1(L=1e-2);
 
 Modelica.Electrical.Analog.Basic.Ground g;

equation
  connect(SRC.p, R1.p);
  connect(SRC.n, g.p);
  
  connect(R1.n, C1.p);
  connect(C1.n, g.p);
  
  connect(C1.p, R2.p);
  connect(R2.n, C2.p);
  connect(C2.n, g.p);
  
  connect(C2.p, R3.p);
  connect(C2.p, C3.p);
  connect(C2.p, L1.p);
  
  connect(R3.n, g.p);
  connect(C3.n, g.p);
  connect(L1.n, g.p);  
  
end Demo;