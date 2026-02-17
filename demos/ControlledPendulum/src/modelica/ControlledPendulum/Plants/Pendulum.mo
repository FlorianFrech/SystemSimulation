within ControlledPendulum.Plants;

model Pendulum
  extends PendulumBase;

equation
  tau_total = tau;
end Pendulum;
