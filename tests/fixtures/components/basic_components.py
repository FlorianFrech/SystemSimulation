from typing import Any

import numpy as np

from syssimx.core.base import CoSimComponent
from syssimx.core.port import PortSpec, PortType, ureg
from syssimx.utilities.units import Quantity, to_pint_unit


# ============================================================================
# Basic Components for Unit Tests
# ============================================================================
class SimpleGain(CoSimComponent):
    """
    Simple gain component with unitless ports for flexible testing.
    y = k * u

    Uses unitless input/output ports so it can be chained and connected
    to any other unitless component without type/unit compatibility issues.
    """

    def __init__(self, name: str, gain: float = 1.0):
        super().__init__(name)
        self.parameters.update({"k": gain})
        self.k = gain

        self.input_specs.update(
            {
                "u": PortSpec(
                    name="u",
                    type=PortType.REAL,
                    direction="in",
                    unit=None,
                    description="Input signal",
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
                    description="Output signal",
                )
            }
        )

        # Direct feedthrough: output y depends on input u
        self.direct_feedthrough = {"y": {"u"}}

    def _initialize_component(self, t0):
        pass

    def evaluate_outputs(self, inputs, t=None):
        self.set_inputs(inputs, t=t)
        self._update_output_states(t)
        return self.get_outputs()

    def _do_step_internal(self, t, dt):
        pass

    def set_state(self, state: dict[str, Any], t: float = None):
        pass

    def get_state(self) -> dict[str, Any]:
        return {}

    def _update_output_states(self, t):
        u = self.inputs["u"].get()
        if u is not None:
            u_val = u.magnitude if hasattr(u, "magnitude") else u
            y = self.k * u_val
            self.outputs["y"].set(y, t)


class GainComponent(CoSimComponent):
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
        self.parameters.update({"k": gain})
        self.k = gain * ureg(self.k_unit_str)

        self.input_specs.update(
            {
                "u": PortSpec(
                    name="u",
                    type=PortType.REAL,
                    direction="in",
                    unit="N*m",
                    description="Input torque",
                )
            }
        )

        self.output_specs.update(
            {
                "y": PortSpec(
                    name="y",
                    type=PortType.REAL,
                    direction="out",
                    unit="rad/s",
                    description="Output angular velocity",
                )
            }
        )

    def _initialize_component(self, t0):
        pass  # nothing to initialize

    def _validate_parameter(self, name, value):
        if name not in self.parameters:
            raise KeyError(f"Parameter {name} not found in GainComponent.")
        if name == "k":
            if not isinstance(value, (float, int)):
                raise TypeError(f"Parameter 'k' must be a float or int, got {type(value)}.")
        return value

    def evaluate_outputs(self, inputs, t=None):
        self.set_inputs(inputs, t=None)
        self._update_output_states(t)
        return self.get_outputs()

    def _do_step_internal(self, t, dt):
        pass  # no internal state to update

    def set_state(self, state: dict[str, Any]):
        pass  # no internal state to set

    def get_state(self) -> dict[str, Any]:
        return {}  # no internal state to return

    def _update_output_states(self, t):
        u = self.inputs["u"].get()
        print(u, self.k)
        y = self.k * u
        self.outputs["y"].set(y, t)


# ============================================================================
# Test Component: Constant Source
# ============================================================================
class ConstantSource(CoSimComponent):
    """A source component that outputs a constant value."""

    def __init__(self, name: str, value: float = 1.0):
        super().__init__(name)
        self.value = value
        self.output_specs.update({"y": PortSpec(name="y", type=PortType.REAL, direction="out")})
        self.direct_feedthrough = {}  # No inputs, no feedthrough

    def _initialize_component(self, t0: float) -> None:
        pass

    def _do_step_internal(self, t: float, dt: float) -> None:
        pass

    def _update_output_states(self, t: float | None = None, event_names: list[str] | None = None):
        self.outputs["y"].set(self.value, t)

    def set_state(self, state: dict[str, Any], t: float) -> None:
        pass

    def get_state(self) -> dict[str, Any]:
        return {"value": self.value}


