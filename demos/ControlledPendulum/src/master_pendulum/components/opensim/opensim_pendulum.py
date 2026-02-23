from typing import Any

import numpy as np
import opensim as osim

from syssimx.components.opensim import OpenSimComponent
from syssimx.core.port import PortSpec, PortType
from syssimx.utilities.units import Quantity, ureg

# ----------------------------------------------------------------------------
# Port specifications
# ----------------------------------------------------------------------------
INPUT_SPECS = {
    "tau": PortSpec("tau", PortType.REAL, direction="in", unit=ureg("N.m").units),
    "omega_invert": PortSpec("omega_invert", PortType.EVENT, direction="in"),
}

OUTPUT_SPECS = {
    "theta": PortSpec("theta", PortType.REAL, direction="out", unit=ureg("rad").units),
    "omega": PortSpec("omega", PortType.REAL, direction="out", unit=ureg("rad/s").units),
    "alpha": PortSpec("alpha", PortType.REAL, direction="out", unit=ureg("rad/s^2").units),
}

# ----------------------------------------------------------------------------
# Parameters
# ----------------------------------------------------------------------------
MODEL_PARAMETERS = {
    "mass": 1.0,  # Mass of the pendulum head (kg)
    "r_head": 0.025,  # Radius of the pendulum head (m)
    "length": 0.4,  # Length of the pendulum rod (m)
    "inertia": 0.01,  # Moment of inertia of the pendulum head (kg.m^2)
    "use_gravity": True,  # Enable/disable gravity
}

CONTACT_PARAMETERS = {
    "with_contact": False,  # Enable/disable contact forces
    "stiffness": 1e12,  # Contact stiffness (N/m)
    "dissipation": 0.0,  # Contact dissipation
    "static_friction": 0.0,  # Static friction coefficient
    "dynamic_friction": 0.0,  # Dynamic friction coefficient
    "viscous_friction": 0.0,  # Viscous friction coefficient
}

INITIAL_CONDITIONS = {
    "theta_start": 0.0,  # Initial angle of the pendulum (rad)
    "omega_start": 0.0,  # Initial angular velocity of the pendulum (rad/s)
}

SOLVER_PARAMETERS = {
    "internal_dt": 1e-4,  # Internal time step for OpenSim integrator (s)
    "IntegratorMethod": osim.Manager.IntegratorMethod_RungeKuttaMerson,  # Integrator method
    "accuracy": 1e-6,  # Integrator accuracy
}

PARAMETERS = {
    "Model": MODEL_PARAMETERS,
    "Contact": CONTACT_PARAMETERS,
    "InitialConditions": INITIAL_CONDITIONS,
    "Solver": SOLVER_PARAMETERS,
}


