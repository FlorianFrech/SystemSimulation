"""Configuration tests for the production master-pendulum region policy."""

import numpy as np
import pytest

master_pendulum = pytest.importorskip(
    "demos.ControlledPendulum.src.master_pendulum.orchestration.master_pendulum"
)

BACKEND_STATE_SEMANTICS = master_pendulum.BACKEND_STATE_SEMANTICS
MasterPendulum = master_pendulum.MasterPendulum
PendulumEnergy = master_pendulum.PendulumEnergy
PendulumState = master_pendulum.PendulumState
PendulumTransferReport = master_pendulum.PendulumTransferReport
PendulumTransferTolerances = master_pendulum.PendulumTransferTolerances
RigidPendulumProperties = master_pendulum.RigidPendulumProperties
transfer_state_semantics = master_pendulum.transfer_state_semantics

MODES = ("FEM", "OpenSim", "FMU")
DIRECTED_PAIRS = tuple((source, target) for source in MODES for target in MODES if source != target)


def _report(**overrides):
    """Build a transfer report whose canonical quantities are all continuous."""
    defaults = {
        "source_mode": "FEM",
        "target_mode": "FMU",
        "time": 0.1,
        "source": PendulumState(theta=0.0, omega=0.0, alpha=0.0, tau=0.0),
        "target": PendulumState(theta=0.0, omega=0.0, alpha=0.0, tau=0.0),
        "source_energy": PendulumEnergy(kinetic=0.0, potential=0.0),
        "target_energy": PendulumEnergy(kinetic=0.0, potential=0.0),
    }
    return PendulumTransferReport(**(defaults | overrides))


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


def test_reset_before_backend_initialization_is_safe():
    plant = MasterPendulum(switch_config=None)

    plant.reset()

    assert plant.active_mode == "FMU"
    assert plant.active_region_index is None
    assert plant.sync_events == []
    assert all(not model._is_initialized for model in plant.models.values())


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
            "alpha": {"value": 180.0, "unit": "degree/s**2"},
            "tau": {"value": 2.0, "unit": "N*m"},
        }
    )

    assert state.theta == pytest.approx(np.pi)
    assert state.omega == pytest.approx(np.pi / 2.0)
    assert state.alpha == pytest.approx(np.pi)
    assert state.tau == pytest.approx(2.0)


@pytest.mark.parametrize("unit", ["rad/s**2", "rad/s^2", "rad/s2"])
def test_canonical_state_accepts_every_backend_acceleration_spelling(unit):
    state = PendulumState.from_mapping(
        {
            "theta": {"value": 0.0, "unit": "rad"},
            "omega": {"value": 0.0, "unit": "rad/s"},
            "alpha": {"value": 1.5, "unit": unit},
            "tau": {"value": 0.0, "unit": "N.m"},
        }
    )

    assert state.alpha == pytest.approx(1.5)


@pytest.mark.parametrize("value", [-1.0, np.inf, np.nan])
def test_transfer_tolerances_require_finite_nonnegative_values(value):
    with pytest.raises(ValueError, match="finite and nonnegative"):
        PendulumTransferTolerances(theta=value)


def test_acceleration_and_energy_tolerances_are_unenforced_by_default():
    tolerances = PendulumTransferTolerances()

    assert tolerances.alpha is None
    assert tolerances.energy is None


def test_transfer_report_identifies_each_discontinuous_quantity():
    report = _report(target=PendulumState(theta=0.2, omega=0.3, alpha=0.0, tau=0.4))

    assert report.violations(PendulumTransferTolerances(theta=0.1, omega=0.2, tau=0.3)) == (
        "theta",
        "omega",
        "tau",
    )


def test_transfer_report_measures_acceleration_and_energy_without_enforcing_them():
    report = _report(
        target=PendulumState(theta=0.0, omega=0.0, alpha=7.5, tau=0.0),
        target_energy=PendulumEnergy(kinetic=1.0, potential=0.25),
    )

    assert report.alpha_error == pytest.approx(7.5)
    assert report.energy_error == pytest.approx(1.25)
    assert report.violations(PendulumTransferTolerances()) == ()
    assert report.violations(PendulumTransferTolerances(alpha=1.0, energy=1.0)) == (
        "alpha",
        "energy",
    )


