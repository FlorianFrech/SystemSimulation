import opensim as osim
import numpy as np

class PendulumModel(osim.Model):
    def __init__(self, mass=80*0.2, length=0.4, inertia=osim.Inertia(0.1, 0.1, 0.1)):
        super().__init__()
        self.setName('pendulum')
        self.setGravity(osim.Vec3(0, -9.81, 0))
        ground = self.getGround()
        ground.attachGeometry(osim.Brick(osim.Vec3(0.1, 0.025, 0.1)))

        # Define the pendulum head body
        head = osim.Body('head', mass, osim.Vec3(0), inertia)
        head.attachGeometry(osim.Sphere(0.05))
        self.addBody(head)

        # Define the pin joint connecting the head to the ground
        joint_name = 'head_joint'
        parent_physical_frame = ground
        location_in_parent = osim.Vec3(0, 0, 0)
        orientation_in_parent = osim.Vec3(0, 0, 0)
        child_physical_frame = head
        location_in_child = osim.Vec3(0, length, 0)
        orientation_in_child = osim.Vec3(0, 0, 0)

        joint = osim.PinJoint(
            joint_name,
            parent_physical_frame,
            location_in_parent,
            orientation_in_parent,
            child_physical_frame,
            location_in_child,
            orientation_in_child
        )

        self.addJoint(joint)

        # Define Coordinate
        coord = joint.updCoordinate()
        coord.setName('q')
        coord.setDefaultValue(0)
        coord.setDefaultSpeedValue(0)

        # Define Coordinate Actuator
        act = osim.CoordinateActuator()
        act.setName('torque_actuator')
        act.setCoordinate(coord)
        act.setOptimalForce(1)
        act.setMinControl(-1e6)
        act.setMaxControl(1e6)
        self.addForce(act)

        # Define controller
        func = osim.Constant(0)
        controller = osim.PrescribedController()
        controller.setName('controller')
        controller.addActuator(act)
        controller.prescribeControlForActuator('torque_actuator', func)
        self.addController(controller)

        # Finalize the model
        self.finalizeConnections()
        state = self.initSystem()
        act.overrideActuation(state, True)

        self.realizePosition(state)
        self.realizeVelocity(state)
        self.realizeAcceleration(state)
        self.realizeDynamics(state)

        # Initialize the Simulation manager
        manager = osim.Manager(self)
        manager.setIntegratorAccuracy(1e-6)
        manager.initialize(state)

        # Store references for later use
        self.state = state
        self.manager = manager
        self.act = act
        self.coord = coord

    def get_q(self):
        return self.coord.getValue(self.state)
    
    def get_omega(self):
        return self.coord.getSpeedValue(self.state)
    
    def set_torque(self, torque: float):
        self.act.setOverrideActuation(self.state, torque)
        self.realizeDynamics(self.state)
        self.realizeAcceleration(self.state)
    
    def do_step(self, t, h):
        self.state = self.manager.integrate(t + h)
        self.realizePosition(self.state)
        self.realizeVelocity(self.state)
        self.realizeAcceleration(self.state)
        self.realizeDynamics(self.state)

    def save(self, filename: str):
        self.printToXML(filename)
