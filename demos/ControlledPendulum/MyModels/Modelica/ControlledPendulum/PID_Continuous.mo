within ControlledPendulum;

model PID_Continuous
  // Parameters
  parameter Real k=10 "Controller gain";
  parameter Real Ti=0.05 "Integral time constant";
  parameter Real Td=0.6 "Derivative time constant";
  parameter Real Nd=10 "Derivative filter divisor";
  parameter Real uMin=-1, uMax=1 "Output limits";
  parameter Real Kaw = 30 "Back-calculation gain for anti-windup 1/Ti";
  parameter Boolean enableFreezeI = true "Enable integrator freeze functionality";
  
  // Inputs
  Modelica.Blocks.Interfaces.RealInput  ref(unit="V") "Reference signal";
  Modelica.Blocks.Interfaces.RealInput  y(unit="V") "Measured output";
  Modelica.Blocks.Interfaces.BooleanInput freezeI(start=false) "Freeze integrator when true (e.g., during wall contact)";

  // Outputs
  Modelica.Blocks.Interfaces.RealOutput u "Control signal";

  // Internal constants
  constant Real xi_start=0 "Integrator initial state";
  constant Real xd_start=0 "Derivative initial state";
  
  // Error calculation: e = ref - y
  Modelica.Blocks.Math.Add addErr(k1=1, k2=-1);
  
  // Proportional part
  Modelica.Blocks.Math.Gain P(k=1);
 
  // Anti-windup: integrator input = e + Kaw*(u_sat - u_presat)
  Modelica.Blocks.Math.Add addIinput;
  Modelica.Blocks.Math.Gain Gaw(k=Kaw);
  
  // Integrator freeze gate
  Modelica.Blocks.Logical.Switch Igate;
  Modelica.Blocks.Sources.Constant zero(k=0);
  Modelica.Blocks.Logical.And freezeGate;
  Modelica.Blocks.Sources.BooleanConstant enableFreeze(k=enableFreezeI);
  
  // Integral part
  Modelica.Blocks.Continuous.Integrator I(
    k=1/Ti, 
    y_start=xi_start,
    initType=Modelica.Blocks.Types.Init.InitialState);
  
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
  
  // For anti-windup: compute (u_sat - u_presat)
  Modelica.Blocks.Math.Add difSat(k1=1, k2=-1);     // u_sat - u_presat

equation
  // Error: e = ref - y
  connect(ref, addErr.u1);
  connect(y,   addErr.u2);
  
  // Distribute error to P, I, D branches
  connect(addErr.y, P.u);
  connect(addErr.y, D.u);
  
  // Anti-windup feedback: I_input = e + Kaw*(u_sat - u_presat)
  connect(addErr.y, addIinput.u1);      // base error
  connect(difSat.y, Gaw.u);             // saturation difference
  connect(Gaw.y, addIinput.u2);         // scaled anti-windup correction

  // Integrator freeze gate
  connect(freezeI, freezeGate.u1);
  connect(enableFreeze.y, freezeGate.u2);
  connect(zero.y, Igate.u1);            // frozen value (0)
  connect(freezeGate.y, Igate.u2);      // combined selector
  connect(addIinput.y, Igate.u3);       // active value (e + anti-windup)
  connect(Igate.y, I.u);                // to integrator
  
  // Sum PID terms
  connect(P.y, sumPID.u1);
  connect(I.y, sumPID.u2);
  connect(D.y, sumPID.u3);
  
  // Apply total gain -> limiter -> output
  connect(sumPID.y, gainK.u);
  connect(gainK.y, lim.u);              // u_presat goes to limiter
  connect(lim.y, u);                    // saturated output
  
  // Anti-windup: difference between saturated and pre-saturated
  connect(lim.y, difSat.u1);            // u_sat
  connect(gainK.y, difSat.u2);          // u_presat (directly from gainK)
  
end PID_Continuous;