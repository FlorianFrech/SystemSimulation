from SysSimX.core.base import CoSimComponent
from SysSimX.core.port import PortSpec, PortState, PortType
from SysSimX.utilities.units import ureg, Quantity

#----------------------------------------------------------------------------
# Port specifications
#----------------------------------------------------------------------------   
INPUT_SPECS = {
    "pos": PortSpec("pos", PortType.REAL, direction="in"),
    "neg": PortSpec("neg", PortType.REAL, direction="in")
}

OUTPUT_SPECS = {
    "diff": PortSpec("diff", PortType.REAL, direction="out")
}
    
#----------------------------------------------------------------------------
# Simple Subtractor Component
#----------------------------------------------------------------------------
class Subtractor(CoSimComponent):
    """
    A subtractor component that subtracts its two input signals.
    res = input1 - input2
    """

    def __init__(self, name="Subtractor"):
        super().__init__(name)

        # Define ports
        self.input_specs = INPUT_SPECS
        self.output_specs = OUTPUT_SPECS
        self._initialize_ports_from_specs()

        self.direct_feedthrough = {'diff': {'pos', 'neg'}}

    def _initialize_component(self, t0: float) -> None:
        """
        Initialize the subtractor component.
        """
        # initialize input values to avoid None issues
        self.inputs['pos'].set(0.0, 0.0)
        self.inputs['neg'].set(0.0, 0.0)
        in1 = self.inputs['pos'].get()
        in2 = self.inputs['neg'].get()
        self.result = in1 - in2

    def _do_step_internal(self, t: float, dt: float) -> None:
        """
        Perform a simulation step by summing the input signals.
        """
        input1_value = self.inputs['pos'].get()
        input2_value = self.inputs['neg'].get()
        self.result = input1_value - input2_value
        self.outputs['diff'].set(self.result, t)

    def _update_output_states(self, t):
        """
        Update the output port states.
        """
        input1_value = self.inputs['pos'].get()
        input2_value = self.inputs['neg'].get()
        if input1_value is None or input2_value is None:
            return
        self.result = input1_value - input2_value
        self.outputs['diff'].set(self.result, t)
    
    def set_state(self, state, t):
        pass

    def get_state(self):
        pass

    def reset(self):
        self.outputs['diff'].set(0.0, self.t)

    def evaluate_outputs(self, inputs) -> dict:
        # Use trial values first, fall back to actual component inputs
        i1 = inputs.get('pos', self.inputs['pos'].get())
        i2 = inputs.get('neg', self.inputs['neg'].get())

        # Unwrap quantities if needed
        if isinstance(i1, Quantity):
            i1 = i1.magnitude
        if isinstance(i2, Quantity):
            i2 = i2.magnitude
        self.outputs['diff'].set(i1 - i2, None)
        return {'diff': i1 - i2}