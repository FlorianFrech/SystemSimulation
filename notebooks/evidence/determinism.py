"""Is a full-FEM run bit-identical when NGSolve's thread count is pinned?

`issues.md` REPRO-02: `FEMPendulum._do_step_internal` enters `TaskManager()` without
pinning a thread count, and repeated identical runs diverge. Bit-identical runs were
verified only under ``ngsolve.SetNumThreads(1)``. Whether a fixed count above one is
enough is open, because a parallel reduction whose partitioning or combine order
depends on scheduling stays non-deterministic at any fixed count.

``SetNumThreads`` is process-global and has to be set before the first
``TaskManager``, so every configuration runs in its own process. The notebook calls
:func:`run_configuration`; the worker side is :func:`main`, invoked as
``python -m evidence.determinism`` from ``notebooks/``.

Comparisons are bit for bit. Comparing contact counts would pass falsely: REPRO-02
found the first bounces agree even with threading unpinned, and only marginal events
differ. A difference in the last bit of ``theta`` is the earliest observable sign.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

__all__ = ["Comparison", "run_configuration", "compare", "main"]

DEFAULT_THREADS = 0  # sentinel: leave NGSolve at its own default


def _label(threads: int) -> str:
    return "default" if threads == DEFAULT_THREADS else f"{threads}"


def run_configuration(
    threads: int,
    n_runs: int,
    horizon_s: float,
    contact: bool,
    out_dir: Path,
    tag: str,
    python: str | None = None,
) -> list[Path]:
    """Run ``n_runs`` full-FEM simulations in one fresh process and return the npz paths.

    Args:
        threads: NGSolve thread count, or 0 to leave the default untouched.
        n_runs: Runs inside the one process. Within-process repetition is where
            REPRO-02 first observed divergence.
        horizon_s: Simulated horizon.
        contact: Wall contact on or off.
        out_dir: Where the arrays go.
        tag: Distinguishes two processes that share a thread count.
        python: Interpreter; defaults to the current kernel's, so the worker sees
            the same NGSolve build.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    prefix = out_dir / f"threads{_label(threads)}_{tag}"
    for stale in out_dir.glob(f"{prefix.name}_run*.npz"):
        stale.unlink()

    env = dict(os.environ)
    if threads == DEFAULT_THREADS:
        env.pop("NGS_NUM_THREADS", None)
    else:
        env["NGS_NUM_THREADS"] = str(threads)

    cmd = [
        python or sys.executable, "-m", "evidence.determinism",
        str(threads), str(n_runs), repr(horizon_s), str(int(contact)), str(prefix),
    ]
    started = time.perf_counter()
    completed = subprocess.run(
        cmd, cwd=str(Path(__file__).resolve().parent.parent), env=env,
        capture_output=True, text=True, check=False,
    )
    elapsed = time.perf_counter() - started
    for line in completed.stdout.splitlines():
        if line.startswith("RUN "):
            print(f"  {line[4:]}")
    if completed.returncode != 0:
        tail = "\n".join(completed.stderr.strip().splitlines()[-15:])
        raise RuntimeError(f"worker for threads={_label(threads)} failed:\n{tail}")
    print(f"  process threads={_label(threads)} tag={tag}: {elapsed:.1f} s")
    return [Path(f"{prefix}_run{k}.npz") for k in range(n_runs)]


@dataclass(frozen=True)
class Comparison:
    """Bitwise comparison of two runs."""

    identical: bool
    same_grid: bool
    max_abs_dtheta: float
    max_abs_domega: float
    first_difference_t: float | None


def compare(path_a: Path, path_b: Path) -> Comparison:
    """Compare two runs bit for bit.

    A different sample count means the event sequence differed, which inserts or
    removes localized steps; the common prefix is then compared instead.
    """
    a, b = np.load(path_a), np.load(path_b)
    ta, tb = a["t"], b["t"]
    same_grid = ta.shape == tb.shape and np.array_equal(ta, tb)
    n = min(ta.size, tb.size)

    dtheta = np.abs(a["theta"][:n] - b["theta"][:n])
    domega = np.abs(a["omega"][:n] - b["omega"][:n])
    differs = (dtheta != 0.0) | (domega != 0.0) | (ta[:n] != tb[:n])
    first = float(ta[np.argmax(differs)]) if differs.any() else None
    if not same_grid and first is None:
        first = float(ta[n - 1]) if n else 0.0  # identical prefix, then lengths diverge

    identical = (
        same_grid
        and np.array_equal(a["theta"], b["theta"])
        and np.array_equal(a["omega"], b["omega"])
    )
    return Comparison(
        identical=bool(identical),
        same_grid=bool(same_grid),
        max_abs_dtheta=float(dtheta.max()) if n else 0.0,
        max_abs_domega=float(domega.max()) if n else 0.0,
        first_difference_t=first,
    )


def main(argv: list[str]) -> None:
    """Worker: pin threads before anything imports the FEM, then run and save."""
    threads, n_runs = int(argv[0]), int(argv[1])
    horizon_s, contact, prefix = float(argv[2]), bool(int(argv[3])), argv[4]

    if threads != DEFAULT_THREADS:
        import ngsolve

        ngsolve.SetNumThreads(threads)

    from evidence import repo_root

    repo = repo_root(Path(__file__).resolve().parent)
    import evidence as ev
    from syssimx_examples.controlled_pendulum.components import FEMPendulum

    base = ev.CONTACT_SCENARIO if contact else ev.NO_CONTACT_SCENARIO
    scenario = base.replace(t_end=horizon_s)
    fmu_paths = ev.discover_fmus(repo, sys.platform)

    for k in range(n_runs):
        # The full-FEM case exactly as 04_performance builds it.
        plant = FEMPendulum(name=ev.PLANT_NAME, group="Plant")
        plant.set_parameters(**ev.make_fem_parameters(scenario))
        ev.declare_plant_feedthrough(plant)
        system, plant = ev.assemble_system(
            plant, scenario, fmu_paths, case_name="Full FEM", detection_probe=True
        )
        started = time.perf_counter()
        system.run(scenario.t0, scenario.t_end, scenario.macro_dt)
        wall = time.perf_counter() - started

        t, data = system.get_history()[plant.name]
        np.savez(
            f"{prefix}_run{k}.npz",
            t=np.asarray(t, dtype=float),
            theta=np.asarray(data["theta"], dtype=float),
            omega=np.asarray(data["omega"], dtype=float),
        )
        print(f"RUN threads={_label(threads)} run={k} wall={wall:.1f}s samples={len(t)}",
              flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
