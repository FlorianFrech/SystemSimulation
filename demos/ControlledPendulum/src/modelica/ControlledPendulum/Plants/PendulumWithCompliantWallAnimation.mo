within ControlledPendulum.Plants;

model PendulumWithCompliantWallAnimation
  "Visualization wrapper around PendulumWithCompliantWall"
  extends PendulumWithCompliantWall(with_contact = true, theta_start=0.5);

  import Modelica.Mechanics.MultiBody.Visualizers.Advanced.Shape;

  // World object needed for 3D animation in OMEdit
  inner Modelica.Mechanics.MultiBody.World world(
    gravityType    = Modelica.Mechanics.MultiBody.Types.GravityTypes.NoGravity,
    animateWorld   = true,
    animateGravity = false);

  // Keep visualization geometry consistent with the physical model.
  parameter Real Lvis  = L "Pendulum length (joint to head center)";
  parameter Real rHead = 0.05 "Radius of spherical pendulum head";

protected 
  // Geometry vectors in world coordinates
  Real rBob[3];
  Real eRod[3];
  Real rWall[3];

  // Rod length so that it ends at the inner surface of the head
  parameter Real Lrod = Lvis - rHead;

  // Visual rod between joint and head
  Shape rod(
    shapeType       = "cylinder",
    r               = {0,0,0},
    r_shape         = {0,0,0},
    lengthDirection = eRod,
    widthDirection  = {0,0,1},
    length          = Lrod,
    width           = 0.03,
    height          = 0.03,
    color           = {0,0,255});

  // Visual head (sphere) whose center coincides with mass point
  Shape bob(
    shapeType       = "sphere",
    r               = {0,0,0},
    r_shape         = rBob - rHead*eRod,
    lengthDirection = eRod,
    widthDirection  = {0,0,1},
    length          = 2*rHead,
    width           = 2*rHead,
    height          = 2*rHead,
    color           = {255,0,0});

  // Visual wall
  parameter Real wallWidth  = 0.02 "Wall thickness in x-direction";
  parameter Real wallHeight = 0.5 "Wall thickness out of plane";

  Shape wallShape(
    shapeType       = "box",
    r               = {0,0,0},
    r_shape         = rWall,
    lengthDirection = {0,-1,0},
    widthDirection  = {-1,0,0},
    length          = Lvis,
    width           = wallWidth,
    height          = wallHeight,
    color           = {160,160,160});

equation
  assert(Lrod > 0, "rHead must be smaller than Lvis for a valid rod geometry.");

  // Unit direction of rod/head (planar motion in x–y plane)
  eRod = { sin(theta), -cos(theta), 0 };

  // Head center is at distance Lvis along eRod
  rBob = Lvis*eRod;

  // Wall: vertical bar from y=0 down to y=-Lvis at x < 0.
  rWall = { -(rHead + wallWidth/2), -0.5*Lvis, 0 };

  annotation(
    experiment(StartTime = 0, StopTime = 5, Interval = 0.001)
  );
end PendulumWithCompliantWallAnimation;
