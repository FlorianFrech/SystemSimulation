from SysSimX.core.base import CoSimComponent
from SysSimX.core.port import PortSpec, PortState, PortType
from SysSimX.utilities.units import ureg, Quantity

#----------------------------------------------------------------------------
# Port specifications
#----------------------------------------------------------------------------   
INPUT_SPECS = {
    "input1": PortSpec("input1", PortType.REAL, direction="in"),
    "input2": PortSpec("input2", PortType.REAL, direction="in")
}

OUTPUT_SPECS = {
    "output": PortSpec("output", PortType.REAL, direction="out")
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

        self.direct_feedthrough = {'output': {'input1', 'input2'}}

    def _initialize_component(self, t0: float) -> None:
        """
        Initialize the adder component.
        """
        # initialize input values to avoid None issues
        self.inputs['input1'].set(0.0, 0.0)
        self.inputs['input2'].set(0.0, 0.0)
        in1 = self.inputs['input1'].get()
        in2 = self.inputs['input2'].get()
        self.result = in1 - in2

    def _do_step_internal(self, t: float, dt: float) -> None:
        """
        Perform a simulation step by summing the input signals.
        """
        input1_value = self.inputs['input1'].get()
        input2_value = self.inputs['input2'].get()
        self.result = input1_value - input2_value
        self.outputs['output'].set(self.result, t)

    def _update_output_states(self, t):
        """
        Update the output port states.
        """
        input1_value = self.inputs['input1'].get()
        input2_value = self.inputs['input2'].get()
        if input1_value is None or input2_value is None:
            return
        self.result = input1_value - input2_value
        self.outputs['output'].set(self.result, t)
    
    def set_state(self, state, t):
        pass

    def get_state(self):
        pass

    def reset(self):
        self.outputs['output'].set(0.0, self.t)

    def eval_outputs(self, **inputs) -> dict:
        i1 = inputs.get('input1', self.inputs['input1'].get())
        i2 = inputs.get('input2', self.inputs['input2'].get())
        return {'output': (i1 - i2)}