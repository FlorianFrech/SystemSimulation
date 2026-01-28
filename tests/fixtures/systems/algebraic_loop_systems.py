"""Factory functions for algebraic loop test systems."""

from syssimx.system import Connection, System
from tests.fixtures.components import SimpleGain


def create_small_algebraic_loop_system() -> tuple[System, SimpleGain, SimpleGain]:
    """
    Create a small system with a two-component algebraic loop.

    Structure:
        GainA.y -> GainB.u
        GainB.y -> GainA.u

    Returns:
        Tuple of (system, gain_a, gain_b)
    """
    sys = System(name="SmallAlgebraicLoop")
    gain_a = SimpleGain(name="GainA", gain=0.8)
    gain_b = SimpleGain(name="GainB", gain=0.6)

    sys.add_component(gain_a)
    sys.add_component(gain_b)

    sys.add_connection(Connection("GainA", "y", "GainB", "u"))
    sys.add_connection(Connection("GainB", "y", "GainA", "u"))

    return sys, gain_a, gain_b
