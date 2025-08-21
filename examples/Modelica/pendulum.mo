model Pendulum
"Example of a simple 1-DOF pendulum."
    // Types
    type Angle=Real(unit="rad");
    type AngularVelocity=Real(unit="rad/s");
    type Length=Real(unit="m", min=0);
    type Gravity=Real(unit="m/s2", min=0);

    // Parameters
    parameter Length l=1.0 "Length of the pendulum";
    parameter Gravity g=9.81 "Acceleration due to gravity";
    parameter Angle theta0=0.1 "Initial angle of the pendulum";
    parameter AngularVelocity omega0=0.0 "Initial angular velocity of the pendulum";

    // Variables
    Real theta(start=theta0, fixed=true) "Angle of the pendulum";
    Real omega(start=omega0, fixed=true) "Angular velocity of the pendulum";

equation
    der(theta) = omega "Derivative of angle is angular velocity";
    l^2*der(omega) = -g*l*sin(theta) "Equation of motion for the pendulum";
    annotation(experiment(StartTime = 0, StopTime = 10, Tolerance = 1e-6));
end Pendulum;