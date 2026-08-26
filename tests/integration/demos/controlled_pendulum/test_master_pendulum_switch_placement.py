"""Macro-step independence of the production angle-region switching policy.

The plant uses the real ``MasterPendulumSwitchConfig`` on ``abs(theta)`` with
real FEM, OpenSim, and FMU backends. Without gravity, contact, or drive torque
the angle is exactly linear in time, so the band-edge crossing has a closed
form and every localized switch can be compared against it.
"""

from __future__ import annotations

import math
from collections.abc import Iterator
from dataclasses import dataclass

import numpy as np
import pytest

pytest.importorskip("ngsolve")
pytest.importorskip("fmpy")
opensim = pytest.importorskip("opensim")

from syssimx_examples.controlled_pendulum.orchestration.master_pendulum import (  # noqa: E402
    MasterPendulumSwitchConfig,
)
from tests.integration.demos.controlled_pendulum.real_backend_support import (  # noqa: E402
    build_angle_region_plant,
    initialize_real_plant,
    require_euler_pendulum_fmu,
)

pytestmark = [pytest.mark.integration, pytest.mark.fem, pytest.mark.fmu, pytest.mark.opensim]

SWITCH_CONFIG = MasterPendulumSwitchConfig()
SIMULATION_TIME = 1.5e-3
# Incommensurate with both analytic crossing times, so a switch that landed on
# a communication point would be visible immediately.
MACRO_STEPS = (1e-4, 1.5e-4, 2.5e-4)

EVENT_TIME_TOLERANCE = 1e-7
PLACEMENT_SPREAD_TOLERANCE = 1e-7
THRESHOLD_TOLERANCE = 1e-6
MINIMUM_GRID_DISTANCE = 1e-5

require_euler_pendulum_fmu()


@dataclass(frozen=True)
class AngleRegionCase:
    """One directed crossing of a production ``abs(theta)`` region boundary."""

    label: str
    angular_position_deg: float
    angular_velocity: float
    boundary_index: int
    source_mode: str
    target_mode: str
    target_region: int

    @property
    def initial_angle(self) -> float:
        return float(np.deg2rad(self.angular_position_deg))

    @property
    def breakpoint(self) -> float:
        return SWITCH_CONFIG.breakpoints[self.boundary_index]

    @property
    def band(self) -> float:
        return SWITCH_CONFIG.bands[self.boundary_index]

    @property
    def threshold(self) -> float:
        """Armed band edge: the upper edge going up, the lower edge going down."""
        if self.angular_velocity > 0.0:
            return self.breakpoint + self.band
        return self.breakpoint - self.band

    @property
    def crossing_time(self) -> float:
        """Closed-form time at which ``abs(theta)`` reaches the armed edge."""
        return abs(self.threshold - self.initial_angle) / abs(self.angular_velocity)


CASES = (
    AngleRegionCase(
        label="descending-into-FEM",
        angular_position_deg=4.5,
        angular_velocity=-20.0,
        boundary_index=0,
        source_mode="OpenSim",
        target_mode="FEM",
        target_region=0,
    ),
    AngleRegionCase(
        label="ascending-into-FMU",
        angular_position_deg=14.9,
        angular_velocity=20.0,
        boundary_index=1,
        source_mode="OpenSim",
        target_mode="FMU",
        target_region=2,
    ),
)
CASES_BY_LABEL = {case.label: case for case in CASES}


@dataclass(frozen=True)
class PlacementResult:
    """Where one run placed its single region switch."""

    case: AngleRegionCase
    macro_step: float
    time: float
    angle: float
    from_mode: str
    to_mode: str
    region: int


@pytest.fixture(scope="module", autouse=True)
def quiet_opensim_logging() -> Iterator[None]:
    previous_level = opensim.Logger.getLevelString()
    opensim.Logger.setLevelString("Error")
    yield
    opensim.Logger.setLevelString(previous_level)


def _run_case(case: AngleRegionCase, macro_step: float) -> PlacementResult:
    plant = build_angle_region_plant(
        angular_position_deg=case.angular_position_deg,
        angular_velocity=case.angular_velocity,
        switch_config=SWITCH_CONFIG,
    )
    try:
        system = initialize_real_plant(plant, name=f"Placement-{case.label}")
        assert plant.active_mode == case.source_mode

        system.run(t0=0.0, tf=SIMULATION_TIME, dt=macro_step)

        assert len(plant.sync_events) == 1, plant.sync_events
        event = plant.sync_events[0]
        return PlacementResult(
            case=case,
            macro_step=macro_step,
            time=float(event["time"]),
            angle=abs(event["transfer_report"].source.theta),
            from_mode=event["from_mode"],
            to_mode=event["to_mode"],
            region=plant.active_region_index,
        )
    finally:
        plant.reset()


@pytest.fixture(scope="module")
def placements() -> dict[str, tuple[PlacementResult, ...]]:
    """Localize each boundary crossing once per macro-step size."""
    return {
        case.label: tuple(_run_case(case, macro_step) for macro_step in MACRO_STEPS)
        for case in CASES
    }


@pytest.mark.parametrize("label", list(CASES_BY_LABEL))
def test_the_real_policy_switches_to_the_expected_adjacent_region(
    placements: dict[str, tuple[PlacementResult, ...]], label: str
):
    case = CASES_BY_LABEL[label]

    for result in placements[label]:
        assert (result.from_mode, result.to_mode) == (case.source_mode, case.target_mode)
        assert result.region == case.target_region


@pytest.mark.parametrize("label", list(CASES_BY_LABEL))
def test_switches_are_localized_on_the_hysteresis_band_edge(
    placements: dict[str, tuple[PlacementResult, ...]], label: str
):
    case = CASES_BY_LABEL[label]

    for result in placements[label]:
        assert result.angle == pytest.approx(case.threshold, abs=THRESHOLD_TOLERANCE)
        # The band, not the breakpoint, is what arms the crossing.
        assert abs(result.angle - case.breakpoint) == pytest.approx(
            case.band, abs=THRESHOLD_TOLERANCE
        )


@pytest.mark.parametrize("label", list(CASES_BY_LABEL))
def test_switch_time_matches_the_closed_form_crossing(
    placements: dict[str, tuple[PlacementResult, ...]], label: str
):
    case = CASES_BY_LABEL[label]

    for result in placements[label]:
        assert result.time == pytest.approx(case.crossing_time, abs=EVENT_TIME_TOLERANCE)


@pytest.mark.parametrize("label", list(CASES_BY_LABEL))
def test_switch_placement_is_independent_of_the_macro_step(
    placements: dict[str, tuple[PlacementResult, ...]], label: str
):
    results = placements[label]
    times = [result.time for result in results]

    assert [result.macro_step for result in results] == list(MACRO_STEPS)
    assert max(times) - min(times) <= PLACEMENT_SPREAD_TOLERANCE


@pytest.mark.parametrize("label", list(CASES_BY_LABEL))
def test_switches_do_not_land_on_a_communication_point(
    placements: dict[str, tuple[PlacementResult, ...]], label: str
):
    for result in placements[label]:
        offset = math.remainder(result.time, result.macro_step)

        assert abs(offset) >= MINIMUM_GRID_DISTANCE
        assert result.time < SIMULATION_TIME
