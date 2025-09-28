import opensim as osim
import numpy as np
from typing import Dict

class OpenSimPendulum:
    """
    Simple 1-DOF OpenSim pendulum model.
    """
    def __init__(self, name: str = 'opensim_pendulum',
                 mass: float = 80*0.2,
                 length: float = 0.4,
                 inertia: osim.Inertia = osim.Inertia(0.1, 0.1, 0.1),
                 q0: float = -np.pi/4,
                 omega0: float = 0.0):
        """
        Constructor for the OpenSimPendulum class.
            :param name: Name of the model instance.
            :param mass: Mass of the pendulum head (kg).
            :param length: Length of the pendulum rod (m).
            :param inertia: Inertia of the pendulum head (kg*m^2).
            :param q0: Initial angle of the pendulum (rad).
        """
        self.name = name
        self.mass = mass
        self.length = length
        self.inertia = inertia
        self.q0 = q0
        self.omega0 = omega0
    
    def _build(self):
        model = osim.Model()
        model.setName(self.name)
        model.setGravity(osim.Vec3(0, -9.81, 0))

        ground = model.getGround()
        head = osim.Body('head', self.mass, osim.Vec3(0), self.inertia)
        model.addBody(head)

        joint = osim.PinJoint('hinge',
                                ground, osim.Vec3(0, 0, 0), osim.Vec3(0, 0, 0),
                                head, osim.Vec3(0, self.length, 0), osim.Vec3(0, 0, 0))
        model.addJoint(joint)

        coord = joint.updCoordinate()
        coord.setName('q')
        coord.setDefaultValue(self.q0)
        coord.setDefaultSpeedValue(self.omega0)
        coord.setRangeMin(-np.pi); coord.setRangeMax(np.pi)

        actuator = osim.CoordinateActuator()
        actuator.setName('torque_actuator')
        actuator.setCoordinate(coord)
        actuator.setOptimalForce(1)
        actuator.setMinControl(-1e6)
        actuator.setMaxControl(1e6)
        model.addForce(actuator)

        controller_function = osim.Constant(0)
        controller = osim.PrescribedController()
        controller.setName('controller')
        controller.addActuator(actuator)
        controller.prescribeControlForActuator('torque_actuator', controller_function)
        model.addController(controller)

        model.finalizeConnections()
        state = model.initSystem()
        actuator.overrideActuation(state, True)

        model.realizePosition(state)
        model.realizeVelocity(state)
        model.realizeAcceleration(state)
        model.realizeDynamics(state)

        manager = osim.Manager(model)
        manager.setIntegratorAccuracy(1e-6)
        manager.initialize(state)

        return model, state, coord, actuator, manager
    
    def initialize(self, t0: float) -> None:
        self.model, self.state, self.coord, self.actuator, self.manager = self._build()

        self.state.setTime(t0)
    
    def set_parameters(self, **parameters: float) -> None:
        if 'q0' in parameters:
            self.coord.setValue(self.state, parameters['q0'])
            self.coord.setSpeedValue(self.state, 0)
            self.model.realizePosition(self.state)
            self.model.realizeVelocity(self.state)
            self.model.realizeAcceleration(self.state)
            self.model.realizeDynamics(self.state)
        
        if 'mass' in parameters:
            self.mass = parameters['mass']
            self.model.updBodySet().get('head').setMass(self.mass)
            self.model.realizePosition(self.state)
            self.model.realizeVelocity(self.state)
            self.model.realizeAcceleration(self.state)
            self.model.realizeDynamics(self.state)
        
        if 'length' in parameters:
            self.length = parameters['length']
            joint = self.model.updJointSet().get('hinge')
            joint.updChildFrame().setTranslation(osim.Vec3(0, self.length, 0))
            self.model.realizePosition(self.state)
            self.model.realizeVelocity(self.state)
            self.model.realizeAcceleration(self.state)
            self.model.realizeDynamics(self.state)
        
        if 'inertia' in parameters:
            self.inertia = parameters['inertia']
            self.model.updBodySet().get('head').setInertia(self.inertia)
            self.model.realizePosition(self.state)
            self.model.realizeVelocity(self.state)
            self.model.realizeAcceleration(self.state)
            self.model.realizeDynamics(self.state)

    def set_inputs(self, **signals: float) -> None:
        if 'torque' in signals:
            self.actuator.setOverrideActuation(self.state, signals['torque'])
            self.model.realizeDynamics(self.state)
            self.model.realizeAcceleration(self.state)

    def step(self, t: float, h: float) -> None:
        self.state = self.manager.integrate(t + h)
        self.model.realizePosition(self.state)
        self.model.realizeVelocity(self.state)
        self.model.realizeAcceleration(self.state)
        self.model.realizeDynamics(self.state)

    def get_outputs(self) -> Dict[str, float]:
        q = float(self.coord.getValue(self.state))
        omega = float(self.coord.getSpeedValue(self.state))
        return {'q': q, 'omega': omega}

    def reset(self) -> None:
        self.model = None
        self.state = None
        self.coord = None
        self.actuator = None
        self.manager = None
        self.model, self.state, self.coord, self.actuator, self.manager = self._build()