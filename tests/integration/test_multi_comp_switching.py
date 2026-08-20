"""Integration tests for event-localized, hysteretic region switching."""

from collections.abc import Callable, Sequence

import pytest

from syssimx.core.multi_comp import ModeKey
from syssimx.system.algorithms.hybrid import HybridAlgorithm
from syssimx.system.system import System
from tests.fixtures.components import RegionMultiComponent


def _magnitude(value, default: float = 0.0) -> float:
    if value is None:
        return default
    return float(getattr(value, "magnitude", value))


def _region_key(component: RegionMultiComponent) -> float:
    return _magnitude(component.outputs["y"].get())


def _run_regions(
    signal: Callable[[float], float],
    *,
    breakpoints: Sequence[float],
    modes: Sequence[ModeKey],
    band: float,
    dt: float,
    tf: float,
) -> RegionMultiComponent:
    plant = RegionMultiComponent(signal=signal, initial_mode=modes[0])
    plant.set_switch_regions(
        key=_region_key,
        breakpoints=breakpoints,
        modes=modes,
        band=band,
    )
    system = System(name="RegionSwitchingSystem")
    system.add_component(plant)
    algorithm = HybridAlgorithm()
    algorithm.verbose = False
    algorithm.tol_time = 1e-8
    algorithm.tol_value = 1e-14
    system.algorithm = algorithm
    system.initialize(t0=0.0)
    system.run(t0=0.0, tf=tf, dt=dt)
    return plant


def _switch_times(plant: RegionMultiComponent) -> list[float]:
    return [float(event["time"]) for event in plant.sync_events]


def _visited_modes(plant: RegionMultiComponent) -> list[ModeKey]:
    return [event["to_mode"] for event in plant.sync_events]


class TestRegionSwitchingInvariants:
    def test_time_driven_cycle_lives_in_the_external_signal_harness(self):
        """Scheduled demonstrations use time as a region key outside production code."""
        plant = _run_regions(
            lambda t: t,
            breakpoints=(0.1, 0.2, 0.3),
            modes=("A", "B", "C", "A"),
            band=0.005,
            dt=0.4,
            tf=0.4,
        )

        assert _visited_modes(plant) == ["B", "C", "A"]
        assert _switch_times(plant) == pytest.approx([0.105, 0.205, 0.305], abs=2e-6)

    def test_one_crossing_dispatches_exactly_one_transition(self):
        plant = _run_regions(
            lambda t: 100.0 * t,
            breakpoints=(5.0,),
            modes=("A", "B"),
            band=0.5,
            dt=0.2,
            tf=0.2,
        )

        assert _visited_modes(plant) == ["B"]
        assert _switch_times(plant) == pytest.approx([0.055], abs=2e-7)

    def test_motion_inside_the_band_does_not_switch_back(self):
        def signal(t: float) -> float:
            if t <= 0.01:
                return 600.0 * t
            return 6.0 - 120.0 * (t - 0.01)

        plant = _run_regions(
            signal,
            breakpoints=(5.0,),
            modes=("A", "B"),
            band=0.5,
            dt=0.01,
            tf=0.02,
        )

        assert _visited_modes(plant) == ["B"]
        assert plant.active_region_index == 1

    def test_full_band_recrossing_always_switches_without_elapsed_time_guard(self):
        def signal(t: float) -> float:
            if t <= 0.01:
                return 600.0 * t
            return 6.0 - 600.0 * (t - 0.01)

        plant = _run_regions(
            signal,
            breakpoints=(5.0,),
            modes=("A", "B"),
            band=0.5,
            dt=0.01,
            tf=0.02,
        )

        assert _visited_modes(plant) == ["B", "A"]
        first, second = _switch_times(plant)
        assert second - first < 0.01

    def test_repeated_model_assignments_keep_independent_region_identity(self):
        plant = _run_regions(
            lambda t: 100.0 * t,
            breakpoints=(5.0, 15.0, 25.0),
            modes=("A", "B", "A", "C"),
            band=0.5,
            dt=0.4,
            tf=0.4,
        )

        assert _visited_modes(plant) == ["B", "A", "C"]
        assert plant.active_region_index == 3
        assert plant.active_mode == "C"

    def test_multiple_boundaries_in_one_macro_step_are_chronological(self):
        plant = _run_regions(
            lambda t: 100.0 * t,
            breakpoints=(5.0, 15.0, 25.0),
            modes=("A", "B", "A", "C"),
            band=0.5,
            dt=0.4,
            tf=0.4,
        )

        assert _switch_times(plant) == pytest.approx([0.055, 0.155, 0.255], abs=2e-7)

    def test_switch_placement_is_independent_of_macro_step_size(self):
        placements = []
        for dt in (0.4, 0.073):
            plant = _run_regions(
                lambda t: 100.0 * t,
                breakpoints=(5.0, 15.0, 25.0),
                modes=("A", "B", "A", "C"),
                band=0.5,
                dt=dt,
                tf=0.4,
            )
            placements.append(_switch_times(plant))

        assert placements[0] == pytest.approx(placements[1], abs=2e-7)
        assert placements[0] == pytest.approx([0.055, 0.155, 0.255], abs=2e-7)
