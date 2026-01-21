"""Algorithm interfaces for advancing a System one time step."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..system import System


# ----------------------------------------------------------------------------
# Abstract Algorithm Base Class
# ----------------------------------------------------------------------------
class Algorithm(ABC):
    """Interface for simulation algorithms.

    Implementations are responsible for advancing a System from time t to t + dt.
    """

    name: str

    @abstractmethod
    def step(self, system: System, t: float, dt: float) -> None:
        """Advance the system from time t to t + dt.

        Args:
            system: System to advance.
            t: Current simulation time.
            dt: Step size.
        """
        ...
