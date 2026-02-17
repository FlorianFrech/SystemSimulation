within ControlledPendulum.Controllers;

model PID_Sampled
  // Parameters (continuous, event-free PID)
  parameter Real Kp = 75 "Proportional gain";
  parameter Real Ki = 0.75 "Integral gain [1/s]";
  parameter Real Kd = 2 "Derivative gain [s]";
  parameter Real dt(unit="s") = 0.01 "Nominal step (used as derivative filter time)";
  parameter Real Tdf(unit="s") = max(dt, 1e-6) "Derivative filter time constant";
  parameter Real uMin = -1;
  parameter Real uMax =  1;
  parameter Boolean derivativeOnMeasurement = true;

  // Inputs
  Modelica.Blocks.Interfaces.RealInput theta_ref(unit="rad");
  Modelica.Blocks.Interfaces.RealInput theta_meas(unit="rad");

  // Outputs
  Modelica.Blocks.Interfaces.RealOutput u(start=0);
  Modelica.Blocks.Interfaces.RealOutput error(start=0);
  Modelica.Blocks.Interfaces.BooleanOutput saturated(start=false);

protected
  // Continuous states (no events)
  Real xi(start=0, fixed=true) "Integrator state";
  Real x_de(start=0, fixed=true) "Derivative filter state on error";
  Real x_dy(start=0, fixed=true) "Derivative filter state on measurement";

  // Internals
  Real e;
  Real P_term, I_term, D_term, u_unsat;
  Real d_err, d_meas;

equation
  // Error
  e = theta_ref - theta_meas;

  // Integrator and derivative filters (event-free ODEs)
  der(xi)   = e;
  der(x_de) = (e - x_de)/Tdf;
  der(x_dy) = (theta_meas - x_dy)/Tdf;

  // Filtered derivatives
  d_err  = (e - x_de)/Tdf;
  d_meas = (theta_meas - x_dy)/Tdf;

  // PID terms
  P_term = Kp * e;
  I_term = Ki * xi;
  D_term = if derivativeOnMeasurement then -Kd * d_meas else Kd * d_err;

  // Output and flags without generating events
  u_unsat   = P_term + I_term + D_term;
  u = noEvent(min(uMax, max(uMin, u_unsat)));
  error     = e;
  saturated = noEvent((u_unsat <= uMin) or (u_unsat >= uMax));
end PID_Sampled;
