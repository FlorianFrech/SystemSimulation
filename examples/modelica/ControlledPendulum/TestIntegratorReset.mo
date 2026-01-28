within ControlledPendulum;

model TestIntegratorReset
  "Simple test model for LimIntegrator reset functionality"
  
  // Constant input signal
  Modelica.Blocks.Sources.Constant constantInput(k=1.0);
  
  // Integrator with reset
  Modelica.Blocks.Continuous.LimIntegrator integrator(
    k=1.0,
    outMax=1e10,
    outMin=-1e10,
    y_start=0,
    use_reset=true);
  
  // Periodic reset signal using boolean pulse
  Modelica.Blocks.Sources.BooleanPulse resetPulse(
    width=1,        // 1% duty cycle (very short pulse)
    period=2.0,     // Reset every 2 seconds
    startTime=1.0); // First reset at t=1s
  
  // Output
  Modelica.Blocks.Interfaces.RealOutput integratorOutput;
  Modelica.Blocks.Interfaces.BooleanOutput resetSignal;

equation
  // Connect input to integrator
  connect(constantInput.y, integrator.u);
  
  // Connect reset signal
  connect(resetPulse.y, integrator.reset);
  
  // Output signals for plotting
  integratorOutput = integrator.y;
  resetSignal = resetPulse.y;
  
  annotation(
    experiment(StartTime=0, StopTime=10, Interval=0.01),
    Documentation(info="<html>
<p>This model tests the LimIntegrator reset functionality.</p>
<p><b>Expected behavior:</b></p>
<ul>
<li>Integrator output should ramp up linearly (slope = 1)</li>
<li>At t=1s, 3s, 5s, 7s, 9s the integrator should reset to 0</li>
<li>After each reset, it should start ramping up again</li>
</ul>
</html>"));

end TestIntegratorReset;