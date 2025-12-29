from typing import Optional, Any, Tuple
from dataclasses import dataclass

#----------------------------------------------------------------------------
# Standard Connection
#----------------------------------------------------------------------------
@dataclass(frozen=True)
class Connection:
    """
    Defines a connection between two components in a co-simulation environment.
     - src_comp, dst_comp: NAMES (str) of source and destination components
     - src_port, dst_port: port NAMES (str) of source and destination ports
     - unit: Optional[Any], unit label for the connection (if applicable)
    """
    src_comp: str
    src_port: str
    dst_comp: str
    dst_port: str
    unit: Optional[Any] = None

    def key(self) -> Tuple[str, str, str, str]:
        """
        Unique key for duplicate detection.
        """
        return (self.src_comp, self.src_port, self.dst_comp, self.dst_port)
    
    def is_zero_delay(self) -> bool:
        """
        Check if the connection is zero-delay (delay == 0).
        """
        return self.delay == 0
    
#----------------------------------------------------------------------------
# Event Connection
#----------------------------------------------------------------------------
@dataclass(frozen=True)
class EventConnection:
    src_comp: str
    src_port: str
    dst_comp: str
    dst_port: str