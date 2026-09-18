"""Shared post-processing: mode timelines, error metrics, and the measured run."""

from __future__ import annotations

import gc
from time import perf_counter_ns

import numpy as np

from syssimx.core.multi_comp import MultiComponent

from .instrument import PHASES, PhaseTracker, instrument_algorithm, instrument_step
from .scenario import Scenario

__all__ = [
    "mode_intervals",
    "mode_active_time",
    "contact_event_times",
    "fem_contact_closures",
    "check_contact_dispatch",
    "trajectory_error_metrics",
    "distance_to_grid",
    "run_measured_case",
]


def mode_intervals(switch_events, initial_mode, t0, t_end):
    """`(t_left, t_right, mode)` intervals covering the whole horizon."""
    rows, mode, left = [], initial_mode, t0
    for event in switch_events:
        right = float(event.time)
        rows.append((left, right, mode))
        mode, left = event.to_mode, right
    rows.append((left, t_end, mode))
    return rows


def mode_active_time(intervals, mode_name) -> float:
    """Simulated time during which `mode_name` was the active model."""
    return sum(max(0.0, right - left) for left, right, mode in intervals if mode == mode_name)


def contact_event_times(system, plant) -> list[float]:
    """Located `wall_hit` instants from the system event history."""
    events = system.get_history().get("Events", {})
    return [float(record.t) for record in events.get((plant.name, "wall_hit"), [])]


def fem_contact_closures(plant) -> int | None:
    """Gap closures the FEM resolved inside accepted advances.

    Read from the contact-enabled FEM model behind `plant`, whether `plant` is
    that model or a `MultiComponent` wrapping it. `None` when no such model
    exists, which is the no-contact regime.
    """
    models = getattr(plant, "models", None) or {"plant": plant}
    for model in models.values():
        if getattr(model, "_with_contact", False) and hasattr(model, "contact_closures"):
            return int(model.contact_closures)
    return None


def check_contact_dispatch(plant, contact_times, label: str = "") -> None:
    """Raise unless every physical closure was dispatched as `wall_hit`.

    The coordinator's own missed-event guard compares indicator signs at the
    macro endpoints and cannot see a contact episode shorter than a macro step.
    This check compares what the FEM did on the committed trajectory with what
    the event history records; a mismatch means the instrument lost or
    duplicated an impact (issues.md HYB-10) and the run is not evidence.
    """
    closures = fem_contact_closures(plant)
    if closures is None:
        return
    dispatched = len(contact_times)
    if closures != dispatched:
        raise AssertionError(
            f"{label + ': ' if label else ''}the FEM closed its contact gap "
            f"{closures} times inside accepted advances but {dispatched} wall_hit "
            f"events were dispatched (HYB-10)"
        )


def distance_to_grid(t_value: float, step: float) -> float:
    """Distance from `t_value` to the nearest communication point."""
    remainder = t_value % step
    return min(remainder, step - remainder)


def trajectory_error_metrics(t, y, t_ref, y_ref, *, t_min=None, t_max=None) -> dict:
    """Sampled trajectory errors against an interpolated reference."""
    t = np.asarray(t, dtype=float)
    y = np.asarray(y, dtype=float)
    t_ref = np.asarray(t_ref, dtype=float)
    y_ref = np.asarray(y_ref, dtype=float)

    mask = np.ones_like(t, dtype=bool)
    if t_min is not None:
        mask &= t >= t_min
    if t_max is not None:
        mask &= t <= t_max

    t_eval, y_eval = t[mask], y[mask]
    err = y_eval - np.interp(t_eval, t_ref, y_ref)
    duration = t_eval[-1] - t_eval[0]

    return {
        "e_inf": float(np.max(np.abs(err))),
        "e_2": float(np.sqrt(np.trapezoid(err**2, t_eval) / duration)),
        "e_mean": float(np.mean(np.abs(err))),
        "n_samples": int(len(t_eval)),
    }


def _collect_outputs(system, plant, case_name, initial_mode, intervals) -> dict:
    history = system.get_history()
    t, data = history[plant.name]
    return {
        # Kept so a failing self-check can say which boundaries fired, rather
        # than only that the mechanism did not run.
        "event_history": history.get("Events", {}),
        "case": case_name,
        "t": np.asarray(t, dtype=float),
        "theta": np.asarray(data["theta"], dtype=float),
        "omega": np.asarray(data["omega"], dtype=float),
        "alpha": np.asarray(data["alpha"], dtype=float),
        "switch_events": list(getattr(plant, "switch_events", [])),
        "contact_times": contact_event_times(system, plant),
        "contact_closures": fem_contact_closures(plant),
        "initial_mode": initial_mode,
        "mode_intervals": intervals,
    }


