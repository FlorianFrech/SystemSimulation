import opensim as osim
import numpy as np
from typing import Dict, Any, Optional

from SysSimX.core.port import PortSpec, PortType, PortState
from SysSimX.core.base import CoSimComponent
from SysSimX.core.opensim_comp import OpenSimComponent
from SysSimX.utilities.units import ureg

#----------------------------------------------------------------------------
# Port specifications
#----------------------------------------------------------------------------   
INPUT_SPECS = {
    "torque": PortSpec("torque", PortType.REAL, direction="in", unit=ureg("N*m").units)
}

OUTPUT_SPECS = {
    "q": PortSpec("q", PortType.REAL, direction="out", unit=ureg("rad").units),
    "omega": PortSpec("omega", PortType.REAL, direction="out", unit=ureg("rad/s").units),
    "alpha": PortSpec("alpha", PortType.REAL, direction="out", unit=ureg("rad/s^2").units)
}
#----------------------------------------------------------------------------
# Parameters
#----------------------------------------------------------------------------
PARAMETERS = {
    "mass": 80*0.2,                # Mass of the pendulum head (kg)
    "length": 0.4,                 # Length of the pendulum rod (m)
    "q0": 0,                        # Initial angle of the pendulum (rad)
    "omega0": 0.0,                  # Initial angular velocity (rad/s)
    "internal_dt": 1e-4             # Internal time step for OpenSim integrator (s)
}

