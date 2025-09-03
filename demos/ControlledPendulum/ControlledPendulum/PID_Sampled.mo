within ControlledPendulum;

model PID_Sampled
  /*
  The model implements a discrete PID controller that samples a reference and a state value
  at discrete time points defined by dt.
  Controller behavior is governed by Kp, Ki, and Kd.
  The output control signal u_control is limited to uMin and uMax values.
  */
  
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
  Modelica.Blocks.Interfaces.RealOutput u_control(start=0);

protected
  // Make inputs appear in the continuous equations
  Real ref_cont;
  Real state_cont;

  // Internal discrete output
  discrete Real u(start=0, fixed=true);

  // Discrete internal histories
  discrete Real e_km1(start=0, fixed=true);
  discrete Real e_km2(start=0, fixed=true);
  discrete Real u_km1(start=0, fixed=true);

  // Scratch variables for algorithm
  Real e_k(start=0);
  Real a0(start=0), a1(start=0), a2(start=0);
  Real u_unsat(start=0);

equation
  // Continuous aliases force the inputs to be “continuous variability” in the FMU
  ref_cont   = reference;
  state_cont = state;

  u_control = u;

algorithm
  when sample(0, dt) then
    e_k := ref_cont - state_cont;

    // Incremental (velocity) form coefficients
    a0 := (Kp + Kd/dt);
    a1 := (Ki*dt - 2*Kd/dt - Kp);
    a2 := (Kd/dt);

    u_unsat := u_km1 + a0*e_k + a1*e_km1 + a2*e_km2;

    u := min(uMax, max(uMin, u_unsat));

    u_km1 := u;
    e_km2 := e_km1;
    e_km1 := e_k;
  end when;

end PID_Sampled;