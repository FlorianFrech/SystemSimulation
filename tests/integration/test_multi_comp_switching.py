"""
Integration tests for event-localized mode switching.

Compares the two switching strategies of ``MultiComponent`` end to end:

1. ``mode_selector`` is polled at the top of each macro step, so a switch
   lands on the communication grid.
2. ``add_switch_indicator`` registers the condition as an event indicator, so
   the hybrid algorithm localizes the crossing by bisection and the switch
   lands at the crossing instant.

The fixture ramps ``y`` at a constant rate, which makes the exact crossing
time known analytically and the placement error measurable.
"""

import numpy as np
import pytest

from syssimx.core.multi_comp import Hysteresis
from syssimx.system.algorithms.hybrid import HybridAlgorithm
from syssimx.system.system import System
from tests.fixtures.components import SwitchableMultiComponent

# Ramp rate of the SLOW mode is 1.0, so y(t) = t and the threshold below is
# crossed at exactly t = 1.0 s. The macro step is deliberately coarse so that
# the grid-based switch cannot land there.
THRESHOLD = 1.0
T_CROSS = 1.0
MACRO_DT = 0.4
T_END = 2.0


def _magnitude(value, default: float = 0.0) -> float:
    """Unwrap a port value, which may be a Pint ``Quantity``."""
    if value is None:
        return default
    return float(getattr(value, "magnitude", value))


def _build_plant(*, localized: bool) -> SwitchableMultiComponent:
    """Return a plant that switches SLOW to FAST, by one strategy or the other."""
    plant = SwitchableMultiComponent(name="Plant", initial_mode="SLOW")

    if localized:
        plant.add_switch_indicator(
            name="to_fast",
            func=lambda c: _magnitude(c.outputs["y"].get()) - THRESHOLD,
            target_mode="FAST",
            direction=1,
        )
    else:
        plant.mode_selector = lambda t: (
            "FAST" if _magnitude(plant.outputs["y"].get()) >= THRESHOLD else "SLOW"
        )

    return plant


def _run(plant: SwitchableMultiComponent) -> System:
    system = System(name="SwitchingSystem")
    system.add_component(plant)
    system.algorithm = HybridAlgorithm()
    system.algorithm.verbose = False
    system.initialize(t0=0.0)
    system.run(t0=0.0, tf=T_END, dt=MACRO_DT)
    return system


def _switch_times(plant: SwitchableMultiComponent) -> list[float]:
    return [float(event["time"]) for event in plant.sync_events]


# ============================================================================
# Test Switch Placement
# ============================================================================
class TestSwitchPlacement:
    """Where the transition lands in time, for each strategy."""

    def test_localized_switch_lands_on_the_crossing(self):
        plant = _build_plant(localized=True)
        _run(plant)

        times = _switch_times(plant)
        assert len(times) == 1, f"expected exactly one switch, got {times}"
        # Bisection should place the switch far inside one macro step of the
        # analytic crossing time.
        assert times[0] == pytest.approx(T_CROSS, abs=1e-3)

    def test_grid_switch_lands_on_a_macro_step(self):
        plant = _build_plant(localized=False)
        _run(plant)

        times = _switch_times(plant)
        assert len(times) == 1, f"expected exactly one switch, got {times}"
        # The selector is polled at step boundaries, so the switch snaps to the
        # first grid point at or after the crossing.
        assert times[0] % MACRO_DT == pytest.approx(0.0, abs=1e-9)
        assert times[0] > T_CROSS

    def test_localization_reduces_the_placement_error(self):
        """The measurement the paper reports: grid error versus localized error."""
        localized = _build_plant(localized=True)
        grid = _build_plant(localized=False)
        _run(localized)
        _run(grid)

        error_localized = abs(_switch_times(localized)[0] - T_CROSS)
        error_grid = abs(_switch_times(grid)[0] - T_CROSS)

        assert error_grid > MACRO_DT / 2
        assert error_localized < error_grid


# ============================================================================
# Test Switch Semantics
# ============================================================================
class TestSwitchSemantics:
    """State handover and guards under a real hybrid run."""

    def test_mode_changes_and_state_is_continuous(self):
        plant = _build_plant(localized=True)
        _run(plant)

        assert plant.active_mode == "FAST"
        # y is carried across the switch, so it keeps growing from the
        # threshold rather than restarting.
        assert _magnitude(plant.outputs["y"].get()) > THRESHOLD

    def test_output_accelerates_after_the_switch(self):
        """FAST ramps four times quicker, so the post-switch slope must rise."""
        plant = _build_plant(localized=True)
        system = _run(plant)

        t_vals, data = system.get_history()["Plant"]
        t_arr = np.asarray(t_vals, dtype=float)
        y_arr = np.asarray(data["y"], dtype=float)

        before = y_arr[t_arr <= T_CROSS]
        after = y_arr[t_arr >= T_CROSS]
        slope_before = np.diff(before).mean() / MACRO_DT
        slope_after = np.diff(after).mean() / MACRO_DT

        assert slope_after > slope_before

    def test_dwell_window_blocks_the_switch(self):
        plant = _build_plant(localized=True)
        plant.hysteresis = Hysteresis(dwell_time=T_END)
        plant.hysteresis.record_switch(t=0.0)

        _run(plant)

        assert plant.active_mode == "SLOW"
        assert _switch_times(plant) == []
