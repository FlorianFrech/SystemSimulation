within FilterSystem;
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