# ----------------------------------------------------------------------------
# Pendulum OpenSim component
# ----------------------------------------------------------------------------
class OpenSimPendulum(OpenSimComponent):
    """
    Simple 1-DOF OpenSim pendulum model.
    """

    def __init__(self, name: str = "opensim_pendulum", group: str | None = None):
        super().__init__(name=name, osim_model_path="", group=group)

        # Define input and output specifications
        self.input_specs.update(INPUT_SPECS)
        self.output_specs.update(OUTPUT_SPECS)

        # Model parameters
        self.parameters.update(PARAMETERS)

        # Configure base class integrator settings
        self.internal_dt = self.parameters["Solver"]["internal_dt"]
        self.integrator_method = self.parameters["Solver"]["IntegratorMethod"]
        self.integrator_accuracy = self.parameters["Solver"]["accuracy"]

        # Pendulum-specific flags
        self._with_contact = self.parameters["Contact"]["with_contact"]
        self._use_gravity = self.parameters["Model"]["use_gravity"]

        # Will be set during build
        self.coord: osim.Coordinate | None = None
        self.actuator: osim.CoordinateActuator | None = None

    # ----------------------------------------------------------------------------
    # Initialization method
    # ----------------------------------------------------------------------------
    def _initialize_component(self, t0: float):
        self._build()

        # Get the state
        self.state = self.model.initSystem()

        # Allow direct actuation override
        self.actuator.overrideActuation(self.state, True)

        # Finalize model setup
        self._finalize_model(t0)

        self.realize()
        self._update_output_states(None)

    # ----------------------------------------------------------------------------
    # Initialization helper - build the OpenSim model
    # ----------------------------------------------------------------------------
    def _build(self):
        # Get parameters
        mp = self.parameters["Model"]
        cp = self.parameters["Contact"]
        ic = self.parameters["InitialConditions"]

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
        base_name = "pendulum_base"
        base_mass = 1
        base_com = osim.Vec3(0, 0, 0)
        base_inertia = osim.Inertia(0, 0, 0)
        base = osim.Body(base_name, base_mass, base_com, base_inertia)
        base_geom = osim.Brick(osim.Vec3(0.1, 0.01, 0.1))
        base_geom.setColor(osim.Vec3(0.8, 0.2, 0.2))
        base.attachGeometry(base_geom)
        model.addBody(base)

        # Create weld joint to fix base to ground
        ground_translation = osim.Vec3(0, 1.2 * mp["length"], 0)
        ground_orientation = osim.Vec3(0, 0, 0)
        base_translation = osim.Vec3(0, 0, 0)
        base_orientation = osim.Vec3(0, 0, 0)
        base_to_ground = osim.WeldJoint(
            "base_to_ground",
            ground,
            ground_translation,
            ground_orientation,
            base,
            base_translation,
            base_orientation,
        )
        model.addJoint(base_to_ground)

        # Add pendulum head body and attach sphere geometry
        head_name = "pendulum_head"
        head_mass = mp["mass"]
        head_com = osim.Vec3(0, 0, 0)
        inertia = mp["inertia"]
        head_inertia = osim.Inertia(0, 0, inertia)  # About z-axis
        head = osim.Body(head_name, head_mass, head_com, head_inertia)
        head_geom = osim.Sphere(mp["r_head"])
        head_geom.setColor(osim.Vec3(0.2, 0.2, 0.8))
        head.attachGeometry(head_geom)
        model.addBody(head)

        # Create pin joint to connect head to base
        l = mp["length"]
        base_translation = osim.Vec3(0, 0, 0)
        base_orientation = osim.Vec3(0, 0, 0)
        head_translation = osim.Vec3(0, l, 0)
        head_orientation = osim.Vec3(0, 0, 0)
        head_to_base = osim.PinJoint(
            "head_to_base",
            base,
            base_translation,
            base_orientation,
            head,
            head_translation,
            head_orientation,
        )
        model.addJoint(head_to_base)

        # Get the coordinate and set initial conditions
        self.theta_start = ic["theta_start"]
        self.omega_start = ic["omega_start"]
        coord = head_to_base.getCoordinate()
        coord.setName("theta")
        coord.setDefaultValue(self.theta_start)
        coord.setDefaultSpeedValue(self.omega_start)
        self.coord = coord

        # Add coordinate actuator to apply torque
        actuator = osim.CoordinateActuator()
        actuator.setName("tau")
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
            cs.setName("head_contact")
            cs.setRadius(mp["r_head"])
            cs.connectSocket_frame(head)
            model.addContactGeometry(cs)

            # Contact half-space for wall
            wall = osim.ContactHalfSpace()
            wall.setName("wall_contact")
            wall.connectSocket_frame(base)
            wall.setOrientation(osim.Vec3(0, np.pi, 0))
            wall.setLocation(osim.Vec3(-mp["r_head"], 0, 0))  # impact for q=0 and omega < 0
            model.addContactGeometry(wall)

            # Set up contact geometry names
            geom_names = osim.StdVectorString()
            geom_names.append("wall_contact")
            geom_names.append("head_contact")

            # Create Hunt-Crossley contact force
            hcf = osim.HuntCrossleyForce()
            hcf.addGeometry("wall_contact")
            hcf.addGeometry("head_contact")
            hcf.setName("contact_force")
            hcf.setStiffness(cp["stiffness"])
            hcf.setDissipation(cp["dissipation"])
            hcf.setStaticFriction(cp["static_friction"])
            hcf.setDynamicFriction(cp["dynamic_friction"])
            hcf.setViscousFriction(cp["viscous_friction"])
            model.addForce(hcf)

        # Create rod geometry
        head_of = osim.PhysicalOffsetFrame()
        head_of.setName("head_of")
        head_of.setParentFrame(head)
        head_of.set_translation(osim.Vec3(0, l/2, 0))
        head_of_geom = osim.Cylinder(0.01, l/2)
        head_of_geom.setColor(osim.Vec3(0.2, 0.8, 0.2))
        head_of.attachGeometry(head_of_geom)
        head.addComponent(head_of)

        # Finalize model connections
        model.finalizeConnections()
        self.model = model

    # ----------------------------------------------------------------------------
    # State methods for setting and getting simulation state
    # ----------------------------------------------------------------------------
    def set_state(self, state: dict[str, Any], t: float) -> None:
        """
        Sets the new angular position and angular velocity of the pendulum.
        Acceleration is updated by updating the input toreque.
        """
        # ------------------------------------
        theta_state = state["theta"]["value"]
        omega_state = state["omega"]["value"]
        tau_state = state["tau"]["value"]

        # Start from a clean topology/state
        self.state = self.model.initSystem()

        # Refresh handy handles (in case pointers changed)
        joint = self.model.updJointSet().get("head_to_base")
        self.coord = joint.updCoordinate()

        # Set time and the new generalized coordinate + speed
        self.state.setTime(float(t))
        self.coord.setValue(self.state, float(theta_state))  # [rad]
        self.coord.setSpeedValue(self.state, float(omega_state))  # [rad/s]

        # Update the applied torque
        self.actuator.overrideActuation(self.state, True)
        self.actuator.setOverrideActuation(self.state, float(tau_state))
        self.set_inputs({"tau": float(tau_state)}, t)

        # Create a fresh Manager bound to this (model,state) and initialize it
        self.manager = osim.Manager(self.model)
        self.manager.setIntegratorAccuracy(self.integrator_accuracy)
        self.manager.initialize(self.state)

        # Realize for consistency
        self.realize()

    def get_state(self) -> dict[str, Any]:
        """
        Returns the current state of the pendulum: angle, angular velocity,
        angular acceleration, and applied torque.
        """
        self.realize()
        theta_state = self.get_coordinate_value("theta")
        omega_state = self.get_coordinate_speed("theta")
        alpha_state = self.get_coordinate_acceleration("theta")
        tau_state = float(self.actuator.getActuation(self.state))

        state = {}
        state["theta"] = {"value": theta_state, "unit": "rad"}
        state["omega"] = {"value": omega_state, "unit": "rad/s"}
        state["alpha"] = {"value": alpha_state, "unit": "rad/s^2"}
        state["tau"] = {"value": tau_state, "unit": "N.m"}
        return state

    # ----------------------------------------------------------------------------
    # Hybrid methods for snapshot/restore and event handling
    # ----------------------------------------------------------------------------
    def snapshot_state(self):
        state = self.get_state()
        state["time"] = {"value": self.state.getTime(), "unit": "s"}
        state["mode"] = "OpenSim"
        return state

    def restore_state(self, snapshot, t):
        if snapshot.get("mode", "") != "OpenSim":
            raise ValueError(
                f"[{self.name}] Incompatible snapshot mode, got '{snapshot.get('mode', '')}'."
            )
        self.set_state(snapshot, t)

    def _handle_events_internal(self, event_names, t):
        if "wall_hit" not in event_names:
            return

        print(f"[{self.name}] Event 'wall_hit' at t={t:.4f}s: Inverting velocity")

        # Invert angular velocity
        omega_new = -1 * self.get_coordinate_speed("theta")
        self.coord.setSpeedValue(self.state, omega_new)
        self.realize()

    # ----------------------------------------------------------------------------
    # Time stepping method
    # ----------------------------------------------------------------------------
    def _do_step_internal(self, t: float, dt: float):
        t_end = t + dt
        t_current = t

        while t_current < t_end:
            # Apply current input
            torque = float(
                self.inputs["tau"].get().magnitude
                if self.inputs["tau"].get() is not None
                else 0
            )
            self.actuator.setOverrideActuation(self.state, torque)
            self.realize()

            # Integrate
            next_t = min(t_current + self.internal_dt, t_end)
            self.state = self.manager.integrate(next_t)

            # Realize after integration
            self.realize()
            t_current = next_t

    # ----------------------------------------------------------------------------
    # Input/output methods
    # ----------------------------------------------------------------------------
    def set_inputs(self, signals: dict[str, Any], t: float | None = None) -> None:
        super().set_inputs(signals, t)  # Update port states

        if "tau" in signals:
            value = signals["tau"]
            if isinstance(value, Quantity):
                value = value.magnitude
            self.actuator.setOverrideActuation(self.state, value)
            self.realize()
            self._update_output_states(t)

    def get_outputs(self) -> dict[str, float]:
        return {name: out_port.get() for name, out_port in self.outputs.items()}

    def _update_output_states(
        self, t: float | None = None, event_names: list[str] | None = []
    ) -> None:
        for name, out_port in self.outputs.items():
            if name == "theta":
                value = float(self.coord.getValue(self.state))
                value = self.get_coordinate_value("theta")
                out_port.set(value * ureg("rad"), t=t)
            elif name == "omega":
                value = float(self.coord.getSpeedValue(self.state))
                value = self.get_coordinate_speed("theta")
                out_port.set(value * ureg("rad/s"), t=t)
            elif name == "alpha":
                value = float(self.coord.getAccelerationValue(self.state))
                value = self.get_coordinate_acceleration("theta")
                out_port.set(value * ureg("rad/s^2"), t=t)
        # Hybrid event outputs
        if event_names:
            for event_name in event_names:
                if event_name in self.output_specs.keys():
                    self.outputs[event_name].set(True, t=t)
        else:
            for out_port in self.outputs.values():
                if out_port.spec.type == PortType.EVENT:
                    out_port.set(False, t=t)

    # ----------------------------------------------------------------------------
    # Reset method
    # ----------------------------------------------------------------------------
    def reset(self) -> None:
        super().reset()
        self.coord = None
        self.actuator = None
        self.manager = None

    # ----------------------------------------------------------------------------
    # Save XML file
    # ----------------------------------------------------------------------------
    def save_model(self, file_path: str = "MyOpenSimPendulum.osim") -> None:
        """
        Save the OpenSim model to an XML file.
        """
        if self.model is not None:
            self.model.printToXML(file_path)
        else:
            raise RuntimeError("Model is not built yet. Cannot save XML.")
