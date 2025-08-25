within FilterSystem;

model BandPassFilter
    // Input connector
    Modelica.Blocks.Interfaces.RealInput U_in(unit="V") "Input voltage signal";

    // Output connectors
    Modelica.Blocks.Interfaces.RealOutput I(unit="A") "Total current signal";
    Modelica.Blocks.Interfaces.RealOutput IL(unit="A") "Inductor current signal";

    // Parameters
    parameter Real R(unit="Ohm") = 100 "Resistance value";
    parameter Real C(unit="F") = 1e-6 "Capacitance value";
    parameter Real L(unit="H") = 0.01 "Inductance value";
    parameter Real IL0(unit="A") = 0 "Initial current through the inductor";

    // Internal variables
    Real I_R(unit="A") "Current through resistor";
    Real I_C(unit="A") "Current through capacitor";
    Real dU_dt(unit="V/s") "Derivative of input voltage";

initial equation
    // Initial condition for the inductor current
    IL = IL0;

equation
    // Calculate derivative of input voltage
    dU_dt = der(U_in);
    
    // Current through each component (parallel RLC circuit)
    I_R = U_in / R;                    // Resistor current (Ohm's law)
    I_C = C * dU_dt;                   // Capacitor current
    der(IL) = U_in / L;                // Inductor voltage-current relationship
    
    // Total current is sum of all branch currents
    I = I_R + I_C + IL;

end BandPassFilter;
