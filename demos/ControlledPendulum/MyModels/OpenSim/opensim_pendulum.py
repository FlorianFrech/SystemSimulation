from pyexpat import model
import opensim as osim
import numpy as np
from typing import Dict, Any, Optional

from SysSimX.core.port import PortSpec, PortType, PortState
from SysSimX.core.base import CoSimComponent
from SysSimX.components.opensim_comp import OpenSimComponent
from SysSimX.utilities.units import ureg, Quantity

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
MODEL_PARAMETERS = {
    "mass": 1.0,                # Mass of the pendulum head (kg)
    "r_head": 0.025,            # Radius of the pendulum head (m)
    "length": 0.4,              # Length of the pendulum rod (m)
    "use_gravity": False,       # Enable/disable gravity
}

CONTACT_PARAMETERS = {
    "with_contact": False,      # Enable/disable contact forces
    "stiffness": 1e6,           # Contact stiffness (N/m)
    "dissipation": 0.5,         # Contact dissipation
    "static_friction": 0.9,     # Static friction coefficient
    "dynamic_friction": 0.9,    # Dynamic friction coefficient
    "viscous_friction": 0.6     # Viscous friction coefficient
}

INITIAL_CONDITIONS = {
    "q0": 0.0,                  # Initial angle of the pendulum (rad)
    "omega0": 0.0,              # Initial angular velocity (rad/s)
}

SOLVER_PARAMETERS = {
    "internal_dt": 1e-4,         # Internal time step for OpenSim integrator (s)
    "IntegratorMethod": osim.Manager.IntegratorMethod_RungeKuttaMerson, # Integrator method
    "accuracy": 1e-6            # Integrator accuracy
}

PARAMETERS = {'Model': MODEL_PARAMETERS,
              'Contact': CONTACT_PARAMETERS,
              'InitialConditions': INITIAL_CONDITIONS,
              'Solver': SOLVER_PARAMETERS}

