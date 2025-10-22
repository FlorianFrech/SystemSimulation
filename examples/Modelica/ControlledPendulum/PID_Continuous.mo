within ControlledPendulum;

model PID_Continuous
  /*
  The model implements a continuous PID controller which can be used as Co-Sim FMU.
  The controller behavior is described by the parameters:
    - k: gain within the total gain block
    - Ti: Time constant of the integrator block
    - Td: Time constant of the derivative block
    - Nd: Parameter for the derivative block
    - uMin/uMax: Limits for the output signal
  */
  
  // Parameters
  parameter Real k=1;
  parameter Real Ti=0.5;
  parameter Real Td=0.1;
  parameter Real Nd=10;
  parameter Real uMin=-1, uMax=1;
  
  // Inputs
  Modelica.Blocks.Interfaces.RealInput  ref(unit="V");
  Modelica.Blocks.Interfaces.RealInput  y(unit="V");
  
  // Outputs
  Modelica.Blocks.Interfaces.RealOutput u;

protected
  // Internal constants
  constant Real xi_start=0 "integrator output start";
  constant Real xd_start=0 "derivative state start";
  
  // Add Error: error = ref - y
  Modelica.Blocks.Math.Add addErr(k1=1, k2=-1);
  
  // Proportional part
  Modelica.Blocks.Math.Gain P(k=1);
  
  // Integral part
  Modelica.Blocks.Continuous.Integrator I(k=1/Ti, y_start=xi_start,
    initType=Modelica.Blocks.Types.Init.InitialState);
  
  // Derivative part
  Modelica.Blocks.Continuous.Derivative D(k=Td,
    T=max(Td/Nd, 100*Modelica.Constants.eps), x_start=xd_start,
    initType=Modelica.Blocks.Types.Init.InitialState);
  
  // Adder
  Modelica.Blocks.Math.Add3 sumPID;
  
  // Total Gain Block
  Modelica.Blocks.Math.Gain gainK(k=k);
 
  // Limit control to -1 <= 1 <= 1
  Modelica.Blocks.Nonlinear.Limiter lim(uMin=uMin, uMax=uMax);

equation
  // Calculate the error
  connect(ref, addErr.u1);
  connect(y,   addErr.u2);
  
  // Connect error to input connector of Proportional, Integral, and derivative part
  connect(addErr.y, P.u); connect(addErr.y, I.u); connect(addErr.y, D.u);
  
  // Connect outputs to total adder block
  connect(P.y, sumPID.u1); connect(I.y, sumPID.u2); connect(D.y, sumPID.u3);
  
  // Apply the global gain and limit output signal
  connect(sumPID.y, gainK.u); connect(gainK.y, lim.u); connect(lim.y, u);
end PID_Continuous;