#----------------------------------------------------------------------------
# Pendulum OpenSim component
#---------------------------------------------------------------------------- 
class OpenSimPendulum(OpenSimComponent):
    """
    Simple 1-DOF OpenSim pendulum model.
    """
    def __init__(self, name: str = 'opensim_pendulum'):
        super().__init__(name=name, osim_model_path="", group="")

        # Define input and output specifications
        self.input_specs = INPUT_SPECS
        self.output_specs = OUTPUT_SPECS
        
        # Initialize port states based on specifications
        for spec in self.input_specs.values():
            self.inputs[spec.name] = PortState(spec)
        for spec in self.output_specs.values():
            self.outputs[spec.name] = PortState(spec)

        # Model parameters
        self.parameters = PARAMETERS

        self._int_dt = self.parameters['internal_dt']

        self._with_contact = False
        self._use_gravity = False    
    #----------------------------------------------------------------------------
    # Initialization method
    #----------------------------------------------------------------------------  
    def initialize(self, t0: float) -> None:
        self.model, self.state, self.coord, self.actuator, self.manager = self._build()
        self.state.setTime(t0)
    
    def _build(self):
        # Model construction
        model = osim.Model()
        model.setName(self.name)

        # Gravity setting
        if self._use_gravity:
            model.setGravity(osim.Vec3(0, -9.81, 0))
        else:
            model.setGravity(osim.Vec3(0, 0, 0))

        # Ground Body
        ground = model.getGround()
        ground.attachGeometry(osim.Brick(osim.Vec3(0.1, 0.025, 0.1)))
        
        # Pendulum Head Body
        head = osim.Body('head', self.parameters['mass'], osim.Vec3(0), osim.Inertia(0, 0, 0))
        head.attachGeometry(osim.Sphere(0.05))
        model.addBody(head)

        # Pin Joint between Ground and Head
        joint = osim.PinJoint('hinge',
                               ground, osim.Vec3(0, 0, 0), osim.Vec3(0, 0, 0),
                               head, osim.Vec3(0, self.parameters['length'], 0), osim.Vec3(0, 0, 0))
        model.addJoint(joint)

        # Joint Coordinate setup
        coord = joint.updCoordinate()
        coord.setName('q')
        coord.setDefaultValue(self.parameters['q0'])
        coord.setDefaultSpeedValue(self.parameters['omega0'])
        coord.setRangeMin(-np.pi); coord.setRangeMax(np.pi)

        # Torque Actuator Setup
        actuator = osim.CoordinateActuator()
        actuator.setName('torque_actuator')
        actuator.setCoordinate(coord)
        actuator.setOptimalForce(1)
        actuator.setMinControl(-1e6)
        actuator.setMaxControl(1e6)
        model.addForce(actuator)

        # Controller Setup - Direct Torque Control
        controller_function = osim.Constant(0)
        controller = osim.PrescribedController()
        controller.setName('controller')
        controller.addActuator(actuator)
        controller.prescribeControlForActuator('torque_actuator', controller_function)
        model.addController(controller)

        # Finalize model connections
        model.finalizeConnections()
        state = model.initSystem()

        # Allow direct actuation override
        actuator.overrideActuation(state, True)

        # Realize model to dynamics
        model.realizePosition(state)
        model.realizeVelocity(state)
        model.realizeAcceleration(state)
        model.realizeDynamics(state)

        # Manager for time integration
        manager = osim.Manager(model)
        manager.setIntegratorMethod(osim.Manager.IntegratorMethod_RungeKuttaMerson) # Adaptive Time Step
        manager.setIntegratorAccuracy(1e-6)
        manager.initialize(state)

        return model, state, coord, actuator, manager
    
    #----------------------------------------------------------------------------
    # Parameter setting method
    #----------------------------------------------------------------------------  
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
    
    #----------------------------------------------------------------------------
    # State methods for setting and getting simulation state
    #----------------------------------------------------------------------------
    def set_state(self, state: Dict[str, Any], t: float) -> None:
        """
        Sets the new angular position and angular velocity of the pendulum.
        Acceleration is updated by updating the input toreque.
        """
        q_state = state['q']['value']
        omega_state = state['omega']['value']
        torque_state = state['torque']['value']

        # Start from a clean topology/state
        self.state = self.model.initSystem()
        # Refresh handy handles (in case pointers changed)
        joint = self.model.updJointSet().get('hinge')
        self.coord = joint.updCoordinate()

        # Set time and the new generalized coordinate + speed
        self.state.setTime(float(t))
        self.coord.setValue(self.state, float(q_state))          # [rad]
        self.coord.setSpeedValue(self.state, float(omega_state)) # [rad/s]

        # Make sure we’re driving the torque directly (bypassing controls)
        self.actuator.overrideActuation(self.state, True)
        self.actuator.setOverrideActuation(self.state, torque_state)
        
        # Realize up to dynamics so everything is consistent for the integrator
        self.model.realizePosition(self.state)
        self.model.realizeVelocity(self.state)
        self.model.realizeAcceleration(self.state)
        self.model.realizeDynamics(self.state)

        # Create a fresh Manager bound to this (model,state) and initialize it
        self.manager = osim.Manager(self.model)
        self.manager.setIntegratorAccuracy(1e-6)
        self.manager.initialize(self.state)

    def get_state(self):
        q_state = float(self.coord.getValue(self.state))
        omega_state = float(self.coord.getSpeedValue(self.state))
        torque_state = self.actuator.getActuation(self.state)

        state = {}
        state['q'] = {'value': q_state, 'unit': 'rad'}
        state['omega'] = {'value': omega_state, 'unit': 'rad/s'}
        state['torque'] = {'value': torque_state, 'unit': 'N*m'}

        return state

    #----------------------------------------------------------------------------
    # Time stepping method
    #----------------------------------------------------------------------------
    def do_step(self, t: float, h: float) -> None:
        t_end = t + h
        i = 0
        while t < t_end:
            current_torque = self.inputs['torque'].get().magnitude
            self.actuator.setOverrideActuation(self.state, current_torque)
            self.model.realizeDynamics(self.state)
            self.model.realizeAcceleration(self.state)

            self.state = self.manager.integrate(t + self._int_dt)
            self.model.realizePosition(self.state)
            self.model.realizeVelocity(self.state)
            self.model.realizeAcceleration(self.state)
            self.model.realizeDynamics(self.state)
            self._update_output_states(t)
            t += self._int_dt
            i = i + 1

    #----------------------------------------------------------------------------
    # Input/output methods
    #----------------------------------------------------------------------------
    def set_inputs(self, signals: Dict[str, Any], t: Optional[float]) -> None:
        if not signals:
            return
        for name, value in signals.items():
            if name not in self.inputs:
                raise KeyError(f"Input '{name}' not found in inputs.")
            port_state = self.inputs[name]
            unit = self.input_specs[name].unit
            port_state.set(value * unit, t=t)
            if name == 'torque':
                self.actuator.setOverrideActuation(self.state, value)
                self.model.realizeDynamics(self.state)
                self.model.realizeAcceleration(self.state)

    def get_outputs(self) -> Dict[str, float]:
        return {name: out_port.get() for name, out_port in self.outputs.items()}

    def _update_output_states(self, t: float) -> None:
        for name, out_port in self.outputs.items():
            if name == 'q':
                value = float(self.coord.getValue(self.state))
                out_port.set(value * ureg("rad"), t=t)
            elif name == 'omega':
                value = float(self.coord.getSpeedValue(self.state))
                out_port.set(value * ureg("rad/s"), t=t)
            elif name == 'alpha':
                value = float(self.coord.getAccelerationValue(self.state))
                out_port.set(value * ureg("rad/s^2"), t=t)

    #----------------------------------------------------------------------------
    # Reset method
    #----------------------------------------------------------------------------
    def reset(self) -> None:
        self.model = None
        self.state = None
        self.coord = None
        self.actuator = None
        self.manager = None
        self.model, self.state, self.coord, self.actuator, self.manager = self._build()



