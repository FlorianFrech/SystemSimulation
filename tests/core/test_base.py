from typing import Dict, Any
from SysSimX.core.base import CoSimComponent
from SysSimX.core.port import PortSpec, PortType, PortState, ureg, Quantity
from SysSimX.utilities.units import to_pint_unit

#---------------------------------------------------------------
# Test Component
#---------------------------------------------------------------

class Gain(CoSimComponent):
    """
    Simple gain component for testing purposes.
    y = k * u
     - y in rad/s
     - k in (rad/s) / (N*m)
     - u in N*m
    """

    def __init__(self, name: str, gain: float, gain_unit: str = "rad/s / (N*m)"):
        super().__init__(name)
        self.k_unit_str = str(to_pint_unit(gain_unit))
        self.k = gain * ureg(self.k_unit_str)
        self._t0 = None

    def _initialize_component(self, t0):
        pass

    def initialize(self, t0: float) -> None:
        self._t0 = t0
        
        self.input_specs = {
            "u": PortSpec(name="u", type=PortType.REAL, direction="in", unit="N*m", description="Input torque")
        }
        self.output_specs = {
            "y": PortSpec(name="y", type=PortType.REAL, direction="out", unit="rad/s", description="Output angular velocity")
        }

        self.inputs = {name: PortState(spec=spec) for name, spec in self.input_specs.items()}
        self.outputs = {name: PortState(spec=spec) for name, spec in self.output_specs.items()}

        # Initialize output to zero
        self.outputs["y"].set(value=Quantity(0.0, "rad/s"), t=t0)

    def _do_step_internal(self, t, dt):
        pass
    
    def do_step(self, t, dt):
        u_val = self.inputs["u"].get()
        if u_val is None:
            y_val = Quantity(0.0, "rad/s")
        else:
            u_q = u_val if isinstance(u_val, Quantity) else Quantity(u_val, "N*m")
            y_val = self.k * u_q
        self.outputs['y'].set(y_val, t=t+dt)
    
    def set_state(self, state: Dict[str, Any]):
        state_keys = self.outputs.keys()
        for key in state_keys:
            if key in state:
                self.outputs[key].set(state[key], t=self._t0)

    def get_state(self) -> Dict[str, Any]:
        state_keys = self.outputs.keys()
        return {key: self.outputs[key].get() for key in state_keys if self.outputs[key].get() is not None}
    
    def _update_output_states(self, t):
        pass
    
    def reset(self) -> None:
        self._t0 = None
        self.inputs = {}
        self.outputs = {}
        self.input_specs = {}
        self.output_specs = {}

#---------------------------------------------------------------

def test_initialization():
    comp = Gain(name="Gain", gain=2.0)
    comp.initialize(t0=0.0)
    y = comp.outputs['y'].get()
    assert comp.name == "Gain"
    assert comp.k.magnitude == 2.0
    assert isinstance(comp.k, Quantity)
    assert comp.outputs['y'].get().magnitude == 0.0
    assert y.is_compatible_with("rad/s")

def test_port_specs():
    comp = Gain(name="Gain", gain=2.0)
    comp.initialize(t0=0.0)
    u_port = comp.inputs['u']
    assert u_port.spec.name == "u"
    assert u_port.spec.type == PortType.REAL
    assert u_port.spec.direction == "in"
    assert u_port.spec.unit == "N*m"
    assert u_port.spec.description == "Input torque"
    
    y_port = comp.outputs['y']
    assert y_port.spec.name == "y"
    assert y_port.spec.type == PortType.REAL
    assert y_port.spec.direction == "out"
    assert y_port.spec.unit == "rad/s"
    assert y_port.spec.description == "Output angular velocity"

def test_port_state():
    comp = Gain(name="Gain", gain=2.0)
    comp.initialize(t0=0.0)
    comp.set_inputs({"u": Quantity(3.0, "N*m")}, t=0.0)
    u_port = comp.inputs['u']
    assert isinstance(u_port.spec, PortSpec)
    assert u_port.value.is_compatible_with("N*m")
    assert u_port.value.magnitude == 3.0
    assert u_port.t_last == 0.0

def test_do_step():
    comp = Gain(name="Gain", gain=2.0)
    comp.initialize(t0=0.0)
    comp.set_inputs({"u": Quantity(3.0, "N*m")}, t=0.0)
    comp.do_step(t=0.0, dt=1.0)
    y_port = comp.outputs['y']
    y = comp.outputs['y'].get()
    assert y.is_compatible_with("rad/s")
    assert abs(y.magnitude - 6.0) < 1e-6
    assert y_port.t_last == 1.0


# TODO: Add tests for set_state, get_state, reset