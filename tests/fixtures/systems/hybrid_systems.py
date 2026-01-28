"""Factory functions for creating hybrid test systems."""

from syssimx.system import Connection, System
from syssimx.system.connection import EventConnection
from tests.fixtures.components import HybridCombi, HybridListener, HybridSource, SimpleGain


def create_simple_hybrid_system() -> tuple[
    System, HybridSource, HybridListener, HybridCombi, SimpleGain
]:
    """
    Create a small hybrid system with event and data connections.

    Structure:
        HybridSource.x -> Gain.u (data edge)
        HybridSource.trigger -> Listener.v_invert (event)
        HybridSource.trigger -> Combi.v_double (event)

    Returns:
        Tuple of (system, source, listener, combi, gain)
    """
    sys = System(name="HybridVisualizer")

    source = HybridSource(name="Source", x0=0.0, v=1.0)
    source.add_event_indicator("trigger", lambda c: c.x, direction=1)
    source.initialize(0.0)

    listener = HybridListener(name="Listener", use_event_annotations=True)
    combi = HybridCombi(name="Combi", x0=0.0, v=1.0)
    gain = SimpleGain(name="Gain", gain=1.5)
    gain.group = "Control"

    for comp in (source, listener, combi, gain):
        sys.add_component(comp)

    # Data connection
    sys.add_connection(Connection("Source", "x", "Gain", "u"))

    # Event connections
    sys.add_event_connection(EventConnection("Source", "trigger", "Listener", "v_invert"))
    sys.add_event_connection(EventConnection("Source", "trigger", "Combi", "v_double"))

    return sys, source, listener, combi, gain
