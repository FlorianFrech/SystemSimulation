"""Shared harness for the fast real-backend master-pendulum tests.

Every consumer keeps its own ``pytest.importorskip`` guards and calls
:func:`require_euler_pendulum_fmu` at module level before importing this
module, so an environment without NGSolve, fmpy, OpenSim, or a platform FMU
skips before any backend is touched.

The configuration is deliberately lightweight: one coarse first-order mesh,
no wall contact, no gravity, and no animation.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from demos.ControlledPendulum.src.master_pendulum.components.fem import pendulum_config as cfg
from demos.ControlledPendulum.src.master_pendulum.orchestration.master_pendulum import (
    MasterPendulum,
    MasterPendulumSwitchConfig,
    PendulumState,
)
from syssimx.system.algorithms.hybrid import HybridAlgorithm
from syssimx.system.system import System

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

SIMULATION_END = 2e-3
MESH_ELEMENT_SIZE = 0.08
FEM_STEP = 1e-4
TOL_TIME = 1e-9
TOL_VALUE = 1e-12


def require_euler_pendulum_fmu() -> None:
    """Skip the calling module when this platform has no Euler pendulum FMU."""
    if not FMU_PATH.is_file():
        pytest.skip(
            f"No Euler pendulum FMU for {sys.platform}: {FMU_PATH}", allow_module_level=True
        )


def build_real_plant(
    *,
    modes: tuple[str, ...],
    breakpoints: tuple[float, ...],
    band: float | tuple[float, ...],
    key: Callable[[Any], float],
    angular_position_deg: float = 5.0,
    angular_velocity: float = 0.2,
    initial_mode: str = "FEM",
    fem_step: float = FEM_STEP,
) -> MasterPendulum:
    """Build the shared coarse, contact-free real-backend configuration."""
    plant = MasterPendulum(
        initial_mode=initial_mode,
        fmu_solver="euler",
        switch_config=None,
    )
    plant.set_parameters(
        FEM={
            "mesh_params": cfg.MeshParameters(
                max_element_size=MESH_ELEMENT_SIZE,
                mesh_order=1,
                curved_elements=False,
            ),
            "init_params": cfg.InitialConditionParameters(
                angular_position_deg=angular_position_deg,
                angular_velocity=angular_velocity,
                drive_torque=0.0,
            ),
            "sim_params": cfg.SimulationParameters(
                tau=fem_step,
                t_end=SIMULATION_END,
                use_gravity=False,
                with_contact=False,
            ),
            "anim_params": cfg.AnimationParameters(animate=False),
        }
    )
    plant.set_switch_regions(key=key, breakpoints=breakpoints, modes=modes, band=band)
    return plant


def build_angle_region_plant(
    *,
    angular_position_deg: float,
    angular_velocity: float,
    initial_mode: str = "FEM",
    switch_config: MasterPendulumSwitchConfig | None = None,
) -> MasterPendulum:
    """Build a plant governed by the production ``abs(theta)`` region policy."""
    config = switch_config or MasterPendulumSwitchConfig()
    return build_real_plant(
        modes=config.modes,
        breakpoints=config.breakpoints,
        band=config.bands,
        key=MasterPendulum._absolute_theta,
        angular_position_deg=angular_position_deg,
        angular_velocity=angular_velocity,
        initial_mode=initial_mode,
    )


def make_hybrid_algorithm() -> HybridAlgorithm:
    """Return the quiet, tightly localized algorithm used by every harness."""
    algorithm = HybridAlgorithm()
    algorithm.verbose = False
    algorithm.tol_time = TOL_TIME
    algorithm.tol_value = TOL_VALUE
    return algorithm


def initialize_real_plant(
    plant: MasterPendulum, t0: float = 0.0, name: str = "RealBackendSwitching"
) -> System:
    """Initialize ``plant`` alone in a system with a zero torque input."""
    system = System(name=name)
    system.add_component(plant)
    system.algorithm = make_hybrid_algorithm()
    system.initialize(t0=t0)
    plant.set_inputs({"tau": 0.0}, t=t0)
    return system


def plain(value: Any) -> Any:
    """Strip units from a port value so snapshots compare by magnitude."""
    if value is None or isinstance(value, (bool, str)):
        return value
    return float(getattr(value, "magnitude", value))


def port_snapshot(component) -> dict[str, dict[str, tuple[Any, float | None]]]:
    return {
        direction: {name: (plain(port.get()), port.t_last) for name, port in ports.items()}
        for direction, ports in (("inputs", component.inputs), ("outputs", component.outputs))
    }


def history_snapshot(component) -> dict[str, tuple[tuple[float, ...], tuple[Any, ...]]]:
    return {
        name: (
            tuple(float(t) for t in data["time"]),
            tuple(plain(value) for value in data["values"]),
        )
        for name, data in component.get_history().items()
    }


def monitor_snapshot(state) -> tuple[Any, ...]:
    return tuple(getattr(state, name) for name in state.traits() if not name.startswith("_"))


def fem_state_snapshot(plant: MasterPendulum) -> dict[str, tuple[float, ...] | float]:
    snapshot = plant.fem.snapshot_state()
    return {
        name: tuple(float(value) for value in snapshot[name])
        for name in ("u", "v", "a", "u_old", "v_old", "a_old")
    } | {"tau": float(snapshot["tau"]), "t": float(snapshot["t"])}


def assert_same_pendulum_state(actual: PendulumState, expected: PendulumState) -> None:
    assert actual.theta == pytest.approx(expected.theta, abs=1e-10)
    assert actual.omega == pytest.approx(expected.omega, abs=1e-10)
    assert actual.tau == pytest.approx(expected.tau, abs=1e-12)
