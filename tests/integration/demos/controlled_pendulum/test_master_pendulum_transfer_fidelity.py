"""Transfer-fidelity characterization for every directed real backend pair.

The plant is driven by a constant torque so the FEM backend carries real
elastic state; without a drive there is nothing for a transfer to lose. The
configuration stays lightweight: one coarse first-order mesh, no wall contact,
no gravity, and no animation.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

pytest.importorskip("ngsolve")
pytest.importorskip("fmpy")
opensim = pytest.importorskip("opensim")

from demos.ControlledPendulum.src.master_pendulum.orchestration.master_pendulum import (  # noqa: E402
    MasterPendulum,
    PendulumTransferReport,
    PendulumTransferTolerances,
    transfer_state_semantics,
)
from tests.integration.demos.controlled_pendulum.real_backend_support import (  # noqa: E402
    build_real_plant,
    initialize_driven_plant,
    require_euler_pendulum_fmu,
)

pytestmark = [pytest.mark.integration, pytest.mark.fem, pytest.mark.fmu, pytest.mark.opensim]

T_FINAL = 7e-4
BREAKPOINTS = (1e-4, 2e-4, 3e-4, 4e-4, 5e-4, 6e-4)
BAND = 1e-5
MODES = ("FEM", "OpenSim", "FEM", "FMU", "OpenSim", "FMU", "FEM")
DIRECTED_PAIRS = tuple(zip(MODES[:-1], MODES[1:], strict=True))
FEM_SOURCE_PAIRS = tuple(pair for pair in DIRECTED_PAIRS if pair[0] == "FEM")
RIGID_SOURCE_PAIRS = tuple(pair for pair in DIRECTED_PAIRS if pair[0] != "FEM")

# A large drive keeps the elastic response of the coarse mesh well above the
# double-precision floor while the trajectory stays short.
DRIVE_TORQUE = 50.0

# Canonical invariants hold to round-off; the rigid interface carries them.
CANONICAL_TOLERANCE = 1e-12
ENERGY_TOLERANCE = 1e-12
# Acceleration is not carried across a transfer. Rigid backends still agree
# because they recompute it from the same torque and inertia; only the FEM
# proxy, which integrates the deformable field, differs.
RIGID_ACCELERATION_TOLERANCE = 1e-9
ACCELERATION_JUMP_LIMIT = 1e-3
# Elastic strain energy the coarse driven mesh is expected to hold.
MINIMUM_ELASTIC_ENERGY = 1e-6
STRAIN_FREE_ENERGY = 1e-12

require_euler_pendulum_fmu()


@pytest.fixture(scope="module", autouse=True)
def quiet_opensim_logging() -> Iterator[None]:
    previous_level = opensim.Logger.getLevelString()
    opensim.Logger.setLevelString("Error")
    yield
    opensim.Logger.setLevelString(previous_level)


@pytest.fixture(scope="module")
def driven_backend_run() -> Iterator[MasterPendulum]:
    """Drive one plant through every directed backend pair under load."""
    plant = build_real_plant(
        modes=MODES,
        breakpoints=BREAKPOINTS,
        band=BAND,
        key=lambda component: float(component.active_comp.t),
    )
    system = initialize_driven_plant(plant, torque=DRIVE_TORQUE)

    system.run(t0=0.0, tf=T_FINAL, dt=T_FINAL)

    yield plant
    plant.reset()


@pytest.fixture(scope="module")
def reports(
    driven_backend_run: MasterPendulum,
) -> dict[tuple[str, str], PendulumTransferReport]:
    """Map every directed backend pair to its accepted transfer report."""
    collected = {
        (event["from_mode"], event["to_mode"]): event["transfer_report"]
        for event in driven_backend_run.sync_events
    }
    assert tuple(collected) == DIRECTED_PAIRS
    return collected


def test_the_driven_trajectory_actually_loads_the_backends(
    reports: dict[tuple[str, str], PendulumTransferReport],
):
    for report in reports.values():
        assert report.source.tau == pytest.approx(DRIVE_TORQUE, abs=1e-9)
        assert report.target.tau == pytest.approx(DRIVE_TORQUE, abs=1e-9)
        assert abs(report.source.alpha) > 1.0


def test_every_directed_transfer_reports_measured_discontinuities(
    reports: dict[tuple[str, str], PendulumTransferReport],
    record_property,
):
    for (source_mode, target_mode), report in reports.items():
        measured = report.discontinuities

        assert set(measured) == {"theta", "omega", "alpha", "tau", "energy"}
        assert all(value >= 0.0 for value in measured.values())
        record_property(
            f"transfer[{source_mode}->{target_mode}]",
            {
                "time": report.time,
                **{name: value for name, value in measured.items()},
                "elastic_energy_lost": report.elastic_energy_lost,
                "total_energy_error": report.total_energy_error,
            },
        )


def test_canonical_state_and_rigid_energy_survive_every_transfer(
    reports: dict[tuple[str, str], PendulumTransferReport],
):
    for report in reports.values():
        assert report.theta_error <= CANONICAL_TOLERANCE
        assert report.omega_error <= CANONICAL_TOLERANCE
        assert report.tau_error <= CANONICAL_TOLERANCE
        assert report.energy_error <= ENERGY_TOLERANCE
        assert report.violations(PendulumTransferTolerances()) == ()


@pytest.mark.parametrize(("source_mode", "target_mode"), FEM_SOURCE_PAIRS)
def test_leaving_fem_drops_the_whole_elastic_strain_energy(
    reports: dict[tuple[str, str], PendulumTransferReport], source_mode, target_mode
):
    report = reports[(source_mode, target_mode)]

    assert report.source_energy.elastic is not None
    assert report.source_energy.elastic > MINIMUM_ELASTIC_ENERGY
    assert report.target_energy.elastic is None
    assert report.elastic_energy_lost == pytest.approx(report.source_energy.elastic)
    assert report.total_energy_error == pytest.approx(report.elastic_energy_lost)


@pytest.mark.parametrize(("source_mode", "target_mode"), RIGID_SOURCE_PAIRS)
def test_a_rigid_source_carries_no_elastic_energy(
    reports: dict[tuple[str, str], PendulumTransferReport], source_mode, target_mode
):
    report = reports[(source_mode, target_mode)]

    assert report.source_energy.elastic is None
    if target_mode == "FEM":
        # Re-entering FEM rebuilds a rigid, strain-free configuration.
        assert report.target_energy.elastic is not None
        assert report.target_energy.elastic < STRAIN_FREE_ENERGY
    else:
        assert report.target_energy.elastic is None
    assert report.total_energy_error <= ENERGY_TOLERANCE


def test_acceleration_is_discontinuous_only_when_the_fem_state_is_left_behind(
    reports: dict[tuple[str, str], PendulumTransferReport],
):
    for pair in RIGID_SOURCE_PAIRS:
        assert reports[pair].alpha_error <= RIGID_ACCELERATION_TOLERANCE

    for pair in FEM_SOURCE_PAIRS:
        report = reports[pair]
        assert report.alpha_error > RIGID_ACCELERATION_TOLERANCE
        assert report.alpha_error <= ACCELERATION_JUMP_LIMIT


@pytest.mark.parametrize(("source_mode", "target_mode"), DIRECTED_PAIRS)
def test_each_report_declares_the_state_it_preserves_and_loses(
    reports: dict[tuple[str, str], PendulumTransferReport], source_mode, target_mode
):
    semantics = reports[(source_mode, target_mode)].semantics

    assert semantics == transfer_state_semantics(source_mode, target_mode)
    assert semantics.preserved == ("theta", "omega", "tau")
    assert "alpha" in semantics.lost


def test_declared_losses_match_what_the_measurement_shows(
    reports: dict[tuple[str, str], PendulumTransferReport],
):
    for pair, report in reports.items():
        semantics = report.semantics
        source_mode = pair[0]

        # Every preserved name is a measured quantity that stayed continuous.
        for name in semantics.preserved:
            assert report.discontinuities[name] <= CANONICAL_TOLERANCE

        if source_mode == "FEM":
            assert "elastic strain energy" in semantics.lost
            assert "Newmark step history" in semantics.lost
            assert "contact gap history" in semantics.lost
            assert report.elastic_energy_lost > MINIMUM_ELASTIC_ENERGY
        if source_mode == "OpenSim":
            assert "integrator step-size and error history" in semantics.lost
        if source_mode == "FMU":
            assert any("canGetAndSetFMUstate" in entry for entry in semantics.lost)
