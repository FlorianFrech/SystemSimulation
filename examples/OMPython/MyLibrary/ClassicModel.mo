model ClassicModel "This is the typical equation-oriented model - Classic Lotka-Volterra"
  // Parameters
  parameter Real alpha=0.1 "Reproduction rate of prey";
  parameter Real beta=0.02 "Mortality rate of predator per prey";
  parameter Real gamma=0.4 "Mortality rate of predator";
  parameter Real delta=0.02 "Reproduction rate of predator per prey";
  parameter Real x0=10 "Start value of prey population";
  parameter Real y0=10 "Start value of predator population";
  
  // Variables with hint for initial values
  Real x(start=x0) "Prey population";
  Real y(start=y0) "Predator population";

// System Equation
equation
  der(x) = x*(alpha-beta*y);
  der(y) = y*(delta*x-gamma);
  annotation(experiment(StartTime = 0, StopTime = 140));
end ClassicModel;
