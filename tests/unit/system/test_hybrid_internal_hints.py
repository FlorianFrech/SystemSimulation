"""Regression tests for internal micro-step hints in ``HybridAlgorithm``.

An event source that resolves its own crossing reports the bracketing interval
through ``report_internal_event()``. When the macro endpoints happened to
straddle the crossing as well, that hint was discarded as a duplicate, the
surviving macro-wide bracket was then filtered out by the hint short-circuit in
``_locate_event_time()``, and the algorithm located an event instant while
dispatching nothing.

The failure needs a ``tol_time`` at least as coarse as the component's internal
sub-step, because only then is the short-circuit reached at all. The default
``1e-8`` never takes that path, which is why the rest of the suite did not see
this. ``notebooks/06_casestudy_performance.ipynb`` sets ``1.5e-4`` deliberately
and lost three of five wall contacts to it.
"""

import pytest

from syssimx.system import System
from syssimx.system.algorithms.hybrid import HybridAlgorithm
from tests.fixtures.components import MicroSteppingSource

# Coarser than the source's 1e-4 sub-step, so the hint short-circuit fires.
COARSE_TOL_TIME = 1.5e-4
MACRO_DT = 1e-3

# The source starts at +5.5e-4 and falls at 1 per second, so it crosses on the
# sub-step from 5e-4 to 6e-4 and ends the macro step at -4.5e-4.
HINT_LEFT = 5e-4
HINT_RIGHT = 6e-4


def _indicator(comp):
    return comp.get_state()["y"]


@pytest.fixture
def source():
    comp = MicroSteppingSource("Source")
    comp.add_event_indicator("zero", func=_indicator, direction=-1)
    return comp


def test_macro_endpoints_and_hint_both_see_the_crossing(source):
    """Guard the premise: this is the case where both sources agree."""
    source.initialize(0.0)
    assert _indicator(source) > 0.0

    source.do_step(0.0, MACRO_DT)
    assert _indicator(source) < 0.0, "the macro endpoints must straddle the crossing"

    hints = source.get_internal_event_hints()
    assert [hint.event_name for hint in hints] == ["zero"]
    assert hints[0].t_before == pytest.approx(HINT_LEFT)
    assert hints[0].t_after == pytest.approx(HINT_RIGHT)


def test_hint_bracket_supersedes_the_macro_bracket(source):
    """The tighter bracket must survive, not be dropped as a duplicate."""
    source.initialize(0.0)

    algorithm = HybridAlgorithm()
    algorithm.tol_time = COARSE_TOL_TIME
    *_, crossings, hints = algorithm._detect_crossings([source], 0.0, MACRO_DT)

    assert [bracket.name for bracket in crossings] == ["zero"], (
        "exactly one bracket is expected; a macro bracket and a hint bracket for "
        "the same event are two descriptions of one crossing"
    )
    assert "Source" in hints

    bracket = crossings[0]
    assert bracket.t_left == pytest.approx(HINT_LEFT)
    assert bracket.t_right == pytest.approx(HINT_RIGHT)
    assert bracket.t_right - bracket.t_left <= COARSE_TOL_TIME


def test_agreeing_hint_and_macro_crossing_still_dispatch_the_event(source):
    """The regression itself: locating an instant must dispatch an event."""
    system = System(name="internal hint regression")
    system.add_component(source)
    system.initialize(t0=0.0)

    assert isinstance(system.algorithm, HybridAlgorithm)
    system.algorithm.tol_time = COARSE_TOL_TIME

    system.run(0.0, MACRO_DT, MACRO_DT)

    records = system.get_history().get("Events", {}).get(("Source", "zero"), [])
    assert len(records) == 1, "the located crossing was never dispatched"

    # Placement comes from the reported bracket, not from the macro interval.
    assert HINT_LEFT <= float(records[0].t) <= HINT_RIGHT + COARSE_TOL_TIME


def test_hint_only_crossing_still_dispatches():
    """The path that already worked must keep working.

    A bouncing source returns to the positive side inside the same macro step,
    so the endpoints show no sign change and the reported bracket is the only
    evidence of the crossing. This is the FEM contact case, and it dispatched
    correctly both before and after the fix.
    """
    comp = MicroSteppingSource("Source", bounce=True)
    comp.add_event_indicator("zero", func=_indicator, direction=-1)

    system = System(name="hint only")
    system.add_component(comp)
    system.initialize(t0=0.0)
    system.algorithm.tol_time = COARSE_TOL_TIME

    system.run(0.0, MACRO_DT, MACRO_DT)

    records = system.get_history().get("Events", {}).get(("Source", "zero"), [])
    assert len(records) == 1, "a bracket reported without an endpoint sign change was lost"
    assert HINT_LEFT <= float(records[0].t) <= HINT_RIGHT + COARSE_TOL_TIME


def test_bounce_hides_the_crossing_from_the_macro_endpoints():
    """Guard the premise of the hint-only case."""
    comp = MicroSteppingSource("Source", bounce=True)
    comp.initialize(0.0)
    assert _indicator(comp) > 0.0

    comp.do_step(0.0, MACRO_DT)
    assert _indicator(comp) > 0.0, "both macro endpoints must sit on the positive side"
    assert [hint.event_name for hint in comp.get_internal_event_hints()] == ["zero"]
