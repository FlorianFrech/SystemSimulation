from typing import Optional, Any
from ..core.base import CoSimComponent
from..core.port import Port

class Connection:
    """
    Defines a connection between two components in a co-simulation environment.

    :param src_comp: Source component
    :param src_port: Port on the source component
    :param dst_comp: Destination component
    :param dst_port: Port on the destination component
    :param delay: Delay in ticks (0 for same-tick, 1 for next-tick)
    :param unit: Optional unit for the connection
    """
    src_comp: CoSimComponent
    src_port: Port
    dst_comp: CoSimComponent
    dst_port: Port
    delay: int = 0 # 0 = same-tick, strict order; 1 = next-tick, no order
    unit: Optional[Any] = None

    def __init__(self,
                 src_comp: CoSimComponent,
                 src_port: Port,
                 dst_comp: CoSimComponent,
                 dst_port: Port,
                 delay: int = 0,
                 unit: Optional[Any] = None):
        self.src_comp = src_comp
        self.src_port = src_port
        self.dst_comp = dst_comp
        self.dst_port = dst_port
        self.delay = delay
        self.unit = unit

        self._validate()
        

    def _validate(self) -> None:
        """Validate the connection."""
        # Validate delay
        if self.delay not in (0, 1):
            raise ValueError(f"Connection delay must be 0 or 1, got {self.delay}")
        
        # Validate ports
        if self.src_port not in self.src_comp.outputs.values():
            raise ValueError(f"Source port {self.src_port} not found in source component outputs")
        if self.dst_port not in self.dst_comp.inputs.values():
            raise ValueError(f"Destination port {self.dst_port} not found in destination component inputs")
        
        # Validate units
        if self.src_port.unit is not None and self.dst_port.unit is not None:
            if not self.src_port.unit.is_compatible_with(self.dst_port.unit):
                raise ValueError(f"Units of source port {self.src_port.unit} and destination port {self.dst_port.unit} are not compatible")