#----------------------------------------------------------------------------
# Pendulum OpenSim component
#---------------------------------------------------------------------------- 
class OpenSimPendulum(OpenSimComponent):
    """
    Simple 1-DOF OpenSim pendulum model.
    """
    def __init__(self, name: str = 'opensim_pendulum', group: Optional[str] = None):
        super().__init__(name=name, osim_model_path="", group=group)

        # Define input and output specifications
        self.input_specs = INPUT_SPECS
        self.output_specs = OUTPUT_SPECS
        self._initialize_ports_from_specs()

        # Model parameters
        self.parameters = PARAMETERS

        # Configure base class integrator settings
        self.internal_dt = self.parameters['Solver']['internal_dt']
        self.integrator_method = self.parameters['Solver']['IntegratorMethod']
        self.integrator_accuracy = self.parameters['Solver']['accuracy']
        
        # Pendulum-specific flags
        self._with_contact = self.parameters['Contact']['with_contact']
        self._use_gravity = self.parameters['Model']['use_gravity']

        # Will be set during build
        self.coord: Optional[osim.Coordinate] = None
        self.actuator: Optional[osim.CoordinateActuator] = None

    #----------------------------------------------------------------------------
    # Initialization method
    #----------------------------------------------------------------------------
    def _initialize_component(self, t0):
        pass

    def initialize(self, t0: float) -> None:
        # Build the OpenSim model
        self._build()

        # Get the state
        self.state = self.model.initSystem()

        # Allow direct actuation override
        self.actuator.overrideActuation(self.state, True)
        self.actuator.setOverrideActuation(self.state, 0.0)

        # Realize model to dynamics
        self.realize()

        # Manager for time integration
        self.manager = osim.Manager(self.model)
        self.manager.setIntegratorMethod(self.parameters['Solver']['IntegratorMethod'])
        self.manager.setIntegratorAccuracy(self.parameters['Solver']['accuracy'])
        self.manager.initialize(self.state)
        self.state.setTime(t0)
    
    def _build(self):
        # Get parameters
        mp = self.parameters['Model']
        cp = self.parameters['Contact']
        ic = self.parameters['InitialConditions']

        # Create model
        model = osim.Model()
        model.setName(self.name)
        if self._use_gravity:
            model.setGravity(osim.Vec3(0, -9.81, 0))
        else:
            model.setGravity(osim.Vec3(0, 0, 0))

        # Get the ground - fixed reference frame
        ground = model.getGround()

        # Create pendulum base and attach geometry
        base_name = 'pendulum_base'
        base_mass = 1 
        base_com = osim.Vec3(0, 0, 0)
        base_inertia = osim.Inertia(0, 0, 0)
        base = osim.Body(base_name, base_mass, base_com, base_inertia)
        base_geom = osim.Brick(osim.Vec3(0.1, 0.01, 0.1))
        base_geom.setColor(osim.Vec3(0.8, 0.2, 0.2))
        base.attachGeometry(base_geom)
        model.addBody(base)

        # Create weld joint to fix base to ground
        ground_translation = osim.Vec3(0, 1.2 * mp['length'], 0)
        ground_orientation = osim.Vec3(0, 0, 0)
        base_translation = osim.Vec3(0, 0, 0)
        base_orientation = osim.Vec3(0, 0, 0)
        base_to_ground = osim.WeldJoint('base_to_ground',
                                        ground, ground_translation, ground_orientation,
                                        base, base_translation, base_orientation)
        model.addJoint(base_to_ground)

        # Add pendulum head body and attach sphere geometry
        head_name = 'pendulum_head'
        head_mass = mp['mass']
        head_com = osim.Vec3(0, 0, 0)
        head_inertia = osim.Inertia(0.0, 0.0, 0.0)
        head = osim.Body(head_name, head_mass, head_com, head_inertia)
        head_geom = osim.Sphere(0.025)
        head_geom.setColor(osim.Vec3(0.2, 0.2, 0.8))
        head.attachGeometry(head_geom)
        model.addBody(head)

        # Create pin joint to connect head to base
        l = mp['length']
        base_translation = osim.Vec3(0, 0, 0)
        base_orientation = osim.Vec3(0, 0, 0)
        head_translation = osim.Vec3(0, l, 0)
        head_orientation = osim.Vec3(0, 0, 0)
        head_to_base = osim.PinJoint('head_to_base',
                                    base, base_translation, base_orientation,
                                    head, head_translation, head_orientation)
        model.addJoint(head_to_base)

        # Get the coordinate and set initial conditions
        self.q0 = ic['q0']
        self.omega0 = ic['omega0']
        coord = head_to_base.getCoordinate()
        coord.setName('q')
        coord.setDefaultValue(self.q0)
        coord.setDefaultSpeedValue(self.omega0)
        self.coord = coord

        # Add coordinate actuator to apply torque
        actuator = osim.CoordinateActuator()
        actuator.setName('torque')
        actuator.setCoordinate(coord)
        actuator.setOptimalForce(1)
        actuator.setMinControl(-1e6)
        actuator.setMaxControl(1e6)
        self.actuator = actuator
        model.addForce(actuator)

        # Add contact if desired
        if self._with_contact:
            # Contact spehere for head
            cs = osim.ContactSphere()
            cs.setName('head_contact')
            cs.setRadius(mp['r_head'])
            cs.connectSocket_frame(head)
            model.addContactGeometry(cs)

            # Contact half-space for wall
            wall = osim.ContactHalfSpace()
            wall.setName('wall_contact')
            wall.connectSocket_frame(base)
            wall.setOrientation(osim.Vec3(0, np.pi, 0))
            wall.setLocation(osim.Vec3(-mp['r_head'], 0, 0)) # impact for q=0 and omega < 0
            model.addContactGeometry(wall)

            # Set up contact geometry names
            geom_names = osim.StdVectorString()
            geom_names.append('wall_contact')
            geom_names.append('head_contact')

            # Create Hunt-Crossley contact force
            hcf = osim.HuntCrossleyForce()
            hcf.addGeometry('wall_contact')
            hcf.addGeometry('head_contact')
            hcf.setName('contact_force')
            hcf.setStiffness(cp['stiffness'])
            hcf.setDissipation(cp['dissipation'])
            hcf.setStaticFriction(cp['static_friction'])
            hcf.setDynamicFriction(cp['dynamic_friction'])
            hcf.setViscousFriction(cp['viscous_friction'])
            model.addForce(hcf)

        # Create rod geometry
        head_of = osim.PhysicalOffsetFrame()
        head_of.setName('head_of')
        head_of.setParentFrame(head)
        head_of.set_translation(osim.Vec3(0, 0.2, 0))
        head_of_geom = osim.Cylinder(0.01, 0.2)
        head_of_geom.setColor(osim.Vec3(0.2, 0.8, 0.2))
        head_of.attachGeometry(head_of_geom)
        head.addComponent(head_of)         

        # Finalize model connections
        model.finalizeConnections()
        self.model = model
        
    #----------------------------------------------------------------------------
    # Parameter setting method
    #----------------------------------------------------------------------------  
    def set_parameters(self, **parameters: float) -> None:
        """
        Set model parameters efficiently with single realization at the end.
        """
        params_changed = False
        
        if 'q0' in parameters:
            self.q0 = parameters['q0']
            self.coord.setValue(self.state, self.q0)
            params_changed = True
        
        if 'omega0' in parameters:
            self.omega0 = parameters['omega0']
            self.coord.setSpeedValue(self.state, self.omega0)
            params_changed = True
        
        if 'mass' in parameters:
            self.mass = parameters['model']['mass']
            self.model.updBodySet().get('head').setMass(self.mass)
            params_changed = True
        
        if 'length' in parameters:
            self.length = parameters['model']['length']
            joint = self.model.updJointSet().get('base_to_ground')
            joint.updChildFrame().setTranslation(osim.Vec3(0, self.length, 0))
            params_changed = True
        
        # Only realize once after all parameters are set
        if params_changed:
            self.realize()
    
    #----------------------------------------------------------------------------
    # State methods for setting and getting simulation state
    #----------------------------------------------------------------------------
    def set_state(self, state: Dict[str, Any], t: float) -> None:
        """
        Sets the new angular position and angular velocity of the pendulum.
        Acceleration is updated by updating the input toreque.
        """
        #------------------------------------
        q_state = state['q']['value']
        omega_state = state['omega']['value']
        torque_state = state['torque']['value']

        # Start from a clean topology/state
        self.state = self.model.initSystem()
        # Refresh handy handles (in case pointers changed)
        joint = self.model.updJointSet().get('head_to_base')
        self.coord = joint.updCoordinate()

        # Set time and the new generalized coordinate + speed
        self.state.setTime(float(t))
        self.coord.setValue(self.state, float(q_state))          # [rad]
        self.coord.setSpeedValue(self.state, float(omega_state)) # [rad/s]

        # Make sure we’re driving the torque directly (bypassing controls)
        self.actuator.overrideActuation(self.state, True)
        self.actuator.setOverrideActuation(self.state, float(torque_state))
        self.set_inputs({'torque': float(torque_state)}, t)
        
        # Realize up to dynamics so everything is consistent for the integrator
        self.realize()
        
        # Create a fresh Manager bound to this (model,state) and initialize it
        self.manager = osim.Manager(self.model)
        self.manager.setIntegratorAccuracy(1e-6)
        self.manager.initialize(self.state)

    def get_state(self) -> Dict[str, Any]:
        """
        Returns the current state of the pendulum: angle, angular velocity,
        angular acceleration, and applied torque.
        """
        self.realize()
        q_state = self.get_coordinate_value('q')
        omega_state = self.get_coordinate_speed('q')
        alpha_state = self.get_coordinate_acceleration('q')
        torque_state = float(self.actuator.getActuation(self.state))

        state = {}
        state['q'] = {'value': q_state, 'unit': 'rad'}
        state['omega'] = {'value': omega_state, 'unit': 'rad/s'}
        state['alpha'] = {'value': alpha_state, 'unit': 'rad/s^2'}
        state['torque'] = {'value': torque_state, 'unit': 'N.m'}

        return state

    #----------------------------------------------------------------------------
    # Time stepping method
    #----------------------------------------------------------------------------
    def _do_step_internal(self, t: float, dt: float):
        t_end = t + dt
        t_current = t

        while t_current < t_end:
            # Apply current input
            torque = float(self.inputs['torque'].get().magnitude if self.inputs['torque'].get() is not None else 0 )
            self.actuator.setOverrideActuation(self.state, torque)
            self.realize()

            # Integrate
            next_t = min(t_current + self.internal_dt, t_end)
            self.state = self.manager.integrate(next_t)

            # Realize after integration
            self.realize()
            t_current = next_t

    #----------------------------------------------------------------------------
    # Input/output methods
    #----------------------------------------------------------------------------
    def set_inputs(self, signals: Dict[str, Any], t: Optional[float]) -> None:
        super().set_inputs(signals, t) # Update port states

        if 'torque' in signals:
            value = signals['torque']
            if isinstance(value, Quantity):
                value = value.magnitude
            self.actuator.setOverrideActuation(self.state, value)
            self.realize()

    def get_outputs(self) -> Dict[str, float]:
        return {name: out_port.get() for name, out_port in self.outputs.items()}

    def _update_output_states(self, t: float) -> None:
        for name, out_port in self.outputs.items():
            if name == 'q':
                value = float(self.coord.getValue(self.state))
                value = self.get_coordinate_value('q')
                out_port.set(value * ureg("rad"), t=t)
            elif name == 'omega':
                value = float(self.coord.getSpeedValue(self.state))
                value = self.get_coordinate_speed('q')
                out_port.set(value * ureg("rad/s"), t=t)
            elif name == 'alpha':
                value = float(self.coord.getAccelerationValue(self.state))
                value = self.get_coordinate_acceleration('q')
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
    
    #----------------------------------------------------------------------------
    # Save XML file
    #----------------------------------------------------------------------------
    def save_model(self, file_path: str="MyOpenSimPendulum.osim") -> None:
        """
        Save the OpenSim model to an XML file.
        """
        if self.model is not None:
            self.model.printToXML(file_path)
        else:
            raise RuntimeError("Model is not built yet. Cannot save XML.")