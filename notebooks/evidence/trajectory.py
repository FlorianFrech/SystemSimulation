"""Controlled single-thread trajectory comparison, separate from timing evidence.

Each physical run uses a fresh process. Only a campaign whose two repetitions
of each execution strategy are bit-identical may emit T2_nocontact_traj.json.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from contextlib import nullcontext
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

import numpy as np

from .scenario import NO_CONTACT_SCENARIO, Scenario

NOTEBOOK = "07_trajectory_comparison"
RESULT_ID = "T2_nocontact_traj"
CASE_NAMES = ("Full FEM", "Switched FEM/FMU")
BACKEND_PINS = {"ngsolve": "6.2.2607", "fmpy": "0.3.20"}


def make_scenario(smoke: bool = False) -> Scenario:
    """Preserve 04_performance's policy; change only threads and repetition protocol."""
    return NO_CONTACT_SCENARIO.replace(
        t_end=0.05 if smoke else 1.0,
        switch_threshold_rad=0.085,
        switch_band_rad=0.015,
        ngsolve_threads=1,
        n_warmup=0,
        n_repeats=2,
    )


def _validate_trace(trace: dict, scenario: Scenario) -> None:
    t = trace["t"]
    if t.ndim != 1 or t.size < 2 or np.any(np.diff(t) < 0):
        raise ValueError("Plant time grid must be nondecreasing with at least two samples.")
    if not np.isclose(t[0], scenario.t0, rtol=0, atol=1e-12) or not np.isclose(
        t[-1], scenario.t_end, rtol=0, atol=1e-12
    ):
        raise ValueError("Recorded plant trajectory does not cover the declared horizon.")
    for name, values in trace.items():
        if values.dtype.kind in "fci" and not np.isfinite(values).all():
            raise ValueError(f"Non-finite values in {name}.")
    for name in ("theta", "omega"):
        if trace[name].shape != t.shape:
            raise ValueError(f"{name} does not match the plant time grid.")
    switches = trace["switch_times"]
    if switches.shape != trace["switch_from"].shape or switches.shape != trace["switch_to"].shape:
        raise ValueError("Switch identities do not match their timestamps.")
    if np.any(np.diff(switches) < 0) or np.any((switches < t[0]) | (switches > t[-1])):
        raise ValueError("Switch timestamps must be ordered inside the declared horizon.")
    if trace["contact_times"].size:
        raise ValueError("A contact-free trajectory contains contact events.")


def _repeatability(traces: list[dict]) -> dict:
    first, second = traces
    if first.keys() != second.keys():
        raise ValueError("Repetition archives have different fields.")
    different = [
        key
        for key in first
        if first[key].dtype != second[key].dtype
        or first[key].shape != second[key].shape
        or first[key].tobytes() != second[key].tobytes()
    ]
    if different:
        raise ValueError("Repetitions are not bit-identical: " + ", ".join(different))
    return {"bit_identical": True, "checked_fields": sorted(first)}


def trajectory_metrics(baseline: dict, switched: dict) -> dict:
    """Linear interpolation on the union grid; repeated timestamps use the last sample."""
    tb, ts = baseline["t"], switched["t"]
    if tb[0] != ts[0] or tb[-1] != ts[-1]:
        raise ValueError("Both trajectories must have the same endpoints; no extrapolation.")
    keep_b = np.r_[tb[1:] != tb[:-1], True]
    keep_s = np.r_[ts[1:] != ts[:-1], True]
    grid = np.union1d(tb, ts)
    delta = np.interp(grid, ts[keep_s], switched["theta"][keep_s]) - np.interp(
        grid, tb[keep_b], baseline["theta"][keep_b]
    )
    delta_omega = np.interp(grid, ts[keep_s], switched["omega"][keep_s]) - np.interp(
        grid, tb[keep_b], baseline["omega"][keep_b]
    )
    return {
        "max_abs_delta_rad": float(np.abs(delta).max()),
        "e_2_rad": float(np.sqrt(np.trapezoid(delta**2, grid) / (grid[-1] - grid[0]))),
        "max_abs_delta_omega_rad_s": float(np.abs(delta_omega).max()),
        "t_max_abs_delta_s": float(grid[np.argmax(np.abs(delta))]),
        "n_samples": int(grid.size),
    }


