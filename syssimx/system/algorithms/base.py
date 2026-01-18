from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..system import System


# ----------------------------------------------------------------------------
# Abstract Algorithm Base Class
# ----------------------------------------------------------------------------
class Algorithm(ABC):
    """Algorithm interface for advancing a System by one time step."""

    name: str

    @abstractmethod
    def step(self, system: System, t: float, dt: float) -> None:
        """Advance the system from t to t+dt."""
        ...
