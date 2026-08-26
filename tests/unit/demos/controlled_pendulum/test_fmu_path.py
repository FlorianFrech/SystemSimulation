"""Tests for controlled-pendulum FMU artifact resolution."""

from pathlib import Path

import pytest

from syssimx_examples.controlled_pendulum.components.fmu.fmu_pendulum import (
    FMUPendulum,
    repository_fmu_path,
)


@pytest.mark.parametrize("solver", ["euler", "cvode"])
def test_repository_fmu_path_resolves_checked_in_artifact(solver):
    path = repository_fmu_path(solver)

    assert path.is_file()
    assert path.name == f"Pendulum_{solver}.fmu"
    assert path.parts[-2:] == ("Plants", f"Pendulum_{solver}.fmu")


def test_repository_fmu_path_can_target_an_explicit_platform():
    path = repository_fmu_path("cvode", platform="linux")

    assert isinstance(path, Path)
    assert path.parts[-3:] == ("linux", "Plants", "Pendulum_cvode.fmu")


def test_repository_fmu_path_rejects_unknown_solver():
    with pytest.raises(ValueError, match="Unsupported FMU solver"):
        repository_fmu_path("rk4")  # type: ignore[arg-type]


def test_fmu_pendulum_explains_missing_external_artifact(tmp_path):
    missing = tmp_path / "Pendulum_cvode.fmu"

    with pytest.raises(FileNotFoundError, match="not included in the SysSimX wheel"):
        FMUPendulum(name="Pendulum", fmu_path=missing)
