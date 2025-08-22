model Pendulum
"Example of a simple 1-DOF pendulum."
    // Types
    type Angle=Real(unit="rad");
    type AngularVelocity=Real(unit="rad/s");
    type Length=Real(unit="m", min=0);
    type Gravity=Real(unit="m/s2", min=0);

    // Parameters
    parameter Length l=1.0;
    parameter Gravity g=9.81;
    parameter Angle theta0=0.1;
    parameter AngularVelocity omega0=0.0;

    // Variables
    Real theta(start=theta0, fixed=true);
    Real omega(start=omega0, fixed=true);

equation
    der(theta) = omega;
    l^2*der(omega) = -g*l*sin(theta);
    annotation(experiment(StartTime = 0, StopTime = 10, Tolerance = 1e-6));
end Pendulum;