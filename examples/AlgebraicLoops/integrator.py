from SysSimX.core.base import CoSimComponent
from SysSimX.core.port import PortSpec, PortType

#----------------------------------------------------------------------------
# Port specifications
#----------------------------------------------------------------------------   
INPUT_SPECS = {
    "input": PortSpec("input", PortType.REAL, direction="in")
}

OUTPUT_SPECS = {
    "output": PortSpec("output", PortType.REAL, direction="out")
}

#----------------------------------------------------------------------------
# Simple Integrator Component
#---------------------------------------------------------------------------- 
class Integrator(CoSimComponent):
    """
    An integrator component that integrates its input signal over time.
    """

    def __init__(self, name="Integrator"):
        super().__init__(name)

        # Define ports
        self.input_specs = INPUT_SPECS
        self.output_specs = OUTPUT_SPECS
        self._initialize_ports_from_specs()

        # Initialize state
        self.state = 0.0

        # Direct feedthrough information
        self.direct_feedthrough = {}  # No direct feedthrough

    def _initialize_component(self, t0: float) -> None:
        """
        Initialize the integrator state.
        """
        self.state = 0.0

    def _do_step_internal(self, t: float, dt: float) -> None:
        """
        Perform a simulation step by integrating the input signal.
        """
        input_value = self.inputs['input'].get()
        self.state += input_value * dt

    def _update_output_states(self, t):
        """
        Update the output port states.
        """
        self.outputs['output'].set(self.state, t)

    def set_state(self, state, t):
        """
        Set the integrator state.
        """
        self.state = state
        self._update_output_states(t)

    def get_state(self):
        """
        Get the current integrator state.
        """
        return self.state
    
    def reset(self, t):
        """
        Reset the integrator state to zero.
        """
        self.state = 0.0
        self._update_output_states(t)
