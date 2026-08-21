from typing import Any

import opensim as osim

from ..core.base import CoSimComponent


class OpenSimComponent(CoSimComponent):
    """
    Wrapper around an OpenSim model to implement the CoSimComponent interface.
    """

    model: osim.Model
    manager: osim.Manager
    state: osim.State

    parameters: dict[str, Any] = {}

    def __init__(self, name: str, osim_model_path: str, group: str | None = None):
        """
        Constructor for the OpenSimComponent class.
        """
        CoSimComponent.__init__(self, name=name, group=group)
        self.path = osim_model_path

        # Populated by subclass
        self.model: osim.Model | None = None
        self.state: osim.State | None = None
        self.manager: osim.Manager | None = None

        # Default Solver Parameters
        self.integrator_method = osim.Manager.IntegratorMethod_RungeKuttaMerson
        self.integrator_accuracy = 1e-6
        self.internal_dt = 1e-4

    def _finalize_model(self, t0: float) -> None:
        """
        Complete OpenSim initialization after model is built/loaded.
        Call this at the end of subclass _initialize_component().
        """
        # Realize to ensure model is ready
        self.realize()

        # Create and initialize manager
        self.manager = osim.Manager(self.model)
        self.manager.setIntegratorMethod(self.integrator_method)
        self.manager.setIntegratorAccuracy(self.integrator_accuracy)
        self.manager.initialize(self.state)
        self.state.setTime(t0)

    def realize(self) -> None:
        """
        Realizes the stage: Position, Velocity, Dynamics, Acceleration
        """
        if self.state is None:
            raise RuntimeError(f"{self.name}: state not initialized")
        self.model.realizeAcceleration(self.state)

    # ---- Reset ----
    def reset(self) -> None:
        """
        Reset the component to a clean state before (before initialization).
        """
        super().reset()
        if self.model is None:
            self.state = None
            self.manager = None
            return
        self.state = self.model.initSystem()
        self.manager = osim.Manager(self.model)

    # ---- Coordinate Helpers ----
    def get_coordinate_value(self, coord_name: str) -> float:
        """Get current value of named coordinate (generalized position)."""
        coord = self._find_coordinate(coord_name)
        return float(coord.getValue(self.state))

    def get_coordinate_speed(self, coord_name: str) -> float:
        """Get current speed of named coordinate (generalized velocity)."""
        coord = self._find_coordinate(coord_name)
        return float(coord.getSpeedValue(self.state))

    def get_coordinate_acceleration(self, coord_name: str) -> float:
        """Get current acceleration of named coordinate."""
        coord = self._find_coordinate(coord_name)
        return float(coord.getAccelerationValue(self.state))

    def set_coordinate_value(self, coord_name: str, value: float) -> None:
        """Set value of named coordinate."""
        coord = self._find_coordinate(coord_name)
        coord.setValue(self.state, float(value))

    def set_coordinate_speed(self, coord_name: str, value: float) -> None:
        """Set speed of named coordinate."""
        coord = self._find_coordinate(coord_name)
        coord.setSpeedValue(self.state, float(value))

    def _find_coordinate(self, name: str) -> osim.Coordinate:
        """Find coordinate by name in model."""
        coord_set = self.model.getCoordinateSet()
        for i in range(coord_set.getSize()):
            coord = coord_set.get(i)
            if coord.getName() == name:
                return coord
        raise KeyError(f"Coordinate '{name}' not found in model '{self.name}'")
