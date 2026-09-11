"""One declared scenario: every parameter an evidence notebook is allowed to vary.

A notebook builds exactly one :class:`Scenario` in its configuration cell and
passes it down. Nothing below reads a module-level constant, so the parameters
a run used are the object it carries, and :meth:`Scenario.provenance` is what
``record()`` writes next to the numbers.

Angles are radians throughout. Notebook 7 previously expressed its region policy
in degrees while notebook 6 used radians, which made the two event tolerances
look different when they were derived by the same rule.
"""

from __future__ import annotations

import platform
import sys
from dataclasses import dataclass, field, asdict

import numpy as np

__all__ = ["Scenario", "CONTACT_SCENARIO", "NO_CONTACT_SCENARIO"]


@dataclass(frozen=True)
class Scenario:
    """Parameters of one measured configuration.

    Attributes:
        name: Short identifier, used in figure and results filenames.
        contact: Whether the wall is present. Drives the FEM contact model, the
            ``wall_hit`` indicator, and the baseline's detection probe.
        t0, t_end, macro_dt: Communication grid.
        fem_internal_dt: FEM sub-step, held fixed across a sweep so that
            refining the macro grid separates placement error from model
            discretization error.
        switch_threshold_rad, switch_band_rad: Region boundary and its
            hysteresis band on ``abs(theta)``.
        region_modes: Ordered models, lowest region first.
        gate_t_open_s, gate_offset_rad: Launch gate. ``gate_t_open_s = 0``
            disables it. The gate exists because theta starts at 0, inside the
            FEM region, so an ungated map runs the deformable model through a
            launch window where the pendulum is accelerating away from the wall.
        event_tol_time: Bisection stopping rule.
        theta_amplitude_deg, setpoint_freq_hz: Shape of the SetPoint FMU wired
            into the loop. ``event_tol_value`` is derived from these, so they
            must match that export.
    """

    name: str
    contact: bool

    t0: float = 0.0
    t_end: float = 0.4
    macro_dt: float = 1e-3
    fem_internal_dt: float = 1e-3

    switch_threshold_rad: float = 0.075
    switch_band_rad: float = 0.005
    region_modes: tuple[str, ...] = ("FEM", "FMU")

    gate_t_open_s: float = 0.0
    gate_offset_rad: float = 0.35

    event_tol_time: float = 1e-5

    theta_amplitude_deg: float = 20.0
    setpoint_freq_hz: float = 3.0

    fmu_solver: str = "cvode"
    contact_stiffness: float = 2e9

    n_warmup: int = 1
    n_repeats: int = 5

    @property
    def gated(self) -> bool:
        return self.gate_t_open_s > 0.0

    @property
    def sim_time(self) -> float:
        return self.t_end - self.t0

    @property
    def max_theta_rate_rad_s(self) -> float:
        """Largest angular rate the setpoint can demand."""
        return float(
            np.deg2rad(2.0 * np.pi * self.setpoint_freq_hz * self.theta_amplitude_deg)
        )

    @property
    def event_tol_value(self) -> float:
        """Bisection early-exit tolerance, derived rather than chosen.

        ``tol_value`` is not an acceptance gate: ``_locate_event_time`` accepts
        events from the final sign-change bracket. What it still controls is the
        early exit inside the bisection loop. Bisecting to ``tol_time`` leaves a
        residual of about ``rate * tol_time``, so a larger value would accept the
        midpoint before the interval is narrow enough. Derived with no margin.

        The product bounds the residual at the *fastest* crossing only, so a
        slower crossing can still exit early at a coarser time than ``tol_time``
        promises. Setting it to zero removes the early exit and leaves
        ``tol_time`` as the sole stopping rule, at a few more iterations.
        """
        return self.max_theta_rate_rad_s * self.event_tol_time

    @property
    def armed_lower_edge(self) -> float:
        return self.switch_threshold_rad - self.switch_band_rad

    @property
    def armed_upper_edge(self) -> float:
        return self.switch_threshold_rad + self.switch_band_rad

    def replace(self, **changes) -> "Scenario":
        """A copy with `changes` applied; the frozen-dataclass idiom."""
        from dataclasses import replace as _replace

        return _replace(self, **changes)

    def provenance(self) -> dict:
        """Flat, JSON-safe record of everything that shapes a measurement."""
        payload = {k: v for k, v in asdict(self).items()}
        payload["region_modes"] = list(self.region_modes)
        payload["event_tol_value"] = self.event_tol_value
        payload["max_theta_rate_rad_s"] = self.max_theta_rate_rad_s
        payload["python"] = sys.version.split()[0]
        payload["platform"] = platform.platform()
        payload["processor"] = platform.processor()
        return payload


# The wall is at theta = 0 and the FEM holds the inner region containing it.
# tol_time sits above the FEM's own 1e-4 s contact sub-step on purpose:
# `FEMPendulum` reports its bracketing interval through `report_internal_event`,
# and `_locate_event_time` accepts such a hint directly when it is already
# narrower than tol_time, skipping bisection. A tighter value makes the
# algorithm re-derive a time the FEM already knew, at about four extra FEM
# solves per event. The cost is placement, which this scenario does not measure.
CONTACT_SCENARIO = Scenario(
    name="contact",
    contact=True,
    switch_threshold_rad=0.075,
    switch_band_rad=0.005,
    gate_t_open_s=0.03,
    gate_offset_rad=0.35,
    event_tol_time=1.5e-4,
)

# No wall, no launch gate, and a wider band. Without contact there is no
# self-reported bracket to accept, so tol_time is the sole stopping rule and is
# set an order finer.
NO_CONTACT_SCENARIO = Scenario(
    name="nocontact",
    contact=False,
    switch_threshold_rad=float(np.deg2rad(5.0)),
    switch_band_rad=float(np.deg2rad(1.0)),
    gate_t_open_s=0.0,
    event_tol_time=1e-5,
)
