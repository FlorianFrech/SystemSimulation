within ControlledPendulum;

model Demo_DrivenWithWall
  /* 
  A model of a controlled pendulum system consisting of:
   - Reference trajectory generator
   - Sensors for reference and state
   - PID controller
   - Drive system
   - Pendulum dynamics
  */

  // Components
  Reference           reference;
  
  AngleEncoder        sensor_ref( q_min = -reference.amplitude,
                                  q_max =  reference.amplitude);

  AngleEncoder        sensor_state( q_min = -reference.amplitude,
                                    q_max =  reference.amplitude);
  
  PID_Continuous        pid(Nd=10, Td=0.05, Ti=0.6, k=10);
  
  Drive               drive;
  
  //Pendulum pendulum;
  //ImpactWall wall(J_eq=pendulum.inertia, sense=-1);
  PendulumWithWallContinuous pendulum;
 
protected
  //Modelica.Blocks.Math.Add torqueSum(k1=1, k2=1);
  //Boolean refBehindWall "True if reference lies on the 'blocked' side of the wall";

equation
  // Sensors
  connect(reference.q_ref, sensor_ref.q);
  connect(pendulum.q, sensor_state.q);
  
  connect(sensor_ref.U_q, pid.ref);
  connect(sensor_state.U_q, pid.y);
  
  // PID -> Drive
  connect(pid.u, drive.u_control);
  
  // Drive <-> Pendulum
  connect(drive.omega, pendulum.omega);
  //connect(drive.torque, torqueSum.u1);
  connect(drive.torque, pendulum.torque);
  
  // Wall connections
  //connect(pendulum.q,   wall.q);
  //connect(pendulum.omega, wall.omega);
  //connect(wall.torque, torqueSum.u2);
  
  // drive torque + wall torque -> pendulum
  //connect(torqueSum.y, pendulum.torque);
  
  // Freeze integrator logic
  //refBehindWall = wall.sense * (reference.q_ref - wall.q_wall) > 0;
  //pid.freezeI = refBehindWall;
  //pid.freezeI = false;
  
  annotation(
    experiment(StartTime = 0, StopTime = 10, Interval = 0.01)
  );

end Demo_DrivenWithWall;
