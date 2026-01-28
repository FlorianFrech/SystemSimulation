within ControlledPendulum;

model PendulumAnimation
  "Wrapper around PendulumWithWall that adds 3D visualization"
  extends PendulumWithWall(with_contact = true);

  import Modelica.Mechanics.MultiBody.Visualizers.Advanced.Shape;
  import Modelica.Constants.pi;

  // World object needed for 3D animation in OMEdit
  inner Modelica.Mechanics.MultiBody.World world(
    gravityType    = Modelica.Mechanics.MultiBody.Types.GravityTypes.NoGravity,
    animateWorld   = true,
    animateGravity = false);

  // Pendulum length = distance joint -> head center (from physical model)
  parameter Real Lvis  = 0.75 "Pendulum length (joint to head center)";
  // Radius of spherical pendulum head (graphics only)
  parameter Real rHead = 0.05 "Radius of spherical pendulum head";

protected 
  // Geometry vectors in world coordinates
  Real rBob[3];
  Real rRod[3];
  Real eRod[3];
  Real rWall[3];

  // 1) Rod length so that it ends at the inner surface of the head
  parameter Real Lrod = Lvis - rHead;

  // Visual rod between joint and head
  Shape rod(
    shapeType       = "cylinder",
    r               = rRod,
    lengthDirection = eRod,
    widthDirection  = {0,0,1},
    length          = Lrod,
    width           = 0.03,
    height          = 0.03,
    color           = {0,0,255});

  // Visual head (sphere) whose center coincides with mass point
  Shape bob(
    shapeType       = "sphere",
    r               = rBob,
    lengthDirection = {1,0,0},
    widthDirection  = {0,1,0},
    // length/width/height are the diameters of the sphere
    length          = 2*rHead,
    width           = 2*rHead,
    height          = 2*rHead,
    color           = {255,0,0});

  // 2) Visual wall:
  //    vertical bar at x = -rHead so that the head just touches it when q = 0,
  //    and the rod (at x=0 for q=0) does NOT intersect the wall.
  parameter Real wallWidth  = 0.02 "Wall thickness in x-direction";
  parameter Real wallHeight = 0.5 "Wall thickness out of plane";

  Shape wallShape(
    shapeType       = "box",
    r               = rWall,
    // vertical downward
    lengthDirection = {0,-1,0},
    // wall thickness in -x direction
    widthDirection  = {-1,0,0},
    length          = Lvis,
    width           = wallWidth,
    height          = wallHeight,
    color           = {160,160,160});

equation
  // Unit direction of rod/head (planar motion in x–y plane)
  eRod = { sin(q), -cos(q), 0 };

  // Head center is at distance Lvis along eRod
  rBob = 1*eRod;

  // Rod center is halfway between joint and rod tip (at distance Lrod)
  rRod = 0.5*Lrod*eRod;

  // Wall: vertical bar from y=0 down to y=-Lvis at x < 0.
  // Right edge (closest to pendulum) is at x = -rHead.
  // With width along -x, the right edge is center_x + width/2:
  //   center_x + wallWidth/2 = -rHead  =>  center_x = -(rHead + wallWidth/2)
  rWall = { -(rHead + wallWidth/2), -0.5*Lvis, 0 };

  annotation(
    experiment(StartTime = 0, StopTime = 2, Interval = 0.001)
  );
end PendulumAnimation;
