within ControlledPendulum.Controllers;

model PID_Continuous
  // Parameters
  parameter Real k=10 "Controller gain";
  parameter Real Ti=0.05 "Integral time constant";
  parameter Real Td=0.6 "Derivative time constant";
  parameter Real Nd=10 "Derivative filter divisor";
  parameter Real uMin=-1, uMax=1 "Output limits";
  
  // Inputs
  Modelica.Blocks.Interfaces.RealInput  theta_ref(unit="rad") "Reference signal";
  Modelica.Blocks.Interfaces.RealInput  theta_meas(unit="rad") "Measured output";
  Modelica.Blocks.Interfaces.BooleanInput resetI(start=false) "Reset integrator on rising edge";

  // Outputs
  Modelica.Blocks.Interfaces.RealOutput u "Control signal";
  Modelica.Blocks.Interfaces.RealOutput I_out "Integrator output (for monitoring)";

  // Internal constants
  constant Real xi_start=0 "Integrator initial state";
  constant Real xd_start=0 "Derivative initial state";
  
  // Error calculation: e = ref - y
  Modelica.Blocks.Math.Add addErr(k1=1, k2=-1);
  
  // Proportional part
  Modelica.Blocks.Math.Gain P(k=1);
  
  // Integral part with reset capability
  Modelica.Blocks.Continuous.LimIntegrator I(
    k=1/Ti,
    outMax=1e10,
    outMin=-1e10,
    y_start=xi_start,
    initType=Modelica.Blocks.Types.Init.InitialState,
    use_reset=true);
  
  // Derivative part with first-order filter
  Modelica.Blocks.Continuous.Derivative D(
    k=Td,
    T=max(Td/Nd, 100*Modelica.Constants.eps), 
    x_start=xd_start,
    initType=Modelica.Blocks.Types.Init.InitialState);
  
  // PID sum: u_presat = k*(P + I + D)
  Modelica.Blocks.Math.Add3 sumPID;
  Modelica.Blocks.Math.Gain gainK(k=k);
 
  // Output saturation
  Modelica.Blocks.Nonlinear.Limiter lim(uMin=uMin, uMax=uMax);

equation
  // Error: e = ref - y
  connect(theta_ref, addErr.u1);
  connect(theta_meas,   addErr.u2);
  
  // Distribute error to P, I, D branches
  connect(addErr.y, P.u);
  connect(addErr.y, I.u);
  connect(addErr.y, D.u);
  
  // Reset integrator on trigger
  connect(resetI, I.reset);
  
  // Sum PID terms
  connect(P.y, sumPID.u1);
  connect(I.y, sumPID.u2);
  connect(D.y, sumPID.u3);
  
  // Apply total gain -> limiter -> output
  connect(sumPID.y, gainK.u);
  connect(gainK.y, lim.u);
  connect(lim.y, u);

  // Expose integrator output
  I_out = I.y;
  
end PID_Continuous;