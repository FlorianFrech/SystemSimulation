from dataclasses import dataclass


# ----------------------------------------------------------------------------
# Standard Connection
# ----------------------------------------------------------------------------
@dataclass(frozen=True)
class Connection:
    """
    Defines a connection between two components in a co-simulation environment.
     - src_comp, dst_comp: NAMES (str) of source and destination components
     - src_port, dst_port: port NAMES (str) of source and destination ports
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
    src_comp: str
    src_port: str
    dst_comp: str
    dst_port: str

    @property
    def event_name(self) -> str:
        return self.src_port

    @property
    def target_comp(self) -> str:
        return self.dst_comp