def run_measured_case(
    build_case,
    case_name: str,
    repeat: int,
    scenario: Scenario,
    *,
    warmup: bool = False,
    keep_result: bool = False,
    progress=None,
):
    """Build, instrument, and time one case.

    Args:
        build_case: Zero-argument factory returning `(system, plant, models)`,
            where `models` maps a label to each component whose solver time is
            to be attributed.
        progress: Optional `tqdm`-like factory, called as `progress(total, desc)`
            and used as a context manager yielding an object with `.update()`.

    Returns:
        `(row, result)`. `result` is `None` unless `keep_result`.
    """
    gc.collect()

    setup_start = perf_counter_ns()
    system, plant, models = build_case()
    setup_s = (perf_counter_ns() - setup_start) * 1e-9

    tracker = PhaseTracker()
    # Replaced by an instrumented subclass rather than patched in place, so the
    # result has to be rebound. Safe after initialize(): the algorithm carries
    # no state across it and the auto-selection guard has already run.
    system.algorithm = instrument_algorithm(system.algorithm, tracker)
    model_timers = {name: instrument_step(comp, name, tracker) for name, comp in models.items()}
    wrapper_timer = (
        instrument_step(plant, "wrapper", tracker) if isinstance(plant, MultiComponent) else None
    )

    # The region map, not the constructor argument, decides which model starts.
    # `_reconcile_initial_region()` derives it from the switching signal at t0,
    # so it has to be read back rather than assumed; assuming mislabels every
    # mode interval below.
    initial_mode = plant.active_mode if isinstance(plant, MultiComponent) else "FEM"

    t0, t_end = scenario.t0, scenario.t_end
    label = f"{'warmup' if warmup else 'repeat'} {repeat + 1} - {case_name}"

    run_start = perf_counter_ns()
    if progress is None:
        system.run(t0, t_end, scenario.macro_dt)
    else:
        with progress(scenario.sim_time, label) as bar:
            seen = t0

            def advance(t_now, _t_final):
                nonlocal seen
                now = min(max(t_now, t0), t_end)
                bar.update(now - seen)
                seen = now

            system.run(t0, t_end, scenario.macro_dt, progress=advance)
    run_s = (perf_counter_ns() - run_start) * 1e-9

    switch_events = list(getattr(plant, "switch_events", []))
    intervals = (
        mode_intervals(switch_events, initial_mode, t0, t_end)
        if isinstance(plant, MultiComponent)
        else [(t0, t_end, initial_mode)]
    )

    solve_s = sum(timer.wall_s for timer in model_timers.values())
    plant_s = wrapper_timer.wall_s if wrapper_timer is not None else solve_s

    row = {
        "case": case_name,
        "repeat": repeat,
        "warmup": warmup,
        "algorithm": type(system.algorithm).__name__,
        "initial_mode": initial_mode,
        "setup_s": setup_s,
        "run_s": run_s,
        "solve_s": solve_s,
        "delegation_s": plant_s - solve_s,
        "overhead_s": run_s - solve_s,
        "fem_active_sim_s": mode_active_time(intervals, "FEM"),
        "n_switches": len(switch_events),
        "n_contacts": len(contact_event_times(system, plant)),
        # Physical closures on the committed trajectory; the notebooks assert
        # this equals n_contacts (HYB-10). None without a contact FEM.
        "n_closures": fem_contact_closures(plant),
    }
    # Seeded so both cases carry the same columns even though the baseline has
    # no FMU model at all.
    for name in ("FEM", "FMU"):
        row[f"{name.lower()}_solve_s"] = 0.0
        row[f"{name.lower()}_calls"] = 0
    for phase in PHASES:
        row[f"solve_{phase}_s"] = sum(timer.phase_s(phase) for timer in model_timers.values())
        row[f"calls_{phase}"] = sum(timer.n_calls[phase] for timer in model_timers.values())
    for name, timer in model_timers.items():
        row[f"{name.lower()}_solve_s"] = timer.wall_s
        row[f"{name.lower()}_calls"] = timer.calls

    result = (
        _collect_outputs(system, plant, case_name, initial_mode, intervals)
        if keep_result
        else None
    )
    return row, result
