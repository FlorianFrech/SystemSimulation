from syssimx.core.base import CoSimComponent
from syssimx.core.port import PortSpec, PortType


# ============================================================================
# Basic Components for Unit Tests
# ============================================================================
class IntegratorComponent(CoSimComponent):
    """
    An integrator component that integrates its input signal u over time.
    x(t) = x0 + ∫ u dt
    Uses unitless ports for flexible testing.
    """

    def __init__(self, name="Integrator", x0=0.0):
        super().__init__(name)

        self.input_specs.update(
            {
                "u": PortSpec(
                    name="u",
                    type=PortType.REAL,
                    direction="in",
                    unit=None,
                    description="Input signal (rate of change)",
                )
            }
        )
        self.output_specs.update(
            {
                "y": PortSpec(
                    name="y",
                    type=PortType.REAL,
                    direction="out",
                    unit=None,
                    description="Integrated output",
                )
            }
        )
        self.x0 = x0

    def _initialize_component(self, t0: float) -> None:
        """
        Initialize the integrator state.
        """
        self.x = self.x0

    def _do_step_internal(self, t: float, dt: float) -> None:
        """
        Perform a simulation step by integrating the input signal.
        """
        u = self.inputs["u"].get()
        if u is not None:
            u_val = u.magnitude if hasattr(u, "magnitude") else u
            self.x += u_val * dt

    def _update_output_states(self, t):
        """
        Update the output port states.
        """
        self.outputs["y"].set(self.x, t)

    def set_state(self, state, t):
        """
        Set the integrator state.
        """
        if isinstance(state, dict):
            self.x = state.get("x", self.x)
        else:
            self.x = state
        self._update_output_states(t)

    def get_state(self):
        """
        Get the current integrator state.
        """
        return {"x": self.x}

    def reset(self, t):
        """
        Reset the integrator state to zero.
        """
        self.x = self.x0
        self._update_output_states(t)
