model QuiescentModelWithInheritance
  extends ClassicModel;
initial equation // are required for initilization to obtain a unique solution
    der(x) = 0;
    der(y) = 0;
end QuiescentModelWithInheritance;
