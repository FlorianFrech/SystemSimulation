"""Fast checks for the separate single-thread trajectory experiment."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "notebooks"))

from evidence.trajectory import make_scenario, summarize_traces, trajectory_metrics


def trace(*, switched=False):
    return {
        "t": np.array([0.0, 0.5, 1.0]),
        "theta": np.array([0.0, 0.2, 0.0]),
        "omega": np.array([0.0, 0.1, 0.0]),
        "sensor_t": np.array([0.01, 0.5, 1.0]),
        "sensor_v_out": np.array([0.0, 1.0, 0.0]),
        "switch_times": np.array([0.1, 0.8] if switched else []),
        "switch_from": np.array(["FEM", "FMU"] if switched else [], dtype="U3"),
        "switch_to": np.array(["FMU", "FEM"] if switched else [], dtype="U3"),
        "contact_times": np.array([]),
        "event_history_json": np.array("[]"),
    }


def test_scenario_preserves_the_recorded_timing_policy():
    scenario = make_scenario()
    assert scenario.t_end == 1.0
    assert scenario.macro_dt == scenario.fem_internal_dt == 0.001
    assert scenario.switch_threshold_rad == 0.085
    assert scenario.switch_band_rad == 0.015
    assert scenario.ngsolve_threads == 1
    assert scenario.n_repeats == 2
    assert scenario.n_warmup == 0
    assert not scenario.contact


def test_union_grid_catches_a_peak_on_the_reference_grid():
    baseline = {
        "t": np.array([0.0, 0.5, 1.0]),
        "theta": np.array([0.0, 2.0, 0.0]),
        "omega": np.zeros(3),
    }
    switched = {"t": np.array([0.0, 1.0]), "theta": np.zeros(2), "omega": np.zeros(2)}
    metrics = trajectory_metrics(baseline, switched)
    assert metrics["max_abs_delta_rad"] == 2.0
    assert metrics["t_max_abs_delta_s"] == 0.5
    assert metrics["e_2_rad"] == pytest.approx(np.sqrt(2.0))


def test_duplicate_event_sample_uses_the_right_limit():
    baseline = {
        "t": np.array([0.0, 0.5, 0.5, 1.0]),
        "theta": np.array([0.0, 99.0, 2.0, 0.0]),
        "omega": np.zeros(4),
    }
    assert trajectory_metrics(baseline, trace())["max_abs_delta_rad"] == 1.8


def test_comparison_refuses_extrapolation():
    baseline = trace()
    baseline["t"] = np.array([0.1, 0.5, 1.0])
    with pytest.raises(ValueError, match="same endpoints"):
        trajectory_metrics(baseline, trace())


def test_admission_checks_sensor_output_even_if_plant_repeats():
    base = [trace(), trace()]
    switched = [trace(switched=True), trace(switched=True)]
    switched[1]["sensor_v_out"][1] += 1.0
    with pytest.raises(ValueError, match="sensor_v_out"):
        summarize_traces(base, switched, make_scenario())


def test_signed_zero_is_not_bit_identical():
    base = [trace(), trace()]
    base[1]["theta"][0] = -0.0
    with pytest.raises(ValueError, match="theta"):
        summarize_traces(base, [trace(switched=True), trace(switched=True)], make_scenario())


@pytest.mark.parametrize("problem", ["nan", "time", "horizon", "no_switch"])
def test_invalid_campaign_cannot_be_admitted(problem):
    base = [trace(), trace()]
    switched = [trace(switched=True), trace(switched=True)]
    if problem == "nan":
        base[0]["theta"][1] = np.nan
    elif problem == "time":
        base[0]["t"] = np.array([0.0, 0.5, 0.4])
    elif problem == "horizon":
        base[0]["t"][-1] = 0.9
    else:
        switched = [trace(), trace()]
    with pytest.raises(ValueError):
        summarize_traces(base, switched, make_scenario())


def test_valid_campaign_emits_counts_and_pair_metrics():
    result = summarize_traces(
        [trace(), trace()], [trace(switched=True), trace(switched=True)], make_scenario()
    )
    assert result["repeatability"]["Full FEM"]["bit_identical"]
    assert result["repeatability"]["Switched FEM/FMU"]["bit_identical"]
    assert result["runs_per_case"] == 2
    assert len(result["per_pair"]) == 2
    assert result["max_abs_delta_rad"] == 0.0


@pytest.mark.parametrize(
    "problem", ["revision", "thread", "scenario", "fmu", "backend", "empty_fmu"]
)
def test_workers_cannot_mix_configurations_or_inputs(problem):
    from copy import deepcopy

    from evidence.trajectory import _verify_workers

    source = {
        "syssimx_revision": "v0.4.3-19-gabcdef0",
        "syssimx_version": "0.4.3",
        "python": "3.13.15",
        "platform": "Windows",
        "dirty_measurement_paths": [],
        "ngsolve_threads_pinned": True,
        "ngsolve_num_threads_env": "1",
    }
    worker = {
        "case": "Full FEM",
        "scenario": make_scenario().provenance(),
        "provenance": source.copy(),
        "fmu_sha256": {"sensor.fmu": "abc"},
        "backend_versions": {"ngsolve": "6.2.2607"},
    }
    workers = [deepcopy(worker), deepcopy(worker)]
    if problem == "revision":
        workers[1]["provenance"]["syssimx_revision"] = "another revision"
    elif problem == "thread":
        workers[1]["provenance"]["ngsolve_num_threads_env"] = "6"
    elif problem == "scenario":
        workers[1]["scenario"]["switch_threshold_rad"] = 0.1
    elif problem == "fmu":
        workers[1]["fmu_sha256"]["sensor.fmu"] = "changed export"
    elif problem == "backend":
        workers[1]["backend_versions"]["ngsolve"] = "a different version"
    else:
        for worker in workers:
            worker["fmu_sha256"] = {}
    with pytest.raises(ValueError):
        _verify_workers(workers, make_scenario(), source, smoke=False)


def test_production_refuses_uncommitted_code_before_running(monkeypatch):
    import record
    from evidence.trajectory import _preflight

    monkeypatch.delenv("SYSSIMX_ALLOW_DIRTY_RESULTS", raising=False)
    monkeypatch.setattr(
        record,
        "provenance",
        lambda **kw: {"dirty_measurement_paths": ["notebooks/evidence/trajectory.py"]},
    )
    with pytest.raises(RuntimeError, match="Commit and push"):
        _preflight(smoke=False)


def test_child_pin_does_not_change_notebook_environment(monkeypatch, tmp_path):
    import evidence.trajectory as trajectory

    captured = {}

    class Process:
        stdout = iter(["LOG_SOLVER | info | native log\n", "Saved worker\n"])

        def __init__(self, command, **kwargs):
            captured.update(kwargs)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def wait(self):
            return 0

    monkeypatch.setenv("NGS_NUM_THREADS", "6")
    monkeypatch.setattr(trajectory.subprocess, "Popen", Process)
    log = tmp_path / "worker.log"
    trajectory._stream_process(["worker"], log_path=log)
    assert trajectory.os.environ["NGS_NUM_THREADS"] == "6"
    assert captured["env"]["NGS_NUM_THREADS"] == "1"
    assert "native log" in log.read_text(encoding="utf-8")


def test_malformed_switch_history_cannot_be_admitted():
    switched = [trace(switched=True), trace(switched=True)]
    switched[0]["switch_times"] = np.array([0.1])
    with pytest.raises(ValueError, match="Switch identities"):
        summarize_traces([trace(), trace()], switched, make_scenario())


def test_hash_collection_uses_the_actual_fmu_component_path(tmp_path):
    import hashlib
    from types import SimpleNamespace

    from evidence.trajectory import _fmu_input_hashes

    archive = tmp_path / "sensor.fmu"
    archive.write_bytes(b"actual model archive")
    # FMUComponent stores the constructor's fmu_path in _path, not fmu_path.
    component = SimpleNamespace(_path=str(archive))
    hashes = _fmu_input_hashes([component, component, object()], tmp_path, expected_count=1)
    assert hashes == {"sensor.fmu": hashlib.sha256(archive.read_bytes()).hexdigest()}


def test_missing_fmu_inputs_cannot_silently_form_an_empty_manifest(tmp_path):
    from evidence.trajectory import _fmu_input_hashes

    with pytest.raises(ValueError, match="Expected 5 FMU inputs"):
        _fmu_input_hashes([object()], tmp_path, expected_count=5)
