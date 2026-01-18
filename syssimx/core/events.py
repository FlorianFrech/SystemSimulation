"""
This module define the hybrid event handling capabilities for SySSimX CoSimComponents.
Dense Time: Supports the resolution of events that occur at the same time instant (t_real: float, t_disc: int).
Event Indicator: Used to check for zero-crossings that trigger events.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import CoSimComponent

# -------------------------------------------------------------------
# Sign function with tolerance
# -------------------------------------------------------------------
import numpy as np


def _sign(value: float, tol: float = 1e-10) -> int:
    """Returns the sign of a value with a tolerance."""
    if abs(value) <= tol:
        return 0
    return int(np.sign(value))


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
    time: DenseTime | None = None
    direction: int | None = None  # -1: falling, 0: any, 1: rising


# -------------------------------------------------------------------
# Event Indicator
# -------------------------------------------------------------------
class EventIndicator:
    """Represents an event indicator for zero-crossing detection."""

    def __init__(
        self, name: str, function: Callable[["CoSimComponent"], float], direction: int = 0
    ):
        self.name = name
        self.function = function
        self.direction = direction
        if direction not in (-1, 0, 1):
            raise ValueError("Direction must be -1 (falling), 0 (both), or +1 (rising).")

    def evaluate(self, component: "CoSimComponent") -> float:
        """Evaluate the event indicator function."""
        return float(self.function(component))


# -------------------------------------------------------------------
# Internal Event Info (for components with internal micro-stepping)
# -------------------------------------------------------------------
@dataclass
class InternalEventInfo:
    """
    Information about an event detected during internal micro-stepping.

    Components that use internal micro-stepping (e.g., FEM models) can detect
    events more precisely than the master algorithm. This class allows them
    to communicate timing hints to the master algorithm for more efficient
    event localization.

    Attributes:
        event_name: Name of the detected event (must match an event indicator)
        t_before: Time of the last micro-step before the event (indicator was positive/negative)
        t_after: Time of the first micro-step after the event (indicator crossed zero)
        indicator_before: Indicator value at t_before (optional, for verification)
        indicator_after: Indicator value at t_after (optional, for verification)

    Usage:
        The master algorithm can use [t_before, t_after] as an initial narrow
        interval for bisection, rather than searching the full macro-step.
    """

    event_name: str
    t_before: float
    t_after: float
    indicator_before: float | None = None
    indicator_after: float | None = None

    def __post_init__(self):
        if self.t_after < self.t_before:
            raise ValueError(f"t_after ({self.t_after}) must be >= t_before ({self.t_before})")

    @property
    def interval_width(self) -> float:
        """Width of the event localization interval."""
        return self.t_after - self.t_before