def test_transfer_report_accounts_for_strain_energy_lost_when_leaving_fem():
    report = _report(
        source_energy=PendulumEnergy(kinetic=2.0, potential=0.0, elastic=0.5),
        target_energy=PendulumEnergy(kinetic=2.0, potential=0.0),
    )

    assert report.source_energy.total == pytest.approx(2.5)
    assert report.target_energy.total == pytest.approx(2.0)
    assert report.energy_error == pytest.approx(0.0)
    assert report.elastic_energy_lost == pytest.approx(0.5)
    assert report.total_energy_error == pytest.approx(0.5)


def test_rigid_properties_use_the_pivot_as_the_potential_energy_datum():
    properties = RigidPendulumProperties(mass=2.0, length=0.5, inertia=0.4, gravity=10.0)

    energy = properties.energy(PendulumState(theta=np.pi, omega=3.0, alpha=0.0, tau=0.0))

    assert energy.kinetic == pytest.approx(0.5 * 0.4 * 9.0)
    assert energy.potential == pytest.approx(2.0 * 10.0 * 0.5 * 2.0)
    assert energy.elastic is None
    assert energy.total == pytest.approx(energy.mechanical)


def test_disabled_gravity_removes_the_potential_energy_term():
    properties = RigidPendulumProperties(mass=2.0, length=0.5, inertia=0.4, gravity=0.0)

    energy = properties.energy(PendulumState(theta=1.0, omega=0.0, alpha=0.0, tau=0.0))

    assert energy.potential == pytest.approx(0.0)


def test_rigid_properties_reject_a_massless_or_singular_configuration():
    with pytest.raises(ValueError, match="must be nonzero"):
        RigidPendulumProperties(mass=1.0, length=1.0, inertia=0.0, gravity=9.81)


@pytest.mark.parametrize(("source_mode", "target_mode"), DIRECTED_PAIRS)
def test_every_directed_transfer_declares_its_state_semantics(source_mode, target_mode):
    semantics = transfer_state_semantics(source_mode, target_mode)

    assert semantics.preserved == ("theta", "omega", "tau")
    assert "alpha" in semantics.lost
    assert semantics.reconstructed == BACKEND_STATE_SEMANTICS[target_mode].reconstructed
    assert set(BACKEND_STATE_SEMANTICS[source_mode].discarded) <= set(semantics.lost)
    assert not set(semantics.preserved) & set(semantics.lost)


@pytest.mark.parametrize("target_mode", ["OpenSim", "FMU"])
def test_leaving_fem_loses_the_flexible_and_contact_state(target_mode):
    semantics = transfer_state_semantics("FEM", target_mode)

    assert "elastic deformation" in semantics.lost
    assert "elastic strain energy" in semantics.lost
    assert "contact gap history" in semantics.lost
    assert "Newmark step history" in semantics.lost


@pytest.mark.parametrize("source_mode", ["OpenSim", "FMU"])
def test_entering_fem_reconstructs_only_rigid_fields(source_mode):
    semantics = transfer_state_semantics(source_mode, "FEM")

    assert semantics.reconstructed == (
        "rigid displacement field",
        "rigid velocity field",
        "rigid acceleration field from the rigid torque balance",
        "Newmark previous-step vectors set equal to the current step",
    )


def test_transfers_declare_lost_solver_history_for_every_backend():
    assert (
        "integrator step-size and error history" in transfer_state_semantics("OpenSim", "FEM").lost
    )
    assert any(
        "canGetAndSetFMUstate" in entry for entry in transfer_state_semantics("FMU", "FEM").lost
    )


def test_unknown_backend_mode_is_rejected():
    with pytest.raises(ValueError, match="Unknown pendulum backend mode"):
        transfer_state_semantics("FEM", "Modelica")


def test_transfer_report_before_initialization_is_rejected():
    plant = MasterPendulum(switch_config=None)

    assert plant.rigid_properties is None
    with pytest.raises(RuntimeError, match="Rigid properties are unavailable"):
        plant._build_transfer_report({}, {}, "FEM", "FMU", 0.0)
