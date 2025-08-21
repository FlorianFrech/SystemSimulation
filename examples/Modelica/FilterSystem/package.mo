package FilterSystem
"Complete filter system package - equivalent to LPF_main.py simulation"

  annotation (Documentation(info="<html>
  <p>FilterSystem package contains Modelica implementations equivalent to the Python simulation in LPF_main.py</p>
  <p>All models are implemented from first principles without using existing Modelica component libraries.</p>
  <p><b>Package Contents:</b></p>
  <ul>
  <li>SignalSource - Composite sine wave generator</li>
  <li>LowPassFilter - RC low-pass filter</li>
  <li>BandPassFilter - RLC bandpass filter</li>
  <li>FilterSystemModel - Complete connected system</li>
  </ul>
  </html>"));
end FilterSystem;
