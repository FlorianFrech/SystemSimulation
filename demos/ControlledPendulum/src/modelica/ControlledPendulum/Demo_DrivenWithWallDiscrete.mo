within ControlledPendulum;

model Demo_DrivenWithWallDiscrete
  /* 
  A model of a controlled pendulum system with integrator reset on wall contact.
  */
  
  // Parameters
  parameter Boolean useReset(start=false, fixed=false);

  // Components
  Reference           reference;
  
  AngleEncoder        sensor_ref( q_min = -reference.amplitude,
                                  q_max =  reference.amplitude);

  AngleEncoder        sensor_state( q_min = -reference.amplitude,
                                    q_max =  reference.amplitude);
  
  PID_Continuous      pid(Nd=10, Td=0.1, Ti=0.2, k=10);
  
  Drive               drive;
  
  PendulumWithWallDiscrete    pendulum;
 
protected
  discrete Boolean contact(start=false) "Current contact state";
  discrete Boolean contactRisingEdge(start=false) "Rising edge detector for contact";

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
  
  // Rising edge detection using when clause
  when pendulum.contact and not pre(contact) then
    contactRisingEdge = true;
    contact = true;
  elsewhen not pendulum.contact then
    contactRisingEdge = false;
    contact = false;
  end when;
  
  // Reset integrator on wall impact
  if useReset then
    pid.resetI = contactRisingEdge;
  else
    pid.resetI = false;
 end if;
  
  annotation(
    experiment(StartTime = 0, StopTime = 10, Interval = 0.01)
  );

end Demo_DrivenWithWallDiscrete;