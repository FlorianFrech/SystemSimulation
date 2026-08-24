"""The HYB-01 guard: a crossing on the accepted trajectory must not pass quietly.

``_detect_crossings()`` advances every event source with the inputs cached at
the left edge of the macro step, while the accepted Gauss-Seidel advance
re-reads them after the upstream generation has stepped. The two trajectories
differ, so a crossing can be present on the committed one and absent from the
one detection examined.

For a single-direction indicator the miss is permanent rather than deferred:
the next macro step starts on the far side of zero and the crossing can never
be observed again. ``HybridAlgorithm`` therefore re-checks every accepted
advance it called event-free.
"""

import logging

import pytest

from syssimx.system import Connection, System
from syssimx.system.algorithms.hybrid import HybridAlgorithm
from tests.fixtures.components import FlippingSource, InputEchoSource


def _indicator(comp):
    return comp.get_state()["y"]


def _generation_of(system, name):
    return next(i for i, gen in enumerate(system.execution_order) if name in gen)


def _build():
    """Upstream flips +1 -> -1 on its first step; the event source echoes it.

    Detection sees the echo of ``+1`` because it steps with the cached input.
    The accepted advance sees ``-1`` because the upstream has already stepped,
    so the indicator crosses zero only on the trajectory that is committed.

    ``Sink`` exists so that ``Echo.y`` is connected. A declared feedthrough
    becomes a zero-delay edge only when the dependent output actually feeds
    something, so without the sink both components share one generation and
    the accepted advance reads the same stale input detection did.
    """
    upstream = FlippingSource("Upstream")
    echo = InputEchoSource("Echo", y0=1.0)
    echo.add_event_indicator("zero", func=_indicator, direction=-1)
    sink = InputEchoSource("Sink")

    system = System(name="stale input")
    system.add_component(upstream)
    system.add_component(echo)
    system.add_component(sink)
    system.add_connection(Connection("Upstream", "v", "Echo", "u"))
    system.add_connection(Connection("Echo", "y", "Sink", "u"))
    system.initialize(t0=0.0)
    return system, echo


def test_the_two_trajectories_really_do_disagree():
    """Guard the premise, so the test cannot pass for the wrong reason."""
    system, echo = _build()
    assert isinstance(system.algorithm, HybridAlgorithm)

    # Feedthrough on ``u`` must place the echo in a later generation than the
    # upstream; without that the accepted advance reads the same stale input.
    assert _generation_of(system, "Upstream") < _generation_of(system, "Echo")

    _, _, indicators_left, crossings, _ = system.algorithm._detect_crossings([echo], 0.0, 1.0)
    assert indicators_left["Echo"]["zero"] == pytest.approx(1.0)
    assert crossings == [], "detection must see no crossing on the stale-input trajectory"


def test_missed_crossing_is_reported(caplog):
    system, echo = _build()
    algorithm = system.algorithm

    with caplog.at_level(logging.WARNING, logger="syssimx.system.algorithms.hybrid"):
        system.run(0.0, 1.0, 1.0)

    assert _indicator(echo) < 0.0, "the accepted trajectory must have crossed"

    assert len(algorithm.missed_events) == 1
    missed = algorithm.missed_events[0]
    assert (missed.source, missed.name) == ("Echo", "zero")
    assert missed.value_left > 0.0 > missed.value_right

    assert any("HYB-01" in record.message for record in caplog.records)


def test_missed_crossing_can_be_made_fatal():
    system, _ = _build()
    system.algorithm.raise_on_missed_event = True

    with pytest.raises(RuntimeError, match="never localized"):
        system.run(0.0, 1.0, 1.0)


def test_guard_is_quiet_when_the_trajectories_agree(caplog):
    """No upstream, so detection and the accepted advance see the same inputs."""
    echo = InputEchoSource("Echo", y0=1.0)
    echo.add_event_indicator("zero", func=_indicator, direction=-1)

    system = System(name="no stale input")
    system.add_component(echo)
    system.initialize(t0=0.0)

    with caplog.at_level(logging.WARNING, logger="syssimx.system.algorithms.hybrid"):
        system.run(0.0, 1.0, 1.0)

    assert system.algorithm.missed_events == []
    assert not [record for record in caplog.records if "HYB-01" in record.message]
