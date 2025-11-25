from SysSimX.core.base import CoSimComponent
from SysSimX.core.port import PortSpec, PortState, PortType
from SysSimX.utilities.units import ureg, Quantity

#----------------------------------------------------------------------------
# Port specifications
#----------------------------------------------------------------------------   
INPUT_SPECS = {
    "input": PortSpec("input", PortType.REAL, direction="in"),
}

OUTPUT_SPECS = {
    "output": PortSpec("output", PortType.REAL, direction="out")
}

#----------------------------------------------------------------------------
# Simple Multiplier Component
#----------------------------------------------------------------------------
class Squarer(CoSimComponent):
    """
    A multiplier component that multiplies its two input signals.
    res = input1 * input2
    """

    def __init__(self, name="Multiplier"):
        super().__init__(name)

        # Define ports
        self.input_specs = INPUT_SPECS
        self.output_specs = OUTPUT_SPECS
        self._initialize_ports_from_specs()

        self.direct_feedthrough = {'output': {'input'}}

    def _initialize_component(self, t0: float) -> None:
        """
        Initialize the multiplier component.
        """
        # initialize input values to avoid None issues
        self.inputs['input'].set(1, t0)
        in_value = self.inputs['input'].get()
        self.result = in_value * in_value
    
    def _do_step_internal(self, t: float, dt: float) -> None:
        """
        Perform a simulation step by multiplying the input signals.
        """
        input_value = self.inputs['input'].get()
        self.result = input_value * input_value
        self.outputs['output'].set(self.result, t)

    def _update_output_states(self, t):
        """
        Update the output port states.
        """
        input_value = self.inputs['input'].get()
        if input_value is None:
            return
        self.result = input_value * input_value
        self.outputs['output'].set(self.result, t)
    
    def set_state(self, state, t):
        pass

    def get_state(self):
        pass

    def reset(self):
        self.outputs['output'].set(0.0, self.t)

    def eval_outputs(self, **inputs) -> dict:
        i = inputs.get('input', self.inputs['input'].get())
        return {'output': (i * i)}