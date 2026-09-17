"""The HYB-08 guard: dispatch only a crossing the accepted trajectory has reached.

This is the reverse of HYB-01. Detection advances the event source with the
input cached at the left edge of the step, so it can locate a crossing that the
accepted advance, which re-reads the updated input, has not reached yet at the
located instant. Dispatching there acts on a state that is still on the old
side of zero, and the same crossing is located again once the committed
trajectory really reaches it.

Here detection integrates ``y' = -2`` from ``y = 1`` and locates zero at
``t = 0.5``; the accepted advance integrates ``y' = -0.8`` and reaches zero at
``t = 1.25``. Exactly one event must be dispatched, at the committed crossing.
"""

import logging

import pytest

from syssimx.system import Connection, System
from tests.fixtures.components import InputEchoSource, RateIntegratingSource, RateStepSource


def _indicator(comp):
    return comp.get_state()["y"]


def _build(**algorithm_options):
    upstream = RateStepSource("Upstream", before=-2.0, after=-0.8)
    integrator = RateIntegratingSource("Integrator", y0=1.0)
    integrator.add_event_indicator("zero", func=_indicator, direction=-1)
    # Connects ``Integrator.y`` so its declared feedthrough becomes an edge.
    sink = InputEchoSource("Sink")

    system = System(name="premature dispatch")
    system.add_component(upstream)
    system.add_component(integrator)
    system.add_component(sink)
    system.add_connection(Connection("Upstream", "v", "Integrator", "u"))
    system.add_connection(Connection("Integrator", "y", "Sink", "u"))
    system.initialize(t0=0.0)
    for key, value in algorithm_options.items():
        setattr(system.algorithm, key, value)
    return system, integrator


def _dispatched(system):
    return system.get_history().get("Events", {}).get(("Integrator", "zero"), [])


def test_detection_locates_the_crossing_too_early():
    """Guard the premise, so the test cannot pass for the wrong reason."""
    system, integrator = _build()
    _, _, _, crossings, _ = system.algorithm._detect_crossings([integrator], 0.0, 1.0)
    assert [c.pair for c in crossings] == [("Integrator", "zero")]


def test_crossing_is_dispatched_once_at_the_committed_instant(caplog):
    system, integrator = _build()
    with caplog.at_level(logging.INFO, logger="syssimx"):
        system.run(0.0, 2.0, 1.0)

    events = _dispatched(system)
    assert len(events) == 1, events
    assert float(events[0].t) == pytest.approx(1.25, abs=1e-4)
    assert integrator.get_state()["y"] < 0.0
    assert "HYB-08" in caplog.text


def test_deferral_limit_dispatches_with_a_warning(caplog):
    system, _ = _build(max_deferrals=0)
    with caplog.at_level(logging.WARNING, logger="syssimx"):
        system.run(0.0, 1.0, 1.0)

    assert len(_dispatched(system)) == 1
    assert "deferral limit" in caplog.text
