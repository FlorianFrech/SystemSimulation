"""Regression tests for event localization that loses its opening bracket."""

import pytest

from syssimx.core.events import DenseTime, EventBracket
from syssimx.system import System
from syssimx.system.algorithms.hybrid import HybridAlgorithm
from tests.fixtures.components import MicroSteppingSource


def _indicator(comp):
    return comp.get_state()["y"]


def test_bisection_falls_back_to_the_macro_endpoint_crossing():
    """A failed final recheck must retain the crossing that opened bisection."""
    source = MicroSteppingSource("Source", y0=1.0, rate=0.0)
    source.add_event_indicator("zero", func=_indicator, direction=-1)
    source.initialize(0.0)

    crossing = EventBracket(
        source="Source",
        name="zero",
        t_left=0.0,
        t_right=1e-3,
        value_left=1.0,
        value_right=-1.0,
    )
    algorithm = HybridAlgorithm(tol_time=1e-3)

    dense_time, located = algorithm._locate_event_time(
        event_sources=[source],
        snapshots_left={"Source": source.checkpoint()},
        input_cache={"Source": {}},
        indicators_left={"Source": {"zero": 1.0}},
        initial_crossings=[crossing],
        t_left=0.0,
        t_right=1e-3,
    )

    assert dense_time == DenseTime(t=1e-3, micro=0)
    assert located == [crossing]


def test_empty_localization_is_fatal_when_requested(monkeypatch):
    """A detected crossing may not become an unreported empty dispatch list."""
    source = MicroSteppingSource("Source")
    source.add_event_indicator("zero", func=_indicator, direction=-1)

    system = System(name="empty localization")
    system.add_component(source)
    system.initialize(t0=0.0)

    algorithm = system.algorithm
    assert isinstance(algorithm, HybridAlgorithm)
    algorithm.raise_on_missed_event = True

    def return_empty_localization(self, *args, **kwargs):
        return DenseTime(t=1e-3, micro=0), []

    monkeypatch.setattr(HybridAlgorithm, "_locate_event_time", return_empty_localization)

    with pytest.raises(RuntimeError, match="localization returned no events"):
        system.run(0.0, 1e-3, 1e-3)

    assert [event.pair for event in algorithm.missed_events] == [("Source", "zero")]
