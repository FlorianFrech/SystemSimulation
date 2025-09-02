within ControlledPendulum;

model DemoModelWall
  /*
   Controlled pendulum with a wall:
    - Reference trajectory
    - Two sensors (reference & state)
    - PID controller
    - Drive
    - Pendulum
    - ImpactWall (compliant contact) whose torque is summed with the drive torque
  */
  
  // Imports
  import Modelica.Constants.pi;
  
  // Components
  ReferenceTrajectory ref;
  
  Sensor              sensor_ref;
  Sensor              sensor_state;
  
  PID_Cont            pid(Nd=10, Td=0.01, Ti=30, k=100);
  
  Drive               drive;
  
  Pendulum            pendulum;
  
  ImpactWall          wall;
  
  // Sum drive torque and wall contact torque before applying to Pendulum
  Modelica.Blocks.Math.Add torqueSum(k1=1, k2=1);
  
  // Wall Signals for plotting
  Modelica.Blocks.Interfaces.RealOutput wall_tau(unit="N.m") = wall.tau;
  Modelica.Blocks.Interfaces.RealOutput wall_penetration(unit="rad") = wall.penetration;
  Modelica.Blocks.Interfaces.BooleanOutput wall_contact = wall.contact;
  
equation
  // Sensing
  connect(ref.q_ref,    sensor_ref.q);
  connect(pendulum.q_state,   sensor_state.q);

  // Control (PID on sensor voltages)
  connect(sensor_ref.U_q,     pid.ref);
  connect(sensor_state.U_q,   pid.y);

  // Drive
  connect(pid.u,              drive.u_control);
  connect(drive.omega,        pendulum.omega_state);

  // Wall connections (reads state, returns contact torque)
  connect(pendulum.q_state,   wall.q);
  connect(pendulum.omega_state, wall.omega);

  // Torque summation: drive torque + wall torque -> pendulum
  connect(drive.torque,       torqueSum.u1);
  connect(wall.tau,           torqueSum.u2);
  connect(torqueSum.y,        pendulum.torque);
  
  annotation(
    experiment(StartTime = 0, StopTime = 20, Interval = 0.001)
  );

end DemoModelWall;