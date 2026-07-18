"""Unit tests for SimulationResult, System.run progress callback, and describe()."""

import numpy as np
import pandas as pd

from syssimx import Connection, SimulationResult, System
from tests.fixtures.components import ConstantSource, IntegratorComponent


def _make_system() -> System:
    src = ConstantSource(name="Src", value=1.0)
    integ = IntegratorComponent(name="Int", x0=0.0)
    system = System(name="ResultDemo")
    system.add_component(src)
    system.add_component(integ)
    system.add_connection(Connection(src_comp="Src", src_port="y", dst_comp="Int", dst_port="u"))
    system.initialize(t0=0.0)
    return system


# ============================================================================
# SimulationResult from System.run
# ============================================================================
class TestSimulationResult:
    def test_run_returns_result_with_metadata(self):
        system = _make_system()
        result = system.run(t0=0.0, tf=1.0, dt=0.1)

        assert isinstance(result, SimulationResult)
        assert result.system_name == "ResultDemo"
        assert result.t0 == 0.0
        assert result.tf == 1.0
        assert result.algorithm == "GaussSeidelAlgorithm"
        assert result.wall_time >= 0.0
        assert set(result.component_names) == {"Src", "Int"}

    def test_getitem_and_contains(self):
        system = _make_system()
        result = system.run(t0=0.0, tf=0.5, dt=0.1)

        assert "Int" in result
        assert "Nope" not in result
        t_vals, ports = result["Int"]
        assert len(t_vals) > 0
        assert "y" in ports

    def test_to_dataframe_long_format(self):
        system = _make_system()
        result = system.run(t0=0.0, tf=1.0, dt=0.1)

        df = result.to_dataframe()
        assert list(df.columns) == ["component", "port", "time", "value"]
        assert set(df["component"].unique()) == {"Src", "Int"}
        # Integrator of constant 1.0 ends at ~1.0
        y_int = df[(df["component"] == "Int") & (df["port"] == "y")]
        assert np.isclose(y_int["value"].iloc[-1], 1.0)

    def test_to_dataframe_wide_format(self):
        system = _make_system()
        result = system.run(t0=0.0, tf=1.0, dt=0.1)

        df = result.to_dataframe(component="Int")
        assert "time" in df.columns
        assert "y" in df.columns
        assert np.isclose(df["y"].iloc[-1], 1.0)

    def test_to_csv_roundtrip(self, tmp_path):
        system = _make_system()
        result = system.run(t0=0.0, tf=0.5, dt=0.1)

        path = result.to_csv(tmp_path / "out.csv", component="Int")
        assert path.exists()
        df = pd.read_csv(path)
        assert "y" in df.columns
        assert len(df) > 0

    def test_from_system_captures_events_key(self):
        system = _make_system()
        system.run(t0=0.0, tf=0.2, dt=0.1)
        result = SimulationResult.from_system(system, t0=0.0, tf=0.2, dt=0.1)
        # Events are captured separately, not as a component history
        assert "Events" not in result.histories

    def test_empty_result_dataframe(self):
        result = SimulationResult(
            system_name="Empty",
            t0=0.0,
            tf=1.0,
            dt=0.1,
            wall_time=0.0,
            algorithm="GaussSeidelAlgorithm",
            histories={},
        )
        df = result.to_dataframe()
        assert df.empty
        assert list(df.columns) == ["component", "port", "time", "value"]


# ============================================================================
# Progress callback
# ============================================================================
class TestProgressCallback:
    def test_progress_called_per_macro_step(self):
        system = _make_system()
        calls: list[tuple[float, float]] = []
        system.run(t0=0.0, tf=1.0, dt=0.1, progress=lambda t, tf: calls.append((t, tf)))

        assert len(calls) == 10
        assert all(tf == 1.0 for _, tf in calls)
        assert np.isclose(calls[-1][0], 1.0)
        # Monotonically increasing times
        times = [t for t, _ in calls]
        assert times == sorted(times)

    def test_run_without_progress_still_works(self):
        system = _make_system()
        result = system.run(t0=0.0, tf=0.3, dt=0.1)
        assert isinstance(result, SimulationResult)


# ============================================================================
# system.describe()
# ============================================================================
class TestDescribe:
    def test_describe_after_initialize(self):
        system = _make_system()
        report = system.describe()

        assert "System 'ResultDemo'" in report
        assert "GaussSeidelAlgorithm" in report
        assert "Src (ConstantSource)" in report
        assert "Int (IntegratorComponent)" in report
        assert "Src.y -> Int.u" in report
        assert "Generation 0" in report
        assert "Algebraic loops: none detected" in report

    def test_describe_before_initialize(self):
        src = ConstantSource(name="Src", value=1.0)
        system = System(name="Fresh")
        system.add_component(src)
        report = system.describe()

        assert "Initialized: False" in report
        assert "not yet computed" in report

    def test_describe_reports_algebraic_loops(self):
        from tests.fixtures.systems.algebraic_loop_systems import (
            create_small_algebraic_loop_system,
        )

        system, _, _ = create_small_algebraic_loop_system()
        system.initialize(t0=0.0)
        report = system.describe()
        assert "Algebraic loops (1)" in report

    def test_describe_is_printable_multiline(self):
        system = _make_system()
        report = system.describe()
        assert isinstance(report, str)
        assert report.count("\n") >= 5
