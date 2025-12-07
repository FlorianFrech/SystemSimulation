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
  
  PID_Continuous        pid(Nd=10, Td=0.05, Ti=0.6, k=10,enableFreezeI=true);
  
  Drive               drive;
  
  PendulumWithWall pendulum;
 
protected
  Boolean refBehindWall "True if reference lies on the 'blocked' side of the wall";

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
  connect(drive.torque, pendulum.torque);
  
  // Freeze integrator logic
  refBehindWall = pendulum.wall.sense * (reference.q_ref - pendulum.wall.q_wall) > 0;
  pid.freezeI = refBehindWall;
  
  annotation(
    experiment(StartTime = 0, StopTime = 10, Interval = 0.01)
  );

end Demo_DrivenWithWall;
