"""Configuration tests for the production master-pendulum region policy."""

import numpy as np
import pytest

master_pendulum = pytest.importorskip(
    "demos.ControlledPendulum.src.master_pendulum.orchestration.master_pendulum"
)

MasterPendulum = master_pendulum.MasterPendulum
PendulumState = master_pendulum.PendulumState
PendulumTransferReport = master_pendulum.PendulumTransferReport
PendulumTransferTolerances = master_pendulum.PendulumTransferTolerances


def test_default_master_pendulum_declares_three_angle_regions():
    plant = MasterPendulum()

    assert plant.switch_regions is not None
    assert plant.switch_regions.modes == ("FEM", "OpenSim", "FMU")
    assert plant.switch_regions.breakpoints == pytest.approx((0.075, np.deg2rad(15.0)))
    assert plant.switch_regions.bands == pytest.approx((0.005, np.deg2rad(1.0)))
    assert len(plant.event_indicators) == 2


def test_none_switch_config_keeps_one_fixed_model():
    plant = MasterPendulum(initial_mode="OpenSim", switch_config=None)

    assert plant.switch_regions is None
    assert plant.active_mode == "OpenSim"
    assert not plant.event_indicators


def test_master_pendulum_declares_feedthrough_before_backend_initialization():
    plant = MasterPendulum(switch_config=None)

    assert plant.direct_feedthrough == {
        "theta": set(),
        "omega": set(),
        "alpha": {"tau"},
    }


def test_canonical_pendulum_state_normalizes_backend_units():
    state = PendulumState.from_mapping(
        {
            "theta": {"value": 180.0, "unit": "degree"},
            "omega": {"value": 90.0, "unit": "degree/s"},
            "tau": {"value": 2.0, "unit": "N*m"},
        }
    )

    assert state.theta == pytest.approx(np.pi)
    assert state.omega == pytest.approx(np.pi / 2.0)
    assert state.tau == pytest.approx(2.0)


@pytest.mark.parametrize("value", [-1.0, np.inf, np.nan])
def test_transfer_tolerances_require_finite_nonnegative_values(value):
    with pytest.raises(ValueError, match="finite and nonnegative"):
        PendulumTransferTolerances(theta=value)


def test_transfer_report_identifies_each_discontinuous_quantity():
    report = PendulumTransferReport(
        source_mode="FEM",
        target_mode="FMU",
        time=0.1,
        source=PendulumState(theta=0.0, omega=0.0, tau=0.0),
        target=PendulumState(theta=0.2, omega=0.3, tau=0.4),
    )

    assert report.violations(PendulumTransferTolerances(theta=0.1, omega=0.2, tau=0.3)) == (
        "theta",
        "omega",
        "tau",
    )
