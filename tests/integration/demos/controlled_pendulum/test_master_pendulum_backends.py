"""Fast real-backend validation for transactional pendulum switching."""

from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("ngsolve")
pytest.importorskip("fmpy")
opensim = pytest.importorskip("opensim")

from demos.ControlledPendulum.src.master_pendulum.components.fem import (  # noqa: E402
    pendulum_config as cfg,
)
from demos.ControlledPendulum.src.master_pendulum.orchestration.master_pendulum import (  # noqa: E402
    MasterPendulum,
    PendulumState,
    PendulumTransferReport,
)
from syssimx.system.algorithms.hybrid import HybridAlgorithm  # noqa: E402
from syssimx.system.system import System  # noqa: E402

pytestmark = [pytest.mark.integration, pytest.mark.fem, pytest.mark.fmu, pytest.mark.opensim]

T_FINAL = 7e-4
BREAKPOINTS = (1e-4, 2e-4, 3e-4, 4e-4, 5e-4, 6e-4)
BAND = 1e-5
EVENT_TIME_TOLERANCE = 2e-6
MODES = ("FEM", "OpenSim", "FEM", "FMU", "OpenSim", "FMU", "FEM")
EXPECTED_TRANSITIONS = tuple(zip(MODES[:-1], MODES[1:], strict=True))

REPOSITORY_ROOT = Path(__file__).parents[4]
FMU_PATH = (
    REPOSITORY_ROOT
    / "demos"
    / "ControlledPendulum"
    / "artifacts"
    / "fmus"
    / sys.platform
    / "Plants"
    / "Pendulum_euler.fmu"
)
if not FMU_PATH.is_file():
    pytest.skip(f"No Euler pendulum FMU for {sys.platform}: {FMU_PATH}", allow_module_level=True)


@pytest.fixture(scope="module", autouse=True)
def quiet_opensim_logging() -> Iterator[None]:
    previous_level = opensim.Logger.getLevelString()
    opensim.Logger.setLevelString("Error")
    yield
    opensim.Logger.setLevelString(previous_level)


@pytest.fixture(scope="module")
def real_backend_run() -> Iterator[MasterPendulum]:
    """Run every directed backend pair once in one 0.7 ms simulation."""
    mesh_params = cfg.MeshParameters(
        max_element_size=0.08,
        mesh_order=1,
        curved_elements=False,
    )
    init_params = cfg.InitialConditionParameters(
        angular_position_deg=5.0,
        angular_velocity=0.2,
        drive_torque=0.0,
    )
    sim_params = cfg.SimulationParameters(
        tau=1e-4,
        t_end=T_FINAL,
        use_gravity=False,
        with_contact=False,
    )
    anim_params = cfg.AnimationParameters(animate=False)

    plant = MasterPendulum(
        initial_mode="FEM",
        fmu_solver="euler",
        switch_config=None,
    )
    plant.set_parameters(
        FEM={
            "mesh_params": mesh_params,
            "init_params": init_params,
            "sim_params": sim_params,
            "anim_params": anim_params,
        }
    )
    plant.set_switch_regions(
        # Scheduled switching belongs to this external validation harness. The
        # active child's trial time makes event localization observable.
        key=lambda component: float(component.active_comp.t),
        breakpoints=BREAKPOINTS,
        modes=MODES,
        band=BAND,
    )

    system = System(name="RealBackendSwitching")
    system.add_component(plant)
    algorithm = HybridAlgorithm()
    algorithm.verbose = False
    algorithm.tol_time = 1e-9
    algorithm.tol_value = 1e-12
    system.algorithm = algorithm
    system.initialize(t0=0.0)
    plant.set_inputs({"tau": 0.0}, t=0.0)
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
