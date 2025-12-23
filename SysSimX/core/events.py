"""
This module define the hybrid event handling capabilities for SySSimX CoSimComponents.
Dense Time: Supports the resolution of events that occur at the same time instant (t_real: float, t_disc: int).
Event Indicator: Used to check for zero-crossings that trigger events.
Event Detector: Used to detect events based on event indicators.
Event Locator: Apply a bisection method to locate the exact time of an event.
Event Handler: Handle the event by updating states instantaneously.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Tuple, List, Optional, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from .base import CoSimComponent

# -------------------------------------------------------------------
# Dense Time
# -------------------------------------------------------------------
@dataclass(order=True, frozen=True)
class DenseTime:
    """Represents a dense time instant with real and discrete values."""
    t: float
    micro: int = 0

# -------------------------------------------------------------------
# Events
# -------------------------------------------------------------------
@dataclass(frozen=True)
class Event:
    name: str
    source: str
    time: DenseTime
    direction: Optional[int] = None # -1: falling, 0: any, 1: rising

# -------------------------------------------------------------------
# Event Indicator
# -------------------------------------------------------------------
class EventIndicator:
    """Represents an event indicator for zero-crossing detection."""
    def __init__(self, name: str,
                 function: Callable[["CoSimComponent"], float],
                 direction: int = 0):
        self.name = name
        self.function = function
        self.direction = direction
        if direction not in (-1, 0, 1):
            raise ValueError("Direction must be -1 (falling), 0 (both), or +1 (rising).")
        
    def evaluate(self, component: "CoSimComponent") -> float:
        """Evaluate the event indicator function."""
        return float(self.function(component))

# -------------------------------------------------------------------
# Event Locator
# -------------------------------------------------------------------
class EventLocator:
    """Locates the exact time of an event using bisection method."""
    def __init__(self,
                 tol_value: float = 1e-8,
                 max_iter: int = 50):
        self.tol_value = tol_value
        self.max_iter = max_iter
    
    def locate_event(self,
                     components: Dict[str, "CoSimComponent"],
                     snapshots: Dict[str, Any],
                     t_left: float,
                     t_right: float,
                     verbose: bool = False) -> Tuple[float, List[Tuple[str, str]], bool]:
        """
        Locate the exact time of an event between t_left and t_right.
        
        Args:
            components: Dictionary of components to check for events
            snapshots: Dictionary of component snapshots at t_left
            t_left: Left boundary of time interval
            t_right: Right boundary of time interval
            verbose: If True, print iteration details
            
        Returns:
            Tuple of (event_time, [(component_name, event_name), ...], success)
        """
        dt = t_right - t_left

        # 1) Restore all components to their snapshots at t_left and get initial indicator values
        indicators_left = {}
        for comp_name, comp in components.items():
            if not comp.supports_rollback:
                raise RuntimeError(f"Component '{comp_name}' does not support rollback required for event location.")
            comp.restore_state(snapshots[comp_name], t=t_left)
            indicators_left[comp_name] = comp.evaluate_event_indicators()

        # 2) Bisection loop
        for iteration in range(self.max_iter):
            # Calculate midpoint
            dt_half = dt / 2
            t_mid = t_left + dt_half

            if verbose:
                print(f"Iteration {iteration + 1}: t_left={t_left:.8f}, t_mid={t_mid:.8f}, "
                      f"t_right={t_right:.8f}, dt={dt:.8e}")

            # Step all components to t_mid
            indicators_mid = {}
            for comp_name, comp in components.items():
                comp.restore_state(snapshots[comp_name], t=t_left)
                comp.do_step(t=t_left, dt=dt_half)
                indicators_mid[comp_name] = comp.evaluate_event_indicators()

            # Check for events at midpoint
            events_left_to_mid = []
            events_mid_to_right = []
            for comp_name, comp in components.items():
                # Get indicators for left and mid
                ind_left = indicators_left[comp_name]
                ind_mid = indicators_mid[comp_name]

                # Check event indicators
                for event_name, indicator in comp.event_indicators.items():
                    val_left = ind_left[event_name]
                    val_mid = ind_mid[event_name]
                    # Check if we are at the event (within tolerance)
                    if abs(val_mid) <= self.tol_value:
                        return t_mid, [(comp_name, event_name)], True
                    # Check for zero-crossing
                    if self._is_crossing(val_left, val_mid, indicator.direction):
                        events_left_to_mid.append((comp_name, event_name))

            if events_left_to_mid:
                # Event is in left half
                t_right = t_mid
                dt = dt_half
            else:
                # Event is in right half
                t_left = t_mid
                dt = dt_half
                indicators_left = indicators_mid  # Move left indicators to mid

                # Update snapshots to mid for next iteration
                for comp_name, comp in components.items():
                    snapshots[comp_name] = comp.snapshot_state()
        
        # Return midpoint with any detected events
        all_events = []
        for comp_name, comp in components.items():
            ind_mid = indicators_mid[comp_name]
            for event_name, indicator in comp.event_indicators.items():
                if abs(ind_mid[event_name]) < self.tol_value * 10:  # Relaxed tolerance
                    all_events.append((comp_name, event_name))
        
        return t_mid, all_events, len(all_events) > 0

    def _is_crossing(self, val_before: float, val_after: float, direction: int) -> bool:
        """
        Check if values indicate a zero-crossing in the specified direction.
        
        Args:
            val_before: Indicator value before
            val_after: Indicator value after
            direction: -1 (falling), 0 (both), +1 (rising)
            
        Returns:
            True if crossing detected
        """
        sign_before = _sign(val_before, self.tol_value)
        sign_after = _sign(val_after, self.tol_value)
        
        # If either value is exactly zero (within tolerance), check if we're crossing
        if sign_before == 0:
            # Started at zero - look at direction we're moving
            if direction == 0:
                return sign_after != 0  # Moving away from zero
            elif direction == 1:
                return sign_after > 0  # Moving to positive
            elif direction == -1:
                return sign_after < 0  # Moving to negative
                
        if sign_after == 0:
            # Ended at zero - this IS an event
            return True
        
        # Check for sign change
        if direction == 0:  # Any direction
            return sign_before * sign_after < 0
        elif direction == 1:  # Rising only
            return sign_before < 0 and sign_after > 0
        elif direction == -1:  # Falling only
            return sign_before > 0 and sign_after < 0
        
        return False

    def _validate_times(self, t_left: float, t_right: float, dt_initial: float) -> bool:
        """Validate the initial time bounds for event location."""
        if t_right <= t_left:
            raise ValueError("t_right must be greater than t_left.")
        if dt_initial <= 0:
            raise ValueError("dt_initial must be positive.")
        if (t_right - t_left) < dt_initial:
            raise ValueError("The interval (t_right - t_left) must be greater than dt_initial.")
        return True
        
# -------------------------------------------------------------------
# Event Locator
# -------------------------------------------------------------------
def _sign(value: float, tol: float = 1e-10) -> int:
    """Returns the sign of a value with a tolerance."""
    if value > tol:
        return 1
    elif value < -tol:
        return -1
    else:
        return 0
    

    
