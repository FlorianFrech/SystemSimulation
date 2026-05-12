within ControlledPendulum.Controllers;

model PIDController
  // Parameters (parallel form)
  parameter Real Kp=12 "Proportional gain";
  parameter Real Ki=8 "Integral gain";
  parameter Real Kd=0.02 "Derivative gain";
  parameter Real uMin=-1, uMax=1 "Output limits";
  parameter Boolean useReset=false "Enable integrator reset input";
  
  // Constants
  constant Real Td=0.5  "Derivative time constant";
  constant Real Nd=10 "Derivative filter divisor";
  
  // Inputs
  Modelica.Blocks.Interfaces.RealInput  theta_ref(unit="rad") "Reference angle";
  Modelica.Blocks.Interfaces.RealInput  theta_meas(unit="rad") "Measured angle";
  Modelica.Blocks.Interfaces.BooleanInput resetI(start=false) if useReset "Reset integrator on rising edge";

  // Outputs
  Modelica.Blocks.Interfaces.RealOutput u "Control signal";
  Modelica.Blocks.Interfaces.RealOutput I_out if useReset "Integrator output";

  // Internal constants
  constant Real xi_start=0 "Integrator initial state";
  constant Real xd_start=0 "Derivative initial state";
  
  // Error calculation: e = theta_ref - theta_meas
  Modelica.Blocks.Math.Add addErr(k1=1, k2=-1);
  
  // Proportional part
  Modelica.Blocks.Math.Gain P(k=Kp);
  
  // Integral part
  Modelica.Blocks.Continuous.LimIntegrator I(
    k=Ki,
    outMax=100*uMax,
    outMin=100*uMin,
    y_start=xi_start,
    initType=Modelica.Blocks.Types.Init.InitialState,
    use_reset=useReset);
  
  // Derivative part with first-order filter
  Modelica.Blocks.Continuous.Derivative D(
    k=Kd,
    T=max(Td/Nd, 100*Modelica.Constants.eps), 
    x_start=xd_start,
    initType=Modelica.Blocks.Types.Init.InitialState);
  
  // PID sum: u_presat = P + I + D
  Modelica.Blocks.Math.Add3 sumPID;

  // Output saturation
  Modelica.Blocks.Nonlinear.Limiter lim(uMin=uMin, uMax=uMax);

equation
  // Error: e = theta_ref - theta_meas
  connect(theta_ref, addErr.u1);
  connect(theta_meas, addErr.u2);
  
  // Distribute error to P, I branches (D on measurement)
  connect(addErr.y, P.u);
  connect(addErr.y, I.u);
  connect(theta_meas, D.u);
  
  // Sum PID terms
  connect(P.y, sumPID.u1);
  connect(I.y, sumPID.u2);
  connect(D.y, sumPID.u3);
  
  // Output saturation
  connect(sumPID.y, lim.u);
  connect(lim.y, u);
  
  if useReset then
    connect(resetI, I.reset);
    connect(I.y, I_out);
  end if;
  
end PIDController;
