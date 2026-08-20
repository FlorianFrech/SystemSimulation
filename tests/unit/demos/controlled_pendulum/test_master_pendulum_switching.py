"""Configuration tests for the production master-pendulum region policy."""

import numpy as np
import pytest

master_pendulum = pytest.importorskip(
    "demos.ControlledPendulum.src.master_pendulum.orchestration.master_pendulum"
)

MasterPendulum = master_pendulum.MasterPendulum


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
