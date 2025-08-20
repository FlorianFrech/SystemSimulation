within FilterSystem;

model FilterSystemModel
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
    C = 0.001,   // F (1 mF converted)
    U_out0 = 0   // V
  ) "First low-pass filter (LPF1)";
  
  LowPassFilter lpf2(
    R = 1000,    // ohm  
    C = 0.001,   // F
    U_out0 = 0   // V
  ) "Second low-pass filter (LPF2)";
  
  BandPassFilter bpf(
    R = 1.26,    // ohm
    L = 1,       // H
    C = 0.0253,  // F
    IL0 = 0      // A
  ) "Band-pass filter (BPF)";

  // Output signals for monitoring (equivalent to plot_config)
  Real src_voltage(unit="V") "Source voltage output";
  Real lpf1_voltage(unit="V") "LPF1 output voltage";  
  Real lpf2_voltage(unit="V") "LPF2 output voltage";
  Real bpf_current(unit="A") "BPF total current";
  Real bpf_inductor_current(unit="A") "BPF inductor current";

equation
  // Signal chain connections (equivalent to sim.connect calls)
  connect(src.U_in, lpf1.U_in);        // SRC.Uin -> LPF1.Uin
  connect(lpf1.U_out, lpf2.U_in);      // LPF1.Uc -> LPF2.Uin  
  connect(lpf2.U_out, bpf.U_in);       // LPF2.Uc -> BPF.U

  // Output monitoring signals
  src_voltage = src.U_in;
  lpf1_voltage = lpf1.U_out;
  lpf2_voltage = lpf2.U_out;
  bpf_current = bpf.I;
  bpf_inductor_current = bpf.IL;

end FilterSystemModel;
