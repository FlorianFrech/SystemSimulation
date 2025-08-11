model FirstOrder "A simple first order differential equation"
    Real x "State variable";
initial equation
    x = 2 "Used before simulation to compute initial values";
equation
    der(x) = 1 - x "Drives value of x towards 1.0";
    annotation(experiment(StartTime = 0, StopTime = 8));
end FirstOrder;