class SineSource(CoSimComponent):
    """A source component that outputs a sine wave: y(t) = amplitude * sin(omega * t)."""

    def __init__(self, name: str, amplitude: float = 1.0, omega: float = 1.0):
        super().__init__(name)
        self.amplitude = amplitude
        self.omega = omega
        self.output_specs.update({"y": PortSpec(name="y", type=PortType.REAL, direction="out")})
        self.direct_feedthrough = {}

    def _initialize_component(self, t0: float) -> None:
        pass

    def _do_step_internal(self, t: float, dt: float) -> None:
        pass

    def _update_output_states(self, t: float | None = None, event_names: list[str] | None = None):
        y = self.amplitude * np.sin(self.omega * self.t)
        self.outputs["y"].set(y, t)

    def set_state(self, state: dict[str, Any], t: float) -> None:
        pass

    def get_state(self) -> dict[str, Any]:
        return {}


class LinearSource(CoSimComponent):
    """A source component that outputs a linear ramp: y(t) = slope * t + offset."""

    def __init__(self, name: str, slope: float = 1.0, offset: float = 0.0):
        super().__init__(name)
        self.slope = slope
        self.offset = offset
        self.output_specs.update({"y": PortSpec(name="y", type=PortType.REAL, direction="out")})
        self.direct_feedthrough = {}

    def _initialize_component(self, t0: float) -> None:
        pass

    def _do_step_internal(self, t: float, dt: float) -> None:
        pass

    def _update_output_states(self, t: float | None = None, event_names: list[str] | None = None):
        y = self.slope * self.t + self.offset
        self.outputs["y"].set(y, t)

    def set_state(self, state: dict[str, Any], t: float) -> None:
        pass

    def get_state(self) -> dict[str, Any]:
        return {}


class Source(CoSimComponent):
    """
    A source component that provides a constant output signal.
    """

    def __init__(self, name="Source", output_value=1.0):
        super().__init__(name)

        # Define ports
        self.output_specs.update({"u(t)=1": PortSpec("u(t)=1", PortType.REAL, direction="out")})

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
        self.outputs["u(t)=1"].set(self.state, t)

    def set_state(self, state, t):
        pass

    def get_state(self):
        return self.state

    def reset(self):
        pass


class Subtractor(CoSimComponent):
    """
    A subtractor component that subtracts its two input signals.
    res = input1 - input2
    """

    def __init__(self, name="Subtractor"):
        super().__init__(name)

        # Define ports
        self.input_specs.update(
            {
                "pos": PortSpec("pos", PortType.REAL, direction="in"),
                "neg": PortSpec("neg", PortType.REAL, direction="in"),
            }
        )
        self.output_specs.update({"diff": PortSpec("diff", PortType.REAL, direction="out")})

        self.direct_feedthrough = {"diff": {"pos", "neg"}}

    def _initialize_component(self, t0: float) -> None:
        """
        Initialize the subtractor component.
        """
        # initialize input values to avoid None issues
        self.inputs["pos"].set(0.0, 0.0)
        self.inputs["neg"].set(0.0, 0.0)
        in1 = self.inputs["pos"].get()
        in2 = self.inputs["neg"].get()
        self.result = in1 - in2

    def _do_step_internal(self, t: float, dt: float) -> None:
        """
        Perform a simulation step by summing the input signals.
        """
        input1_value = self.inputs["pos"].get()
        input2_value = self.inputs["neg"].get()
        self.result = input1_value - input2_value
        self.outputs["diff"].set(self.result, t)

    def _update_output_states(self, t):
        """
        Update the output port states.
        """
        input1_value = self.inputs["pos"].get()
        input2_value = self.inputs["neg"].get()
        if input1_value is None or input2_value is None:
            return
        self.result = input1_value - input2_value
        self.outputs["diff"].set(self.result, t)

    def set_state(self, state, t):
        pass

    def get_state(self):
        pass

    def reset(self):
        self.outputs["diff"].set(0.0, self.t)

    def evaluate_outputs(self, inputs) -> dict:
        # Use trial values first, fall back to actual component inputs
        i1 = inputs.get("pos", self.inputs["pos"].get())
        i2 = inputs.get("neg", self.inputs["neg"].get())

        # Unwrap quantities if needed
        if isinstance(i1, Quantity):
            i1 = i1.magnitude
        if isinstance(i2, Quantity):
            i2 = i2.magnitude
        self.outputs["diff"].set(i1 - i2, None)
        return {"diff": i1 - i2}
