"""Connection definitions for co-simulation components.

This module defines data classes for representing connections between
components in a co-simulation environment.

Classes:
    - Connection: Standard data connection between two components.
    - EventConnection: Event-based connection for event handling.
"""

from dataclasses import dataclass


# ----------------------------------------------------------------------------
# Standard Connection
# ----------------------------------------------------------------------------
@dataclass(frozen=True)
class Connection:
    """Defines a connection between two components in a co-simulation environment.

    Attributes:
        src_comp (str): Name of the source component.
        src_port (str): Name of the output port on the source component.
        dst_comp (str): Name of the destination component.
        dst_port (str): Name of the input port on the destination component.
    """

    src_comp: str
    src_port: str
    dst_comp: str
    dst_port: str

    def key(self) -> tuple[str, str, str, str]:
        """
        Unique key for duplicate detection.
        """
        return (self.src_comp, self.src_port, self.dst_comp, self.dst_port)


# ----------------------------------------------------------------------------
# Event Connection
# ----------------------------------------------------------------------------
@dataclass(frozen=True)
class EventConnection:
    """Defines an event connection between a source (event producer) and target (event listener).

    When added to a System via add_event_connection():
    - The system automatically subscribes the target to the event
    - No manual Event object creation or subscribe_event() call required

    Attributes:
        src_comp: Name of the component that produces the event (has event indicator)
        src_port: Name of the event (must match event indicator name on source)
        dst_comp: Name of the component that handles the event
        dst_port: Name of the event input port on the target (for visualization)
    """

    src_comp: str
    src_port: str
    dst_comp: str
    dst_port: str
    
    @property
    def event_name(self) -> str:
        """Name of the event (same as src_port)."""
        return self.src_port

    @property
    def target_comp(self) -> str:
        """Name of the target component."""
        return self.dst_comp

    def key(self) -> tuple[str, str, str, str]:
        """Unique key for duplicate detection."""
        return (self.src_comp, self.src_port, self.dst_comp, self.dst_port)
