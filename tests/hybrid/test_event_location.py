from typing import Any, Dict
from pathlib import Path
import numpy as np
import pytest

from SysSimX.core.base import CoSimComponent
from SysSimX.core.port import PortSpec, PortType
from SysSimX.core.events import EventLocator
from SysSimX.components.fmu_comp import FMUComponent
from SysSimX.utilities.units import Quantity

# -------------------------------------------------------------------
# FMU Pendulum Component with Rollback Support
# -------------------------------------------------------------------
class Pendulum(FMUComponent):
    """
    FMU-based pendulum component with rollback support.
    """
    def __init__(self, name, group = None):
        fmu_path = Path(__file__).parent.parent / "test_data" / "FMUs" / "Pendulum.fmu"
        super().__init__(name, fmu_path, group)

    def snapshot_state(self):
        """Create a snapshot of the current component state."""
        state = super().get_state()
        state["t"] = self.t
        return state

    def restore_state(self, snapshot, t):
        """Restore component to a previous state from snapshot."""
        self.t = t
        q0 = snapshot['q']['value']
        omega0 = snapshot['omega']['value']
        self._instance.reset()
        self._instance.instantiate()
        self._instance.setupExperiment(startTime=t)
        self._instance.enterInitializationMode()
        self.set_parameters(**{'q0': q0, 'omega0': omega0})
        self._apply_parameters_starts()
        self._apply_input_starts()
        self._instance.exitInitializationMode()

        self._update_output_states(t)
        self._record_outputs(t)

    def _handle_events_internal(self, event_names, t):
        if "wall_hit" not in event_names:
            return
        restitution = 1
        output = self.get_outputs()
        q0 = output['q'].magnitude
        omega0 = -restitution * output['omega'].magnitude

        self._instance.reset()
        self._instance.instantiate()
        self._instance.setupExperiment(startTime=t)
        self._instance.enterInitializationMode()
        self.set_parameters(**{'q0': q0, 'omega0': omega0})
        self._apply_parameters_starts()
        self._apply_input_starts()
        self._instance.exitInitializationMode()

        self._update_output_states(t)
        self._record_outputs(t)

# -------------------------------------------------------------------
# Test Cases
# -------------------------------------------------------------------
def test_event_location():
    pendulum = Pendulum(name="Pendulum")
    pendulum.set_parameters(q0=0.3)
    pendulum.initialize(t0=0.0)

    def event_indicator(comp: Pendulum) -> float:
        """Event indicator function for the pendulum component."""
        return comp.get_outputs()['q']

    pendulum.add_event_indicator(name="wall_hit",
                                func=event_indicator,
                                direction=-1)
    
    t = 0.0
    dt_initial = 0.01
    t_end = 1
    
    locator = EventLocator(tol_value=1e-6, max_iter=50)

    events = None
    t_left = t
    t_right = t + dt_initial

    while t < t_end:
        # 1) Save state before the step
        snapshot_before = pendulum.snapshot_state()
        
        # 2) Evaluate event indicators
        g_before = pendulum.evaluate_event_indicators()
        
        # 3) Perform the step
        if events:
            dt = t_right - t
        else:
            dt = dt_initial
        pendulum.do_step(t, dt)
        
        # 4) Evaluate event indicators after the step
        g_after = pendulum.evaluate_event_indicators()
        
        # 5) Check for events
        events = pendulum.detect_event_crossing(g_before, g_after)
        
        if events:
            t_left = t
            t_right = t + dt
            dt_initial = dt

            print(f"\n{'='*60}")
            print(f"Event detected in interval [{t_left:.4f}, {t_right:.4f}]")
            print(f"Events: {events}")
            print(f"{'='*60}\n")

            components = {pendulum.name: pendulum}
            snapshots = {pendulum.name: snapshot_before}

            t_event, detected_events, success = locator.locate_event(components,
                                                                    snapshots,
                                                                    t_left,
                                                                    t_right,
                                                                    verbose=False)

            if success:
                print(f"\n{'='*60}")
                print(f"Event located at t={t_event:.8f}")
                print(f"Events: {detected_events}")
                print(f"{'='*60}\n")
                
                # 7) Handle the event
                event_names = [event_name for comp_name, event_name in detected_events]
                pendulum.handle_event(event_names, t_event)
                
                # Update time and continue
                t = t_event
            else:
                print("Warning: Event location failed, continuing...")
                t += dt
        else:
            t += dt
    
    assert np.isclose(t_event, 0.43634, atol=1e-5), f"Expected event time around 0.43634766, got {t_event}"
    assert len(detected_events) == 1 and detected_events[0][1] == "wall_hit", f"Expected event 'wall_hit', got {detected_events}"
