"""The switching pendulum plant and its region key.

`SwitchingPendulum` replaces the near-identical wrappers that notebooks 6, 7 and
9 each declared separately. The only thing that varied between them was whether
the FEM model carries the wall, which is now a `Scenario` field.
"""

from __future__ import annotations

import numpy as np

from syssimx.core.multi_comp import MultiComponent
from syssimx_examples.controlled_pendulum.components import FEMPendulum, FMUPendulum
import syssimx_examples.controlled_pendulum.components.fem.pendulum_config as config

from .scenario import Scenario

__all__ = [
    "PLANT_NAME",
    "scalar_value",
    "absolute_theta",
    "make_fem_parameters",
    "TimeGatedRegionKey",
    "region_key_for",
    "SwitchingPendulum",
    "FemToFemPendulum",
]

PLANT_NAME = "Pendulum"


def scalar_value(value) -> float:
    """Unwrap a port reading, which may be a dict or a Pint quantity."""
    if isinstance(value, dict):
        value = value.get("value", np.nan)
    if hasattr(value, "magnitude"):
        value = value.magnitude
    return float(value)


def absolute_theta(comp) -> float:
    """Absolute deflection in radians, read off the wrapper.

    Evaluated against the `MultiComponent` rather than a sub-model, so it reads
    the unified `theta` output regardless of which model is currently active.
    """
    value = comp.outputs["theta"].get()
    if value is None:
        return 0.0
    return abs(float(getattr(value, "magnitude", value)))


def make_fem_parameters(scenario: Scenario) -> dict:
    """FEM configuration for one scenario."""
    init_params = config.InitialConditionParameters()
    init_params.angular_position_deg = 0.0

    sim_params = config.SimulationParameters()
    sim_params.tau = scenario.fem_internal_dt
    sim_params.t_end = scenario.t_end
    sim_params.with_contact = scenario.contact
    sim_params.use_gravity = True

    anim_params = config.AnimationParameters()
    anim_params.animate = False

    return {
        "init_params": init_params,
        "sim_params": sim_params,
        "anim_params": anim_params,
    }


class TimeGatedRegionKey:
    """Angle region key with a decaying offset that suppresses the launch window.

    The gate reads the *active sub-model's* clock. `HybridAlgorithm` calls
    `_do_step_internal` directly for trial steps and for every bisection
    iteration, and only `do_step` advances a component's `t`, so the wrapper's
    own `self.t` stays pinned at the left edge of the macro step. A gate reading
    `comp.t` would return the same value at both ends of the bracket, no sign
    change would be detected, and the gate would never fire.

    The offset ramps rather than steps because a discontinuous key can cross two
    boundaries at one instant, which `_resolve_region_target` rejects.
    """

    def __init__(self, offset: float, t_open: float, mode: str = "ramp"):
        self.offset = float(offset)
        self.t_open = float(t_open)
        self.mode = mode

    def value(self, t: float, abs_theta: float) -> float:
        """Gated key from a time and an absolute angle, both in SI units.

        Exposed separately so a boundary-localization table can reconstruct the
        key at a located event without re-running the system.
        """
        if self.mode == "step":
            return self.offset if t < self.t_open else abs_theta
        return abs_theta + self.offset * max(0.0, 1.0 - t / self.t_open)

    def __call__(self, comp) -> float:
        return self.value(float(comp.active_comp.t), absolute_theta(comp))


def region_key_for(scenario: Scenario):
    """The region key this scenario declares: gated, or the bare angle."""
    if scenario.gated:
        return TimeGatedRegionKey(
            offset=scenario.gate_offset_rad, t_open=scenario.gate_t_open_s
        )
    return absolute_theta


