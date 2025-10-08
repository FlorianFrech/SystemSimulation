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
        """
        Set model parameters efficiently with single realization at the end.
        """
        params_changed = False
        
        if 'q0' in parameters:
            self.coord.setValue(self.state, parameters['q0'])
            params_changed = True
        
        if 'omega0' in parameters:
            self.coord.setSpeedValue(self.state, parameters['omega0'])
            params_changed = True
        
        if 'mass' in parameters:
            self.mass = parameters['mass']
            self.model.updBodySet().get('head').setMass(self.mass)
            params_changed = True
        
        if 'length' in parameters:
            self.length = parameters['length']
            joint = self.model.updJointSet().get('hinge')
            joint.updChildFrame().setTranslation(osim.Vec3(0, self.length, 0))
            params_changed = True
        
        if 'inertia' in parameters:
            self.inertia = parameters['inertia']
            self.model.updBodySet().get('head').setInertia(self.inertia)
            params_changed = True
        
        # Only realize once after all parameters are set
        if params_changed:
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
        q_state = float(self.coord.getValue(self.state))
        omega_state = float(self.coord.getSpeedValue(self.state))
        return {'q_state': q_state, 'omega_state': omega_state}

    def reset(self) -> None:
        self.model = None
        self.state = None
        self.coord = None
        self.actuator = None
        self.manager = None
        self.model, self.state, self.coord, self.actuator, self.manager = self._build()


    def reinitialize(self, t: float, q_state: float, omega_state: float, rebuild: bool = False) -> None:
        """
        Reinitialize the pendulum with new state (q, omega) at simulation time t.

        Notes:
        - Uses a fresh State from initSystem() to avoid stale cache.
        - Rebuild only if structure changed (mass props, joint frames, etc.).
        """
        # Store for bookkeeping (optional)
        self.q0 = float(q_state)
        self.omega0 = float(omega_state)

        if rebuild or self.model is None:
            # Full rebuild uses defaults we set below anyway
            self.model, self.state, self.coord, self.actuator, self.manager = self._build()
        else:
            # Start from a clean topology/state
            self.state = self.model.initSystem()
            # Refresh handy handles (in case pointers changed)
            joint = self.model.updJointSet().get('hinge')
            self.coord = joint.updCoordinate()
            #self.actuator = self.model.updForceSet().get('torque_actuator').updDowncast()

        # Set time and the new generalized coordinate + speed
        self.state.setTime(float(t))
        self.coord.setValue(self.state, float(q_state))          # [rad]
        self.coord.setSpeedValue(self.state, float(omega_state)) # [rad/s]

        # Make sure we’re driving the torque directly (bypassing controls)
        self.actuator.overrideActuation(self.state, True)

        # Realize up to dynamics so everything is consistent for the integrator
        self.model.realizePosition(self.state)
        self.model.realizeVelocity(self.state)
        self.model.realizeDynamics(self.state)

        # Create a fresh Manager bound to this (model,state) and initialize it
        self.manager = osim.Manager(self.model)
        self.manager.setIntegratorAccuracy(1e-6)
        self.manager.initialize(self.state)
