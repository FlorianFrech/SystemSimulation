within FilterSystem;
model DemoModel
  Real src_voltage(unit="V");
  Real lpf1_voltage(unit="V");
  Real lpf2_voltage(unit="V");
  Real bpf_current(unit="A");
  Real bpf_IL(unit="A");
  FilterSystem.SignalSource src(A1=60, A2=5, f1=0.159, f2=7.96);
  FilterSystem.LowPassFilter lpf1(R=1000, C=1e-03, U0=0);
  FilterSystem.LowPassFilter lpf2(R=1000, C=1e-03, U0=0);
  FilterSystem.BandPassFilter bpf(R=1.26, C=0.0253, L=1, IL0=0);
equation
  connect(src.U_in, lpf1.U_in);
  connect(lpf1.U_out, lpf2.U_in);
  connect(lpf2.U_out, bpf.U_in);
  src_voltage = src.U_in;
  lpf1_voltage = lpf1.U_out;
  lpf2_voltage = lpf2.U_out;
  bpf_current = bpf.I;
  bpf_IL = bpf.IL;
end DemoModel;