within ;
package FilterSystem
  import Modelica;

  package Components
    partial model TwoPin
      Modelica.Electrical.Analog.Interfaces.Pin p, n;
      Modelica.Units.SI.Voltage v = p.v - n.v;
      Modelica.Units.SI.Current i;
    equation
      // KCL: current into p equals current out of n
      p.i + n.i = 0;
      i = p.i;
    end TwoPin;

    model Resistor "Ohmic resistor"
      extends FilterSystem.Components.TwoPin;
      parameter Modelica.Units.SI.Resistance R = 1e3;
    equation
      v = R*i;
    end Resistor;

    model Capacitor "Capacitor (charge convention)"
      extends FilterSystem.Components.TwoPin;
      parameter Modelica.Units.SI.Capacitance C = 1e-6;
    equation
      i = C*der(v);
    end Capacitor;

    model Inductor "Inductor (flux convention)"
      extends FilterSystem.Components.TwoPin;
      parameter Modelica.Units.SI.Inductance L = 1e-2;
    equation
      v = L*der(i);
    end Inductor;
  end Components;

  package Filters
    model LowPassFilterRC
      "Series R–C one-port; Uc is capacitor voltage"
      Modelica.Electrical.Analog.Interfaces.Pin p, n;
      parameter Modelica.Units.SI.Resistance  R = 1e3;
      parameter Modelica.Units.SI.Capacitance C = 1e-6;

      FilterSystem.Components.Resistor  R1(R=R);
      FilterSystem.Components.Capacitor C1(C=C);

      Modelica.Blocks.Interfaces.RealOutput Uc "Capacitor voltage";
    equation
      connect(p,   R1.p);
      connect(R1.n, C1.p);
      connect(C1.n, n);

      Uc = C1.v;  // v = p.v - n.v from TwoPin
      annotation (Icon(graphics={Text(extent={{-90,76},{90,46}}, textString="%name")}));
    end LowPassFilterRC;

    model BandPassFilterRLC
      "Parallel RLC one-port; I is total current, IL is inductor current"
      Modelica.Electrical.Analog.Interfaces.Pin p, n;
      parameter Modelica.Units.SI.Resistance  R = 10;
      parameter Modelica.Units.SI.Inductance  L = 0.01;
      parameter Modelica.Units.SI.Capacitance C = 25e-3;

      FilterSystem.Components.Resistor  R1(R=R);
      FilterSystem.Components.Inductor  L1(L=L);
      FilterSystem.Components.Capacitor C1(C=C);

      Modelica.Blocks.Interfaces.RealOutput IL "Inductor current";
      Modelica.Blocks.Interfaces.RealOutput I  "Total current";
    equation
      // Parallel branches between p and n
      connect(p, R1.p); connect(R1.n, n);
      connect(p, L1.p); connect(L1.n, n);
      connect(p, C1.p); connect(C1.n, n);

      IL = L1.i;
      I  = R1.i + L1.i + C1.i;
    end BandPassFilterRLC;
  end Filters;

  package Sources
    model SignalSource
      "Two-tone voltage source"
      import Modelica.Constants.pi;

      Modelica.Electrical.Analog.Interfaces.PositivePin p;
      Modelica.Electrical.Analog.Interfaces.NegativePin n;

      parameter Real A1 = 60 "Amplitude 1 [V]";
      parameter Real A2 = 5  "Amplitude 2 [V]";
      parameter Real f1 = 0.159 "Frequency 1 [Hz]";
      parameter Real f2 = 7.96  "Frequency 2 [Hz]";
      parameter Real phase1 = 0 "Phase 1 [rad]";
      parameter Real phase2 = 0 "Phase 2 [rad]";

    protected
      Real v1, v2;
    equation
      v1 = A1*sin(2*pi*f1*time + phase1);
      v2 = A2*sin(2*pi*f2*time + phase2);

      // KVL across source & KCL through source
      p.v - n.v = v1 + v2;
      0 = p.i + n.i;
    end SignalSource;
  end Sources;

  model Demo
    // Source
    FilterSystem.Sources.SignalSource SRC;

    // Two low-pass filters (RC one-ports)
    FilterSystem.Filters.LowPassFilterRC LPF1(R=1e3, C=1e-6);
    FilterSystem.Filters.LowPassFilterRC LPF2(R=1e3, C=1e-3);

    // Band-pass (parallel RLC)
    FilterSystem.Filters.BandPassFilterRLC BPF(R=1e2, L=0.01, C=1e-6);

    // Bridges to drive electrical stages from Real signals (cascading like the Python pipeline)
    Modelica.Electrical.Analog.Sources.SignalVoltage vin2;
    Modelica.Electrical.Analog.Sources.SignalVoltage vinBPF;

    // Ground
    Modelica.Electrical.Analog.Basic.Ground g;

  equation
    // Stage 0: drive LPF1 from SRC
    connect(SRC.p, LPF1.p);
    connect(SRC.n, g.p);
    connect(LPF1.n, g.p);

    // Stage 1: LPF1.Uc (Real) → SignalVoltage → LPF2
    connect(LPF1.Uc, vin2.v);
    connect(vin2.p,  LPF2.p);
    connect(vin2.n,  g.p);
    connect(LPF2.n,  g.p);

    // Stage 2: LPF2.Uc (Real) → SignalVoltage → BPF (parallel RLC)
    connect(LPF2.Uc, vinBPF.v);
    connect(vinBPF.p, BPF.p);
    connect(vinBPF.n, g.p);
    connect(BPF.n,    g.p);

    annotation (experiment(StopTime=10, Interval=0.01));
  end Demo;

  annotation (uses(Modelica(version="4.0.0")));
end FilterSystem;