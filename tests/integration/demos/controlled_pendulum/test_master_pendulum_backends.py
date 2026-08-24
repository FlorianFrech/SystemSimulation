"""Fast real-backend validation for transactional pendulum switching."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock

import numpy as np
import pytest

pytest.importorskip("ngsolve")
pytest.importorskip("fmpy")
opensim = pytest.importorskip("opensim")

from demos.ControlledPendulum.src.master_pendulum.orchestration.master_pendulum import (  # noqa: E402
    MasterPendulum,
    PendulumState,
    PendulumTransferReport,
)
from tests.integration.demos.controlled_pendulum.real_backend_support import (  # noqa: E402
    assert_same_pendulum_state,
    build_real_plant,
    fem_state_snapshot,
    history_snapshot,
    initialize_real_plant,
    monitor_snapshot,
    port_snapshot,
    require_euler_pendulum_fmu,
)

pytestmark = [pytest.mark.integration, pytest.mark.fem, pytest.mark.fmu, pytest.mark.opensim]

T_FINAL = 7e-4
BREAKPOINTS = (1e-4, 2e-4, 3e-4, 4e-4, 5e-4, 6e-4)
BAND = 1e-5
EVENT_TIME_TOLERANCE = 2e-6
MODES = ("FEM", "OpenSim", "FEM", "FMU", "OpenSim", "FMU", "FEM")
EXPECTED_TRANSITIONS = tuple(zip(MODES[:-1], MODES[1:], strict=True))
LIFECYCLE_BREAKPOINTS = (1e-4, 2e-4)
LIFECYCLE_MODES = ("FEM", "OpenSim", "FMU")

require_euler_pendulum_fmu()


@pytest.fixture(scope="module", autouse=True)
def quiet_opensim_logging() -> Iterator[None]:
    previous_level = opensim.Logger.getLevelString()
    opensim.Logger.setLevelString("Error")
    yield
    opensim.Logger.setLevelString(previous_level)


def _build_real_plant(
    *,
    modes: tuple[str, ...] = MODES,
    breakpoints: tuple[float, ...] = BREAKPOINTS,
) -> MasterPendulum:
    """Build the scheduled-switching plant used by this module."""
    return build_real_plant(
        modes=modes,
        breakpoints=breakpoints,
        band=BAND,
        # Scheduled switching belongs to this external validation harness. The
        # active child's trial time makes event localization observable.
        key=lambda component: float(component.active_comp.t),
    )


@pytest.fixture(scope="module")
def real_backend_run() -> Iterator[MasterPendulum]:
    """Run every directed backend pair once in one 0.7 ms simulation."""
    plant = _build_real_plant()
    system = initialize_real_plant(plant)

    system.run(t0=0.0, tf=T_FINAL, dt=T_FINAL)

    yield plant
    plant.reset()


def test_real_backends_cover_every_directed_transfer(real_backend_run: MasterPendulum):
    events = real_backend_run.sync_events
    actual_transitions = tuple((event["from_mode"], event["to_mode"]) for event in events)
    expected_times = [breakpoint + BAND for breakpoint in BREAKPOINTS]

    assert actual_transitions == EXPECTED_TRANSITIONS
    assert [event["time"] for event in events] == pytest.approx(
        expected_times, abs=EVENT_TIME_TOLERANCE
    )
    assert real_backend_run.active_region_index == len(MODES) - 1
    assert real_backend_run.active_mode == "FEM"


def test_real_backend_transfers_preserve_canonical_physical_state(
    real_backend_run: MasterPendulum,
):
    reports = [event["transfer_report"] for event in real_backend_run.sync_events]

    assert len(reports) == len(EXPECTED_TRANSITIONS)
    assert all(isinstance(report, PendulumTransferReport) for report in reports)
    assert (
        tuple((report.source_mode, report.target_mode) for report in reports)
        == EXPECTED_TRANSITIONS
    )
    assert all(report.violations(real_backend_run.transfer_tolerances) == () for report in reports)


def test_no_contact_free_motion_remains_physical(real_backend_run: MasterPendulum):
    final_state = PendulumState.from_mapping(real_backend_run.get_state())
    expected_theta = np.deg2rad(5.0) + 0.2 * T_FINAL

    assert real_backend_run.fem._with_contact is False
    assert real_backend_run.opensim._with_contact is False
    assert final_state.theta == pytest.approx(expected_theta, abs=5e-8)
    assert final_state.omega == pytest.approx(0.2, abs=1e-8)
    assert final_state.tau == pytest.approx(0.0, abs=1e-10)


def test_real_backend_reset_reinitialize_matches_fresh_instance(monkeypatch):
    restart_time = 1e-3
    reused = _build_real_plant(
        modes=LIFECYCLE_MODES,
        breakpoints=LIFECYCLE_BREAKPOINTS,
    )
    fresh = _build_real_plant(
        modes=LIFECYCLE_MODES,
        breakpoints=LIFECYCLE_BREAKPOINTS,
    )
    try:
        system = initialize_real_plant(reused)
        system.run(t0=0.0, tf=3e-4, dt=3e-4)
        assert reused.active_mode == "FMU"

        old_instance = reused.fmu._instance
        old_unzipdir = Path(reused.fmu._unzipdir)
        terminate = Mock(wraps=old_instance.terminate)
        free_instance = Mock(wraps=old_instance.freeInstance)
        monkeypatch.setattr(old_instance, "terminate", terminate)
        monkeypatch.setattr(old_instance, "freeInstance", free_instance)
        old_opensim_model = reused.opensim.model
        old_opensim_state = reused.opensim.state
        old_opensim_manager = reused.opensim.manager

        system.reset()

        # Release is governed by the archive's static policy, not by a blanket
        # workaround (issues.md HARD-05 step 1). This plant is built with the
        # euler export, which tolerates teardown, so reset() must actually
        # terminate and free. The extraction directory survives either way: it
        # is shared through the module-level cache (issues.md HARD-07 step 1).
        policy = reused.fmu.release_policy
        assert policy.releasable, policy.reason
        assert terminate.call_count == 1
        assert free_instance.call_count == 1
        assert not system.is_initialized
        assert reused.fmu._instance is None
        assert Path(reused.fmu._unzipdir) == old_unzipdir
        assert old_unzipdir.is_dir()
        assert reused.opensim.model is None
        assert reused.opensim.state is None
        assert reused.opensim.manager is None
        assert reused.rigid_properties is None

        system.initialize(restart_time)
        reused.set_inputs({"tau": 0.0}, t=restart_time)
        fresh_system = initialize_real_plant(fresh, t0=restart_time)

        assert system.is_initialized == fresh_system.is_initialized is True
        assert reused.active_region_index == fresh.active_region_index == 2
        assert reused.active_mode == fresh.active_mode == "FMU"
        assert reused.sync_events == fresh.sync_events == []
        assert reused.t == fresh.t == restart_time
        assert reused.rigid_properties == fresh.rigid_properties
        assert reused.opensim.model is not old_opensim_model
        assert reused.opensim.state is not old_opensim_state
        assert reused.opensim.manager is not old_opensim_manager
        assert port_snapshot(reused) == port_snapshot(fresh)
        assert history_snapshot(reused) == history_snapshot(fresh)
        assert monitor_snapshot(reused.monitoring_state) == monitor_snapshot(fresh.monitoring_state)
        for mode in reused.models:
            assert_same_pendulum_state(
                PendulumState.from_mapping(reused.models[mode].get_state()),
                PendulumState.from_mapping(fresh.models[mode].get_state()),
            )
            assert port_snapshot(reused.models[mode]) == port_snapshot(fresh.models[mode])
            assert history_snapshot(reused.models[mode]) == history_snapshot(fresh.models[mode])
    finally:
        reused.reset()
        fresh.reset()


def test_failed_real_target_validation_restores_the_transaction(monkeypatch):
    plant = _build_real_plant(modes=("FEM", "FMU"), breakpoints=(1e-4,))
    try:
        initialize_real_plant(plant)
        plant.set_inputs({"tau": 0.01}, t=0.0)
        components = {"wrapper": plant, **plant.models}
        ports_before = {name: port_snapshot(comp) for name, comp in components.items()}
        histories_before = {name: history_snapshot(comp) for name, comp in components.items()}
        states_before = {
            mode: PendulumState.from_mapping(model.get_state())
            for mode, model in plant.models.items()
        }
        fem_before = fem_state_snapshot(plant)
        master_monitor_before = monitor_snapshot(plant.monitoring_state)
        fem_monitor_before = monitor_snapshot(plant.fem.monitoring_state)
        target_instance = plant.fmu._instance
        target_unzipdir = plant.fmu._unzipdir
        terminate_instance = Mock(wraps=target_instance.terminate)
        free_instance = Mock(wraps=target_instance.freeInstance)
        instantiate_instance = Mock(wraps=target_instance.instantiate)
        monkeypatch.setattr(target_instance, "terminate", terminate_instance)
        monkeypatch.setattr(target_instance, "freeInstance", free_instance)
        monkeypatch.setattr(target_instance, "instantiate", instantiate_instance)

        def reject_transfer(*_args):
            raise RuntimeError("real target continuity rejected")

        monkeypatch.setattr(plant, "_build_transfer_report", reject_transfer)

        with pytest.raises(RuntimeError, match="real target continuity rejected"):
            plant._switch_region(1, t=0.0)

        assert plant.active_region_index == 0
        assert plant.active_mode == "FEM"
        assert plant.t == 0.0
        assert plant.sync_events == []
        assert plant.fmu._instance is not target_instance
        assert plant.fmu._unzipdir == target_unzipdir
        # Rollback recreates the slave, releasing the outgoing one when the
        # archive tolerates it (issues.md HARD-05 step 1). This plant uses the
        # euler export, so the old instance is terminated and freed rather than
        # stranded. The mocked instance is the released one, so its own
        # instantiate() is never called again; the replacement is a new object.
        policy = plant.fmu.release_policy
        assert policy.releasable, policy.reason
        assert terminate_instance.call_count == 1
        assert free_instance.call_count == 1
        instantiate_instance.assert_not_called()
        assert fem_state_snapshot(plant) == fem_before
        assert monitor_snapshot(plant.monitoring_state) == master_monitor_before
        assert monitor_snapshot(plant.fem.monitoring_state) == fem_monitor_before
        for name, comp in components.items():
            assert port_snapshot(comp) == ports_before[name]
            assert history_snapshot(comp) == histories_before[name]
        for mode, model in plant.models.items():
            assert_same_pendulum_state(
                PendulumState.from_mapping(model.get_state()), states_before[mode]
            )
    finally:
        plant.reset()


def test_real_trial_advances_are_observationally_pure(monkeypatch, caplog):
    plant = _build_real_plant(
        modes=LIFECYCLE_MODES,
        breakpoints=LIFECYCLE_BREAKPOINTS,
    )
    try:
        initialize_real_plant(plant)
        plant.fem.anim_params.animate = True
        update_master_monitor = Mock()
        update_fem_monitor = Mock()
        redraw_fem = Mock()
        update_fem_scene = Mock()
        monkeypatch.setattr(plant, "_update_monitoring", update_master_monitor)
        monkeypatch.setattr(plant.fem, "update_monitoring", update_fem_monitor)
        monkeypatch.setattr(plant.fem._viz, "redraw", redraw_fem)
        monkeypatch.setattr(plant.fem, "update_scene", update_fem_scene)

        for region_index, mode in enumerate(LIFECYCLE_MODES):
            if region_index:
                plant._switch_region(region_index, t=0.0, record=False)
            components = {"wrapper": plant, **plant.models}
            ports_before = {name: port_snapshot(comp) for name, comp in components.items()}
            histories_before = {name: history_snapshot(comp) for name, comp in components.items()}
            fem_frames_before = tuple(
                len(history.vecs)
                for history in (
                    plant.fem._gf_u_history,
                    plant.fem._gf_v_history,
                    plant.fem._gf_cauchy_stress_history,
                    plant.fem._gf_von_mises_history,
                )
            )
            master_monitor_before = monitor_snapshot(plant.monitoring_state)
            fem_monitor_before = monitor_snapshot(plant.fem.monitoring_state)
            switch_log_before = deepcopy(plant.sync_events)
            checkpoint = plant.checkpoint()

            caplog.clear()
            with caplog.at_level(logging.INFO):
                with plant.trial_context():
                    plant.do_step(0.0, 5e-5)
                plant.restore_checkpoint(checkpoint)

            assert plant.active_mode == mode
            assert plant.active_region_index == region_index
            assert plant.t == 0.0
            assert plant.sync_events == switch_log_before
            assert monitor_snapshot(plant.monitoring_state) == master_monitor_before
            assert monitor_snapshot(plant.fem.monitoring_state) == fem_monitor_before
            assert (
                tuple(
                    len(history.vecs)
                    for history in (
                        plant.fem._gf_u_history,
                        plant.fem._gf_v_history,
                        plant.fem._gf_cauchy_stress_history,
                        plant.fem._gf_von_mises_history,
                    )
                )
                == fem_frames_before
            )
            for name, comp in components.items():
                assert port_snapshot(comp) == ports_before[name]
                assert history_snapshot(comp) == histories_before[name]
            assert not [
                record
                for record in caplog.records
                if record.name.startswith(("syssimx", "demos.ControlledPendulum"))
            ]

        update_master_monitor.assert_not_called()
        update_fem_monitor.assert_not_called()
        redraw_fem.assert_not_called()
        update_fem_scene.assert_not_called()
    finally:
        plant.reset()
