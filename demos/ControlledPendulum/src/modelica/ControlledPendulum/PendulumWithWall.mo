within ControlledPendulum;

model PendulumWithWall
  // Imports
  import Modelica.Constants.pi;
  
  // Parameters
  parameter Boolean with_contact(start=true)
    "Boolean flag for contact simulation";
    
  // Components
  Pendulum            pendulum(q0=0);
  ImpactWall          wall(k=1e10,
                           q_wall=0,
                           sense=-1,
                           J_eq=pendulum.inertia) if with_contact;
  
  // External torque input
  Modelica.Blocks.Interfaces.RealInput torque(unit="N.m");
  
  // Outputs
  Modelica.Blocks.Interfaces.RealOutput q(unit="rad");
  Modelica.Blocks.Interfaces.RealOutput omega(unit="rad/s");
  Modelica.Blocks.Interfaces.RealOutput alpha(unit="rad/s2");
  Modelica.Blocks.Interfaces.BooleanOutput contact;

protected
  Modelica.Blocks.Math.Add torqueSum(k1=1, k2=1) if with_contact;
  
equation
  if with_contact then
    // Wall connections
    connect(pendulum.q,   wall.q);
    connect(pendulum.omega, wall.omega);
    
    // External torque + wall torque -> pendulum
    connect(torque, torqueSum.u1);
    connect(wall.torque, torqueSum.u2);
    connect(torqueSum.y, pendulum.torque);
    
    //Contact flag
    contact = wall.contact;
  else
    // No wall - directly apply external torque
    connect(torque, pendulum.torque);
    contact = false;
  end if;
 
  // Output signals from pendulum
  q = pendulum.q;
  omega = pendulum.omega;
  alpha = pendulum.alpha;
  
    
  annotation(
    experiment(StartTime = 0, StopTime = 2, Interval = 0.001)
  );

end PendulumWithWall;
