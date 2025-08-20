package FilterSystem
"Complete filter system package - equivalent to LPF_main.py simulation"

  model SignalSource
  "Composite sine wave signal generator - equivalent to signal_source.py"
    // Constants
    import Modelica.Constants.pi;
    
    // Output connector
    Modelica.Blocks.Interfaces.RealOutput U_in(unit="V") "Output voltage signal";
    
    // Parameters (matching Python MODULE PARAMETERS)
    parameter Real A1(unit="V") = 60 "Amplitude of first sine wave";
    parameter Real A2(unit="V") = 5 "Amplitude of second sine wave";
    parameter Real f1(unit="Hz") = 0.159 "Frequency of the first sine wave";
    parameter Real f2(unit="Hz") = 7.96 "Frequency of the second sine wave";
    
    // Internal variables
    Real s1(unit="V") "First sine wave component";
    Real s2(unit="V") "Second sine wave component";
    
  equation
    // Generate the two sine waves (matching Python signal_generator function)
    s1 = A1 * sin(2 * pi * f1 * time);
    s2 = A2 * sin(2 * pi * f2 * time);
    
    // Output is the sum of the signals (s1 + s2)
    U_in = s1 + s2; 
  end SignalSource;

  model LowPassFilter
  "Low-pass filter - equivalent to lowpass_filter.py"
      // Input connector
      Modelica.Blocks.Interfaces.RealInput U_in(unit="V") "Input voltage signal";
      
      // Output connector
      Modelica.Blocks.Interfaces.RealOutput U_out(unit="V") "Output voltage signal";

      // Parameters (matching Python MODULE PARAMETERS)
      parameter Real R(unit="Ohm") = 1000 "Resistance value";
      parameter Real C(unit="F") = 1e-6 "Capacitance value";
      parameter Real U_out0(unit="V") = 0 "Initial output voltage";

  initial equation
      // Initial condition for the output voltage (matching Python INITIAL_VALUES)
      U_out = U_out0;
      
  equation
      // Low-pass filter equation (matching Python dUc function)
      // dUc/dt = (Uin - Uc) / (R * C)
      der(U_out) = (U_in - U_out) / (R * C);
  end LowPassFilter;

  model BandPassFilter
  "Bandpass filter - equivalent to bandpass_filter.py"
      // Input connector
      Modelica.Blocks.Interfaces.RealInput U_in(unit="V") "Input voltage signal";

      // Output connectors
      Modelica.Blocks.Interfaces.RealOutput I(unit="A") "Total current signal";
      Modelica.Blocks.Interfaces.RealOutput IL(unit="A") "Inductor current signal";

      // Parameters (matching Python PARAMETERS)
      parameter Real R(unit="Ohm") = 100 "Resistance value";
      parameter Real C(unit="F") = 1e-6 "Capacitance value";
      parameter Real L(unit="H") = 0.01 "Inductance value";
      parameter Real IL0(unit="A") = 0 "Initial current through the inductor";

      // Internal variables
      Real I_R(unit="A") "Current through resistor";
      Real I_C(unit="A") "Current through capacitor";
      Real dU_dt(unit="V/s") "Derivative of input voltage";

  initial equation
      // Initial condition for the inductor current (matching Python INITIAL_VALUES)
      IL = IL0;

  equation
      // Calculate derivative of input voltage (matching Python update_du)
      dU_dt = der(U_in);
      
      // Current through each component (parallel RLC circuit)
      I_R = U_in / R;                    // Resistor current (Ohm's law)
      I_C = C * dU_dt;                   // Capacitor current (matching Python compute_total_current)
      der(IL) = U_in / L;                // Inductor voltage-current relationship (matching Python dIL)
      
      // Total current is sum of all branch currents (matching Python compute_total_current)
      I = I_R + I_C + IL;
  end BandPassFilter;

  model FilterChainSystem
  "Complete filter chain system equivalent to LPF_main.py"

    // Component instances with parameters matching the Python simulation
    SignalSource src(
      A1 = 60,     // V
      A2 = 5,      // V  
      f1 = 0.159,  // Hz
      f2 = 7.96    // Hz
    ) "Signal source (SRC)";
    
    LowPassFilter lpf1(
      R = 1000,    // ohm
      C = 0.001,   // F (1 mF converted from Python normalise_units=True)
      U_out0 = 0   // V
    ) "First low-pass filter (LPF1)";
    
    LowPassFilter lpf2(
      R = 1000,    // ohm  
      C = 0.001,   // F (0.001 F as specified in Python)
      U_out0 = 0   // V
    ) "Second low-pass filter (LPF2)";
    
    BandPassFilter bpf(
      R = 1.26,    // ohm (as specified in Python)
      L = 1,       // H (as specified in Python)
      C = 0.0253,  // F (as specified in Python)
      IL0 = 0      // A
    ) "Band-pass filter (BPF)";

    // Output signals for monitoring (equivalent to plot_config)
    Real src_voltage(unit="V") = src.U_in "Source voltage output";
    Real lpf1_voltage(unit="V") = lpf1.U_out "LPF1 output voltage";  
    Real lpf2_voltage(unit="V") = lpf2.U_out "LPF2 output voltage";
    Real bpf_current(unit="A") = bpf.I "BPF total current";
    Real bpf_inductor_current(unit="A") = bpf.IL "BPF inductor current";

  equation
    // Signal chain connections (equivalent to sim.connect calls)
    connect(src.U_in, lpf1.U_in);        // SRC.Uin -> LPF1.Uin
    connect(lpf1.U_out, lpf2.U_in);      // LPF1.Uc -> LPF2.Uin  
    connect(lpf2.U_out, bpf.U_in);       // LPF2.Uc -> BPF.U

    annotation(
      experiment(StartTime = 0, StopTime = 2, Tolerance = 1e-6, Interval = 0.01),
      Documentation(info="<html>
      <p>This system replicates the Python simulation from LPF_main.py</p>
      <p><b>Signal Chain:</b></p>
      <ul>
      <li>SignalSource generates composite sine wave (60V@0.159Hz + 5V@7.96Hz)</li>
      <li>First LowPassFilter (R=1kΩ, C=1mF) filters the signal</li>
      <li>Second LowPassFilter (R=1kΩ, C=1mF) provides additional filtering</li>
      <li>BandPassFilter (R=1.26Ω, L=1H, C=0.0253F) processes the final signal</li>
      </ul>
      <p><b>Simulation Parameters:</b></p>
      <ul>
      <li>Duration: 2 seconds (t_end=2)</li>
      <li>Time step: 0.01 seconds (dt=0.01)</li>
      </ul>
      <p><b>Monitoring Variables:</b></p>
      <ul>
      <li>Group 1: src_voltage, lpf1_voltage, lpf2_voltage (Real-Time LPFs)</li>
      <li>Group 2: bpf_current, bpf_inductor_current (Real-Time BPF)</li>
      </ul>
      </html>")
    );
  end FilterChainSystem;

  annotation (Documentation(info="<html>
  <p>FilterSystem package contains Modelica implementations equivalent to the Python simulation in LPF_main.py</p>
  <p>All models are implemented from first principles without using existing Modelica component libraries.</p>
  </html>"));
end FilterSystem;