class SwitchingPendulum(MultiComponent):
    """FEM/FMU pendulum pair behind one interface, switched by a region map.

    FEM is initialized first because its mesh determines the mass, inertia and
    equivalent length the FMU has to be parameterised with; without that the two
    modes describe different pendulums. `_adapt_state` renames the running state
    to the FMU's initial-condition parameters, which is the functional half of
    the handover.
    """

    def __init__(
        self,
        scenario: Scenario,
        name: str = PLANT_NAME,
        initial_mode: str = "FEM",
    ):
        self.scenario = scenario
        self.fem = FEMPendulum(name="FEM_Pendulum")
        self.fmu = FMUPendulum(name="FMU_Pendulum", solver=scenario.fmu_solver)

        super().__init__(
            name=name,
            models={"FEM": self.fem, "FMU": self.fmu},
            initial_mode=initial_mode,
            group="Plant",
        )

        self._unify_ports()
        self._initialize_ports_from_specs()
        self.parameters.update(
            {"FEM": self.fem.get_parameters(), "FMU": self.fmu.get_parameters()}
        )

    def _initialize_component(self, t0):
        self.fem.set_parameters(**self.parameters.get("FEM", {}))
        self.fem.initialize(t0)
        self._sync_fmu_from_fem()
        self.fmu.initialize(t0)
        self.direct_feedthrough = self.active_comp.direct_feedthrough

    def _sync_fmu_from_fem(self):
        self.fmu.set_parameters(
            theta_start=np.deg2rad(self.fem.init_params.angular_position_deg),
            omega_start=self.fem.init_params.angular_velocity,
            m=self.fem.mass,
            L=self.fem._equivalent_length,
            J=self.fem.inertia,
            g=9.81 if self.fem._use_gravity else 0.0,
        )

    def _adapt_state(self, state, target_mode):
        if target_mode == "FMU":
            return {
                "theta_start": state["theta"],
                "omega_start": state["omega"],
                "tau": state["tau"],
            }
        return state

    def declare_regions(self) -> "SwitchingPendulum":
        """Install the scenario's region map. Call before `System.initialize`."""
        self.set_switch_regions(
            key=region_key_for(self.scenario),
            breakpoints=(self.scenario.switch_threshold_rad,),
            modes=self.scenario.region_modes,
            band=self.scenario.switch_band_rad,
        )
        return self


class FemToFemPendulum(MultiComponent):
    """Two FEM pendulums behind one region map: a switch that changes no model.

    The control for the performance comparison. Both modes hold an independently
    constructed `FEMPendulum` with identical parameters, so the region map fires
    and the state traverses the full transfer path while the physics on either
    side is the same. Any trajectory deviation it shows is the cost of the
    handover itself, not of model mismatch.
    """

    def __init__(self, scenario: Scenario, name: str = PLANT_NAME, initial_mode: str = "FEM_A"):
        self.scenario = scenario
        self.fem_a = FEMPendulum(name="FEM_Pendulum_A")
        self.fem_b = FEMPendulum(name="FEM_Pendulum_B")

        super().__init__(
            name=name,
            models={"FEM_A": self.fem_a, "FEM_B": self.fem_b},
            initial_mode=initial_mode,
            group="Plant",
        )

        self._unify_ports()
        self._initialize_ports_from_specs()
        self.parameters.update(
            {"FEM_A": self.fem_a.get_parameters(), "FEM_B": self.fem_b.get_parameters()}
        )

    def _initialize_component(self, t0):
        for model in (self.fem_a, self.fem_b):
            model.set_parameters(**self.parameters.get(model_key(model, self), {}))
            model.initialize(t0)
        self.direct_feedthrough = self.active_comp.direct_feedthrough

    def _adapt_state(self, state, target_mode):
        return dict(state)

    def declare_regions(self) -> "FemToFemPendulum":
        self.set_switch_regions(
            key=region_key_for(self.scenario),
            breakpoints=(self.scenario.switch_threshold_rad,),
            modes=("FEM_A", "FEM_B"),
            band=self.scenario.switch_band_rad,
        )
        return self


def model_key(model, wrapper) -> str:
    """Mode key under which `wrapper` registered `model`."""
    for key, candidate in wrapper.models.items():
        if candidate is model:
            return key
    raise KeyError(f"{model.name} is not a sub-model of {wrapper.name}")
