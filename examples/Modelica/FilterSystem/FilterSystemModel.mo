within FilterSystem;

model FilterSystemModel
"Complete filter chain system equivalent to LPF_main.py"

   //Component instances with parameters matching the Python simulation
  SignalSource src(
    A1 = 60,     // V
    A2 = 5,      // V  
    f1 = 0.159,  // Hz
    f2 = 7.96    // Hz
  );
  
  LowPassFilter lpf1(
    R = 1000,    // ohm
    C = 0.001,   // F (1 mF converted)
    U_out0 = 0   // V
  ) "First low-pass filter (LPF1)";
  
  LowPassFilter lpf2(
    R = 1000,    // ohm  
    C = 0.001,   // F
    U_out0 = 0   // V
  );
  
  BandPassFilter bpf(
    R = 1.26,    // ohm
    L = 1,       // H
    C = 0.0253,  // F
    IL0 = 0      // A
  );

  // Output signals for monitoring (equivalent to plot_config)
  Real src_voltage(unit="V");
  Real lpf1_voltage(unit="V");  
  Real lpf2_voltage(unit="V");
  Real bpf_current(unit="A");
  Real bpf_inductor_current(unit="A");

equation
  connect(src.U_in, lpf1.U_in);        
  connect(lpf1.U_out, lpf2.U_in);      
  connect(lpf2.U_out, bpf.U_in);  

  // Output monitoring signals
  src_voltage = src.U_in;
  lpf1_voltage = lpf1.U_out;
  lpf2_voltage = lpf2.U_out;
  bpf_current = bpf.I;
  bpf_inductor_current = bpf.IL;

end FilterSystemModel;
