within ControlledPendulum;

model ControlUnit
  // Parameters
  parameter Integer wall_sense = -1;
  parameter Real wall_position(unit="rad")=0;
  
  // Components
  Reference           reference;
  AngleEncoder        sensor_ref( q_min = -reference.amplitude,
                                  q_max =  reference.amplitude);
  AngleEncoder        sensor_state( q_min = -reference.amplitude,
                                    q_max =  reference.amplitude);
  PID_Continuous        pid(Nd=10, Td=0.05, Ti=0.6, k=10,enableFreezeI=true);
  
  // Interfaces
  Modelica.Blocks.Interfaces.RealInput q_pendulum(unit="rad");
  Modelica.Blocks.Interfaces.RealOutput u_control;
 
protected
  Boolean refBehindWall "True if reference lies on the 'blocked' side of the wall";

equation
  // Sensors
  connect(reference.q_ref, sensor_ref.q);
  connect(q_pendulum, sensor_state.q);
  
  connect(sensor_ref.U_q, pid.ref);
  connect(sensor_state.U_q, pid.y);
  
  // PID -> Drive
  connect(pid.u, u_control);
  
  // Freeze integrator logic
  refBehindWall = wall_sense * (reference.q_ref - wall_position) > 0;
  pid.freezeI = refBehindWall;
  
  annotation(
    experiment(StartTime = 0, StopTime = 10, Interval = 0.01)
  );

end ControlUnit;