from typing import Any, Dict

import numpy as np

from SysSimX.core.base import CoSimComponent
from SysSimX.core.port import PortSpec, PortType
from SysSimX.utilities.units import Quantity

# -------------------------------------------------------------------
# Hybrid Test Component
# -------------------------------------------------------------------
class HybridComponent(CoSimComponent):
    """
    Simple component with a state variable that evolves linearly.
    x(t) = x0 + v * t
    Used for testing event indicators and zero-crossing detection.
    """
    
    def __init__(self, name: str, x0: float = 0.0, velocity: float = 1.0):
        super().__init__(name)
        self.x0 = x0
        self.v = velocity
        self.x = x0
        self._t0 = None
        
    def _initialize_component(self, t0: float) -> None:
        self._t0 = t0
        self.x = self.x0
        
        self.output_specs = {
            "x": PortSpec(name="x", type=PortType.REAL, direction="out", unit="m", description="State variable")
        }
        self._initialize_ports_from_specs()
        
    def _do_step_internal(self, t: float, dt: float) -> None:
        self.x = self.x0 + self.v * (t + dt - self._t0)
        
    def _update_output_states(self, t: float) -> None:
        self.outputs["x"].set(Quantity(self.x, "m"), t=t)
        
    def set_state(self, state: Dict[str, Any], t: float) -> None:
        if "x" in state:
            val = state["x"]
            self.x = val.magnitude if isinstance(val, Quantity) else val
            
    def get_state(self) -> Dict[str, Any]:
        return {"x": Quantity(self.x, "m")}
    
    def reset(self) -> None:
        super().reset()
        self.x = self.x0
        self._t0 = None
        self.inputs = {}
        self.outputs = {}

# -------------------------------------------------------------------
# Test Cases
# -------------------------------------------------------------------
def test_add_event_indicator():
    comp = HybridComponent('HybridComp', x0=0.0, velocity=1.0)
    comp.initialize(t0=0.0)
    event_function = lambda c: c.x
    comp.add_event_indicator(name='test_event',
                             func=event_function,
                             direction=1)
    assert comp.has_state_events
    assert 'test_event' in comp.event_indicators

def test_duplicate_event_indicator():
    comp = HybridComponent('HybridComp', x0=0.0, velocity=1.0)
    comp.initialize(t0=0.0)
    event_function = lambda c: c.x
    comp.add_event_indicator(name='test_event',
                             func=event_function,
                             direction=1)
    try:
        comp.add_event_indicator(name='test_event',
                                 func=event_function,
                                 direction=1)
        assert False, "Expected KeyError"
    except KeyError as e:
        assert "already exists" in str(e)

def test_detect_invalid_direction():
    comp = HybridComponent('HybridComp', x0=0.0, velocity=1.0)
    comp.initialize(t0=0.0)
    event_function = lambda c: c.x
    invalid_direction = 2  # Invalid direction
    try:
        comp.add_event_indicator(name='test_event',
                                 func=event_function,
                                 direction=invalid_direction)
        assert False, "Expected ValueError for invalid direction"
    except ValueError:
        pass

def test_has_state_events_property():
    comp = HybridComponent('HybridComp', x0=0.0, velocity=1.0)
    comp.initialize(t0=0.0)
    assert not comp.has_state_events
    comp.add_event_indicator(name='test_event',
                             func=lambda comp: comp.x,
                             direction=1)
    assert comp.has_state_events
    assert 'test_event' in comp.event_indicators

def test_evaluate_event_indicators():
    comp = HybridComponent('HybridComp', x0=0.0, velocity=1.0)
    comp.initialize(t0=0.0)
    comp.add_event_indicator(name='test_event',
                             func=lambda c: c.x,
                             direction=1)
    assert comp.evaluate_event_indicators() == {'test_event': 0.0}
    comp.do_step(t=0.0, dt=1.0)
    assert comp.evaluate_event_indicators() == {'test_event': 1.0}

def test_event_crossing_detection_rising():
    comp = HybridComponent('HybridComp', x0=-1.0, velocity=1.0)
    comp.initialize(t0=0.0)
    comp.add_event_indicator(name='test_event',
                             func=lambda c: c.x,
                             direction=1)
    
    # No crossing yet
    prev_values = comp.evaluate_event_indicators()
    comp.do_step(t=0.0, dt=0.5)  # x goes from -1 to -0.5
    curr_values = comp.evaluate_event_indicators()
    assert comp.detect_event_crossing(previous=prev_values, current=curr_values) == []

    # Crossing occurs here
    prev_values = curr_values
    comp.do_step(t=0.5, dt=1.0)  # x goes from -0.5 to 0.5
    curr_values = comp.evaluate_event_indicators()
    crossings = comp.detect_event_crossing(previous=prev_values, current=curr_values)
    assert 'test_event' in crossings

    # No crossing this time
    prev_values = curr_values
    comp.v = -1.0
    comp.do_step(t=1.5, dt=1.0)  # x goes from 0.5 to -0.5
    curr_values = comp.evaluate_event_indicators()
    assert comp.detect_event_crossing(previous=prev_values, current=curr_values) == []

def test_event_crossing_detection_falling():
    comp = HybridComponent('HybridComp', x0=1.0, velocity=-1.0)
    comp.initialize(t0=0.0)
    comp.add_event_indicator(name='test_event',
                             func=lambda c: c.x,
                             direction=-1)
    
    # No crossing yet
    prev_values = comp.evaluate_event_indicators()
    comp.do_step(t=0.0, dt=0.5)  # x goes from 1 to 0.5
    curr_values = comp.evaluate_event_indicators()
    assert comp.detect_event_crossing(previous=prev_values, current=curr_values) == []

    # Crossing occurs here
    prev_values = curr_values
    comp.do_step(t=0.5, dt=1.0)  # x goes from 0.5 to -0.5
    curr_values = comp.evaluate_event_indicators()
    crossings = comp.detect_event_crossing(previous=prev_values, current=curr_values)
    assert 'test_event' in crossings
    
    # No crossing this time
    prev_values = curr_values
    comp.v = 1.0
    comp.do_step(t=1.5, dt=1.0)  # x goes from -0.5 to 0.5
    curr_values = comp.evaluate_event_indicators()
    assert comp.detect_event_crossing(previous=prev_values, current=curr_values) == []


def test_event_crossing_detection_both():
    comp = HybridComponent('HybridComp', x0=-1.0, velocity=2.0)
    comp.initialize(t0=0.0)
    comp.add_event_indicator(name='test_event',
                             func=lambda c: c.x,
                             direction=0)
    
    prev_values = comp.evaluate_event_indicators()
    comp.do_step(t=0.0, dt=1.0)  # x goes from -1 to 1
    curr_values = comp.evaluate_event_indicators()
    crossings = comp.detect_event_crossing(previous=prev_values, current=curr_values)
    assert 'test_event' in crossings
    
    prev_values = curr_values
    comp.v = -2.0
    comp.do_step(t=1.0, dt=1.0)  # x goes from 1 to -1
    curr_values = comp.evaluate_event_indicators()
    crossings = comp.detect_event_crossing(previous=prev_values, current=curr_values)
    assert 'test_event' in crossings