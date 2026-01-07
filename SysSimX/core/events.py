"""
This module define the hybrid event handling capabilities for SySSimX CoSimComponents.
Dense Time: Supports the resolution of events that occur at the same time instant (t_real: float, t_disc: int).
Event Indicator: Used to check for zero-crossings that trigger events.
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

    def __str__(self) -> str:
        return f"({self.t:.8f}, {self.micro})"
    
    def advance_micro(self) -> "DenseTime":
        """Returns a new DenseTime advanced by one micro step."""
        return DenseTime(self.t, self.micro + 1)
    
    def to_float(self) -> float:
        """Converts DenseTime to a single float representation."""
        return self.t

# -------------------------------------------------------------------
# Events
# -------------------------------------------------------------------
@dataclass(frozen=True)
class Event:
    name: str
    source: str
    time: Optional[DenseTime] = None
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
# Sign function with tolerance
# -------------------------------------------------------------------
def _sign(value: float, tol: float = 1e-10) -> int:
    """Returns the sign of a value with a tolerance."""
    if value > tol:
        return 1
    elif value < -tol:
        return -1
    else:
        return 0