def summarize_traces(
    baseline: list[dict], switched: list[dict], scenario: Scenario, *, smoke: bool = False
) -> dict:
    """Fail closed on nonrepeatability, missing horizon, or an unexercised full campaign."""
    if len(baseline) != 2 or len(switched) != 2:
        raise ValueError("Exactly two fresh-process runs per case are required.")
    repeatability = {}
    for name, traces in zip(CASE_NAMES, (baseline, switched), strict=True):
        for trace in traces:
            _validate_trace(trace, scenario)
        repeatability[name] = _repeatability(traces)
    if any(trace["switch_times"].size for trace in baseline):
        raise ValueError("Full-FEM reference unexpectedly switched.")
    if not smoke and any(not trace["switch_times"].size for trace in switched):
        raise ValueError("The switched strategy performed no switch.")
    pairs = [trajectory_metrics(b, s) for b, s in zip(baseline, switched, strict=True)]
    return {
        "scenario": scenario.provenance(),
        "runs_per_case": 2,
        "fresh_process_per_run": True,
        "repeatability": repeatability,
        "per_pair": pairs,
        "max_abs_delta_rad": max(p["max_abs_delta_rad"] for p in pairs),
        "e_2_rad": max(p["e_2_rad"] for p in pairs),
        "max_abs_delta_omega_rad_s": max(p["max_abs_delta_omega_rad_s"] for p in pairs),
        "n_switches_per_run": [int(t["switch_times"].size) for t in switched],
        "comparison_grid": "union of both recorded grids, last sample at duplicate times",
        "interpolation": "linear, no extrapolation",
        "interpretation": "reproducible strategy comparison; not isolated switching error or physical validation",
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fmu_input_hashes(models: list, repo: Path, *, expected_count: int) -> dict:
    """Hash the archives actually referenced by FMUComponent._path."""
    paths = {
        Path(model._path).resolve()
        for model in models
        if hasattr(model, "_path") and Path(model._path).suffix.lower() == ".fmu"
    }
    if len(paths) != expected_count:
        raise ValueError(f"Expected {expected_count} FMU inputs, found {len(paths)}.")
    return {path.relative_to(repo).as_posix(): _sha256(path) for path in sorted(paths)}


def _pin_threads() -> None:
    import ngsolve

    ngsolve.SetNumThreads(1)
    os.environ["NGS_NUM_THREADS"] = "1"


def _preflight(smoke: bool) -> dict:
    from record import provenance

    block = provenance(notebook=NOTEBOOK, smoke=smoke)
    if smoke:
        return block
    if os.environ.get("SYSSIMX_ALLOW_DIRTY_RESULTS") == "1":
        raise RuntimeError("Disable SYSSIMX_ALLOW_DIRTY_RESULTS for this campaign.")
    if block["dirty_measurement_paths"] != []:
        raise RuntimeError("Commit and push the measured code before running this campaign.")
    repo = Path(__file__).resolve().parents[2]
    if block["syssimx_path"] is None or Path(block["syssimx_path"]).resolve() != repo:
        raise RuntimeError("Use this SysSimX source checkout, not a different installation.")
    for package, expected in BACKEND_PINS.items():
        if version(package) != expected:
            raise RuntimeError(f"Use {package} {expected}, matching the paper timing environment.")
    for older, newer in (("v0.4.3", "HEAD"), ("HEAD", "origin/main")):
        check = subprocess.run(
            ["git", "merge-base", "--is-ancestor", older, newer],
            cwd=repo,
            capture_output=True,
            text=True,
            check=False,
        )
        if check.returncode:
            raise RuntimeError(
                "The producer must descend from v0.4.3 and be pushed to origin/main."
            )
    return block


def _verify_workers(metadata: list[dict], scenario: Scenario, source: dict, smoke: bool) -> dict:
    """Do not pool workers from different code, configurations, or FMU exports."""
    manifests = {}
    all_hashes = {}
    for meta in metadata:
        if meta["scenario"] != scenario.provenance():
            raise ValueError("Worker scenario differs from the declared campaign.")
        block = meta["provenance"]
        for field in ("syssimx_revision", "syssimx_version", "python", "platform"):
            if block[field] != source[field]:
                raise ValueError(f"Worker provenance differs in {field}.")
        if not smoke and block["dirty_measurement_paths"] != []:
            raise ValueError("Worker source changed during the campaign.")
        if not block["ngsolve_threads_pinned"] or block["ngsolve_num_threads_env"] != "1":
            raise ValueError("Worker did not pin one NGSolve thread.")
        name, hashes = meta["case"], meta["fmu_sha256"]
        if not hashes:
            raise ValueError("Worker FMU input manifest is empty.")
        if name in manifests and manifests[name] != hashes:
            raise ValueError("FMU inputs changed between repetitions.")
        manifests[name] = hashes
        for path, digest in hashes.items():
            if path in all_hashes and all_hashes[path] != digest:
                raise ValueError("Shared FMU inputs differ between cases.")
            all_hashes[path] = digest
    if len({json.dumps(m["backend_versions"], sort_keys=True) for m in metadata}) != 1:
        raise ValueError("Workers used different backend versions.")
    return manifests


def _worker(case: str, target: Path, smoke: bool) -> None:
    from record import provenance

    import evidence as ev
    from syssimx_examples.controlled_pendulum.components import FEMPendulum

    before = _preflight(smoke)
    scenario = make_scenario(smoke)
    repo = ev.repo_root(Path(__file__).resolve().parent)
    if case == "full_fem":
        plant = FEMPendulum(name=ev.PLANT_NAME, group="Plant")
        plant.set_parameters(**ev.make_fem_parameters(scenario))
    else:
        plant = ev.SwitchingPendulum(scenario, name=ev.PLANT_NAME).declare_regions()
        plant.set_parameters(**{"FEM": ev.make_fem_parameters(scenario)})
    ev.declare_plant_feedthrough(plant)
    name = CASE_NAMES[case == "switched"]
    system, plant = ev.assemble_system(
        plant,
        scenario,
        ev.discover_fmus(repo, sys.platform),
        case_name=name,
        detection_probe=case == "full_fem",
    )
    outputs = plant.get_outputs()
    initial = {key: ev.scalar_value(outputs[key]) for key in ("theta", "omega")}
    initial_mode = getattr(plant, "active_mode", "FEM")
    models = [*system.components.values(), *getattr(plant, "models", {}).values()]
    hashes = _fmu_input_hashes(models, repo, expected_count=5 + int(case == "switched"))
    last_progress = scenario.t0

    def progress(t_now, _t_final):
        nonlocal last_progress
        if t_now - last_progress >= max(0.01, scenario.sim_time / 10):
            print(f"{name}: {t_now:.3f} / {scenario.t_end:.3f} s", flush=True)
            last_progress = t_now

    system.run(scenario.t0, scenario.t_end, scenario.macro_dt, progress=progress)
    history = system.get_history()
    t, data = history[plant.name]
    arrays = {"t": np.asarray(t, dtype=float)}
    for key in ("theta", "omega"):
        arrays[key] = np.asarray(data[key], dtype=float)
    if arrays["t"][0] > scenario.t0:
        arrays["t"] = np.r_[scenario.t0, arrays["t"]]
        for key in ("theta", "omega"):
            arrays[key] = np.r_[initial[key], arrays[key]]
    switches = list(getattr(plant, "switch_events", []))
    arrays.update(
        {
            "switch_times": np.asarray([e.time for e in switches], dtype=float),
            "switch_from": np.asarray([e.from_mode for e in switches], dtype="U16"),
            "switch_to": np.asarray([e.to_mode for e in switches], dtype="U16"),
            "contact_times": np.asarray(ev.contact_event_times(system, plant), dtype=float),
            "event_history_json": np.array(
                json.dumps(
                    [
                        [component, indicator, [float(e.t) for e in events]]
                        for (component, indicator), events in sorted(
                            history.get("Events", {}).items()
                        )
                    ]
                )
            ),
        }
    )
    for component, port, prefix in (
        ("Angle Sensor", "v_out", "sensor"),
        ("Angle Decoder", "theta", "decoder"),
        ("PID", "u", "controller"),
        ("Drive", "torque", "drive"),
    ):
        times, values = history[component]
        arrays[prefix + "_t"] = np.asarray(times, dtype=float)
        arrays[prefix + "_" + port] = np.asarray(values[port], dtype=float)
    _validate_trace(arrays, scenario)
    after = _preflight(smoke)
    if after["syssimx_revision"] != before["syssimx_revision"]:
        raise RuntimeError("Source revision changed while the worker ran.")
    if any(_sha256(repo / path) != digest for path, digest in hashes.items()):
        raise RuntimeError("An FMU input changed while the worker ran.")
    np.savez_compressed(target, **arrays)
    metadata = {
        "case": name,
        "process_id": os.getpid(),
        "initial_mode": initial_mode,
        "scenario": scenario.provenance(),
        "provenance": provenance(notebook=NOTEBOOK, smoke=smoke),
        "backend_versions": {p: version(p) for p in ("ngsolve", "fmpy", "numpy")},
        "fmu_sha256": hashes,
        "raw_sha256": _sha256(target),
        "missed_events": len(system.algorithm.missed_events),
    }
    target.with_suffix(".json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {name}: {arrays['t'].size} samples, {len(switches)} switches", flush=True)


def _stream_process(command: list[str], log_path: Path | None = None) -> None:
    env = {**os.environ, "NGS_NUM_THREADS": "1", "PYTHONUNBUFFERED": "1"}
    with log_path.open("w", encoding="utf-8") if log_path else nullcontext() as log:
        with subprocess.Popen(
            command,
            cwd=Path(__file__).resolve().parent.parent,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        ) as proc:
            for line in proc.stdout:
                if log is not None:
                    log.write(line)
                if not line.startswith("LOG_SOLVER"):
                    print(line, end="", flush=True)
            if proc.wait():
                raise RuntimeError("Trajectory subprocess failed; no campaign result was admitted.")


def _campaign(raw_dir: Path | None, results: Path, smoke: bool) -> Path:
    from record import record

    source = _preflight(smoke)
    scenario = make_scenario(smoke)
    if raw_dir is None:
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        raw_dir = Path(__file__).resolve().parents[1] / "figures" / f"{RESULT_ID}_{stamp}"
    raw_dir = raw_dir.resolve()
    raw_dir.mkdir(parents=True, exist_ok=False)
    traces, metadata, artifacts = {}, [], []
    for case, name in zip(("full_fem", "switched"), CASE_NAMES, strict=True):
        traces[name] = []
        for repeat in range(scenario.n_repeats):
            path = raw_dir / f"{case}_run{repeat}.npz"
            print(f"Starting {name}, fresh-process run {repeat + 1}/2", flush=True)
            command = [
                sys.executable,
                "-m",
                "evidence.trajectory",
                "--worker",
                case,
                "--run-path",
                str(path),
            ]
            log_path = path.with_suffix(".log")
            _stream_process(command + (["--smoke"] if smoke else []), log_path=log_path)
            meta = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
            if _sha256(path) != meta["raw_sha256"]:
                raise ValueError("Raw trajectory checksum does not match its worker metadata.")
            with np.load(path, allow_pickle=False) as stored:
                traces[name].append({key: stored[key] for key in stored.files})
            metadata.append(meta)
            artifacts.append(
                {
                    "case": name,
                    "repeat": repeat,
                    "npz": path.name,
                    "sha256": meta["raw_sha256"],
                    "metadata": path.with_suffix(".json").name,
                    "metadata_sha256": _sha256(path.with_suffix(".json")),
                    "log": log_path.name,
                    "log_sha256": _sha256(log_path),
                }
            )
    manifests = _verify_workers(metadata, scenario, source, smoke)
    values = summarize_traces(traces[CASE_NAMES[0]], traces[CASE_NAMES[1]], scenario, smoke=smoke)
    values.update(
        {
            "fmu_sha256": manifests,
            "backend_versions": metadata[0]["backend_versions"],
            "worker_provenance": [m["provenance"] for m in metadata],
            "worker_process_ids": [m["process_id"] for m in metadata],
            "raw_directory": str(raw_dir),
            "raw_artifacts": artifacts,
            "missed_events_per_run": [m["missed_events"] for m in metadata],
        }
    )
    if any(values["missed_events_per_run"]):
        raise ValueError("A worker reported missed events; inspect the raw runs before admission.")
    after = _preflight(smoke)
    if after["syssimx_revision"] != source["syssimx_revision"]:
        raise RuntimeError("Source revision changed during the campaign.")
    (raw_dir / "manifest.json").write_text(json.dumps(values, indent=2) + "\n", encoding="utf-8")
    return record(RESULT_ID, values, notebook=NOTEBOOK, smoke=smoke, directory=results)


def run_experiment(results: Path, *, smoke: bool = False, raw_dir: Path | None = None) -> Path:
    """Notebook entry point: keep all NGSolve state inside subprocesses."""
    command = [sys.executable, "-m", "evidence.trajectory", "--results", str(results.resolve())]
    if raw_dir is not None:
        command += ["--raw-dir", str(raw_dir.resolve())]
    _stream_process(command + (["--smoke"] if smoke else []))
    return results / (RESULT_ID + (".smoke.json" if smoke else ".json"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true", help="50 ms diagnostic; never quotable")
    parser.add_argument("--worker", choices=("full_fem", "switched"))
    parser.add_argument("--run-path", type=Path)
    parser.add_argument("--raw-dir", type=Path)
    parser.add_argument("--results", type=Path)
    parser.add_argument(
        "--preflight", action="store_true", help="check clean pushed source without running"
    )
    args = parser.parse_args()
    from record import paper_results_dir

    from evidence import repo_root

    repo_root(Path(__file__).resolve().parent)
    _pin_threads()
    if args.preflight:
        print(json.dumps(_preflight(args.smoke), indent=2))
    elif args.worker:
        if args.run_path is None:
            parser.error("--worker requires --run-path")
        _worker(args.worker, args.run_path, args.smoke)
    else:
        target = args.results if args.results is not None else paper_results_dir()[0]
        print("Recorded:", _campaign(args.raw_dir, target, args.smoke), flush=True)


if __name__ == "__main__":
    main()
