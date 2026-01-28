"""
Factory functions for creating test systems with mock components.
"""

from syssimx.system import Connection, System
from tests.fixtures.components import (
    ConstantSource,
    GainComponent,
    IntegratorComponent,
    SimpleGain,
    Subtractor,
    TorqueSource,
)


def create_two_component_system(
    name: str = "TwoCompSystem",
) -> tuple[System, SimpleGain, SimpleGain]:
    """
    Create a simple system with two SimpleGain components in series.

    Structure: Input -> GainA -> GainB -> Output

    Returns:
        Tuple of (system, comp_a, comp_b)
    """
    sys = System(name=name)
    comp_a = SimpleGain(name="GainA", gain=2.0)
    comp_b = SimpleGain(name="GainB", gain=3.0)

    connection = Connection(
        src_comp=comp_a.name,
        src_port="y",
        dst_comp=comp_b.name,
        dst_port="u",
    )

    sys.add_component(comp_a)
    sys.add_component(comp_b)
    sys.add_connection(connection)

    return sys, comp_a, comp_b


def create_chain_system(n_components: int = 3) -> tuple[System, list[SimpleGain]]:
    """
    Create a chain of n SimpleGain components in series.

    Structure: Gain0 -> Gain1 -> ... -> Gain(N-1)

    Returns:
        Tuple of (system, list of components)
    """
    sys = System(name=f"Chain{n_components}")
    components = [SimpleGain(name=f"Gain{i}", gain=1.5) for i in range(n_components)]

    for comp in components:
        sys.add_component(comp)

    for i in range(n_components - 1):
        connection = Connection(
            src_comp=components[i].name,
            src_port="y",
            dst_comp=components[i + 1].name,
            dst_port="u",
        )
        sys.add_connection(connection)

    return sys, components


def create_feedback_loop_system() -> tuple[System, SimpleGain, IntegratorComponent]:
    """
    Create a feedback loop system (NOT an algebraic loop due to integrator state).

    Structure:
        Gain.y -> Integrator.u
        Integrator.y -> Gain.u (feedback through state)

    The integrator breaks the algebraic loop because its output depends
    on internal state, not directly on the current input.

    Returns:
        Tuple of (system, gain, integrator)
    """
    sys = System(name="FeedbackLoop")
    gain = SimpleGain(name="Gain", gain=-1.0)
    integrator = IntegratorComponent(name="Integrator", x0=1.0)

    sys.add_component(gain)
    sys.add_component(integrator)

    # Gain output -> Integrator input
    conn1 = Connection(
        src_comp="Gain",
        src_port="y",
        dst_comp="Integrator",
        dst_port="u",
    )
    # Integrator output -> Gain input (feedback)
    conn2 = Connection(
        src_comp="Integrator",
        src_port="y",
        dst_comp="Gain",
        dst_port="u",
    )

    sys.add_connection(conn1)
    sys.add_connection(conn2)

    return sys, gain, integrator


def create_algebraic_loop_system() -> tuple[System, SimpleGain, SimpleGain]:
    """
    Create a system with an algebraic loop (direct feedthrough cycle).

    Structure:
        GainA.y -> GainB.u
        GainB.y -> GainA.u (algebraic loop!)

    Both components have direct feedthrough, creating a true algebraic loop.

    Returns:
        Tuple of (system, gain_a, gain_b)
    """
    sys = System(name="AlgebraicLoop")
    gain_a = SimpleGain(name="GainA", gain=0.5)
    gain_b = SimpleGain(name="GainB", gain=0.5)

    sys.add_component(gain_a)
    sys.add_component(gain_b)

    # GainA -> GainB
    conn1 = Connection(
        src_comp="GainA",
        src_port="y",
        dst_comp="GainB",
        dst_port="u",
    )
    # GainB -> GainA (creates algebraic loop)
    conn2 = Connection(
        src_comp="GainB",
        src_port="y",
        dst_comp="GainA",
        dst_port="u",
    )

    sys.add_connection(conn1)
    sys.add_connection(conn2)

    return sys, gain_a, gain_b


def create_visualizer_continuous_system() -> tuple[System, dict[str, object]]:
    """
    Create a continuous system with grouped components, direct feedthrough,
    multi-input ports, and a unit-labeled edge (no algebraic loops).

    Structure:
        Reference sources -> Subtractor -> Gain -> Integrator (ungrouped)
        TorqueSource -> GainComponent (unitful edge)

    Returns:
        Tuple of (system, components dict)
    """
    sys = System(name="VisualizerContinuous")

    # Grouped reference sources
    ref = ConstantSource(name="Ref", value=1.0)
    ref.group = "Reference"
    bias = ConstantSource(name="Bias", value=-0.2)
    bias.group = "Reference"

    # Control path with direct feedthrough and multiple inputs
    error = Subtractor(name="Error")
    error.group = "Control"
    gain = SimpleGain(name="Gain", gain=2.0)
    gain.group = "Control"

    # Plant component left ungrouped to exercise ungrouped rendering
    plant = IntegratorComponent(name="Plant", x0=0.0)

    # Unitful edge for label rendering
    torque = TorqueSource(name="Torque", torque=1.0)
    torque.group = "Actuator"
    torque_gain = GainComponent(name="TorqueToSpeed", gain=1.0)
    torque_gain.group = "Plant"

    for comp in (ref, bias, error, gain, plant, torque, torque_gain):
        sys.add_component(comp)

    # Reference path
    sys.add_connection(Connection("Ref", "y", "Error", "pos"))
    sys.add_connection(Connection("Bias", "y", "Error", "neg"))
    sys.add_connection(Connection("Error", "diff", "Gain", "u"))
    sys.add_connection(Connection("Gain", "y", "Plant", "u"))

    # Unitful edge
    sys.add_connection(Connection("Torque", "y", "TorqueToSpeed", "u"))

    return sys, {
        "ref": ref,
        "bias": bias,
        "error": error,
        "gain": gain,
        "plant": plant,
        "torque": torque,
        "torque_gain": torque_gain,
    }
