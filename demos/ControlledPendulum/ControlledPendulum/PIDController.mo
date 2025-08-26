within ControlledPendulum;

model PIDController
  // Parameters
  parameter Real Kp = 100;
  parameter Real Ki = 500;
  parameter Real Kd = 30;
  parameter Real dt(unit="s") = 0.01;
  
  // Limits
  parameter Real uMin=-1;
  parameter Real uMax=1;
  
  // Inputs
  Modelica.Blocks.Interfaces.RealInput reference;
  Modelica.Blocks.Interfaces.RealInput state;
  
  // Output
  Modelica.Blocks.Interfaces.RealOutput u_control;
  
  protected
  Real e_km1(start=0);
  Real e_km2(start=0);
  Real u_km1(start=0);
  Real e_k;
  Real a0, a1, a2;
initial equation
  u_control = 0;
algorithm
  when sample(0, dt) then
    e_k := reference - state;

    // Incremental (velocity) form coefficients
    a0 := (Kp + Kd/dt);
    a1 := (Ki*dt - 2*Kd/dt - Kp);
    a2 := (Kd/dt);

    // Corrected recurrence (note e_km1 vs e_km2)
    u_control := u_km1 + a0*e_k + a1*e_km1 + a2*e_km2;

    // Apply saturation
    u_control :=  min(uMax, max(uMin, u_control));
    
    // Shift states
    u_km1 := u_control;
    e_km2 := e_km1;
    e_km1 := e_k;
  end when;

end PIDController;