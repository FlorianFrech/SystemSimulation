from SysSimX.core.base import CoSimComponent
from SysSimX.core.port import PortSpec, PortType

#----------------------------------------------------------------------------
# Port specifications
#----------------------------------------------------------------------------   
INPUT_SPECS = {}

OUTPUT_SPECS = {
    "u(t)=1": PortSpec("u(t)=1", PortType.REAL, direction="out")
}

#----------------------------------------------------------------------------
# Simple Source Component
#----------------------------------------------------------------------------
class Source(CoSimComponent):
    """
    A source component that provides a constant output signal.
    """

    def __init__(self, name="Source", output_value=1.0):
        super().__init__(name)

        # Define ports
        self.input_specs = INPUT_SPECS
        self.output_specs = OUTPUT_SPECS
        self._initialize_ports_from_specs()      

        # Direct feedthrough information
        self.direct_feedthrough = {}  # No direct feedthrough

    def _initialize_component(self, t0: float) -> None:
        """
        Initialize the source component.
        """
        self.state = 1

    def _do_step_internal(self, t: float, dt: float) -> None:
        """
        Perform a simulation step by setting the output signal.
        """
        self.state = 1

    def _update_output_states(self, t):
        """
        Update the output port states.
        """
        self.outputs['u(t)=1'].set(self.state, t)

    def set_state(self, state, t):
        pass

    def get_state(self):
        return self.state
    
    def reset(self):
        self.state = 0.0
    