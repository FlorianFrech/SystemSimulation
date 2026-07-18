"""Unit tests for the declarative system loader (YAML/JSON) and the CLI."""

import json

import numpy as np
import pytest
import yaml

from syssimx.system import SimulationResult
from syssimx.system.algorithms import GaussSeidelAlgorithm, JacobiAlgorithm
from syssimx.system.loader import (
    ConfigError,
    build_system,
    load_config,
    run_from_config,
)

BASE_CONFIG = {
    "system": {"name": "LoaderDemo"},
    "components": [
        {
            "name": "Src",
            "class": "tests.fixtures.components:ConstantSource",
            "args": {"value": 1.0},
        },
        {
            "name": "Int",
            "class": "tests.fixtures.components:IntegratorComponent",
            "args": {"x0": 0.0},
        },
    ],
    "connections": [{"src": "Src.y", "dst": "Int.u"}],
    "algorithm": {"type": "gauss_seidel"},
    "run": {"t0": 0.0, "tf": 1.0, "dt": 0.1},
}


def _config() -> dict:
    return json.loads(json.dumps(BASE_CONFIG))  # deep copy


# ============================================================================
# build_system
# ============================================================================
class TestBuildSystem:
    def test_builds_named_system_with_components(self):
        system = build_system(_config())
        assert system.name == "LoaderDemo"
        assert set(system.components) == {"Src", "Int"}
        assert len(system.connections) == 1
        assert isinstance(system.algorithm, GaussSeidelAlgorithm)

    def test_algorithm_selection(self):
        config = _config()
        config["algorithm"] = {"type": "jacobi"}
        system = build_system(config)
        assert isinstance(system.algorithm, JacobiAlgorithm)

    def test_mapping_endpoint_form(self):
        config = _config()
        config["connections"] = [
            {"src": {"component": "Src", "port": "y"}, "dst": {"component": "Int", "port": "u"}}
        ]
        system = build_system(config)
        c = system.connections[0]
        assert (c.src_comp, c.src_port, c.dst_comp, c.dst_port) == ("Src", "y", "Int", "u")

    def test_constructor_args_applied(self):
        config = _config()
        config["components"][0]["args"] = {"value": 42.0}
        system = build_system(config)
        assert system.components["Src"].value == 42.0


# ============================================================================
# Validation errors
# ============================================================================
class TestConfigErrors:
    def test_missing_components(self):
        with pytest.raises(ConfigError, match="at least one component"):
            build_system({"system": {"name": "X"}})

    def test_unknown_algorithm(self):
        config = _config()
        config["algorithm"] = {"type": "runge_kutta"}
        with pytest.raises(ConfigError, match="Unknown algorithm type 'runge_kutta'"):
            build_system(config)

    def test_bad_class_spec_format(self):
        config = _config()
        config["components"][0]["class"] = "no.colon.here"
        with pytest.raises(ConfigError, match="module.path:ClassName"):
            build_system(config)

    def test_unimportable_module(self):
        config = _config()
        config["components"][0]["class"] = "nonexistent.module:Thing"
        with pytest.raises(ConfigError, match="Cannot import module"):
            build_system(config)

    def test_unknown_class_in_module(self):
        config = _config()
        config["components"][0]["class"] = "tests.fixtures.components:NoSuchClass"
        with pytest.raises(ConfigError, match="has no attribute"):
            build_system(config)

    def test_bad_constructor_args(self):
        config = _config()
        config["components"][0]["args"] = {"bogus_kwarg": 1}
        with pytest.raises(ConfigError, match="cannot construct"):
            build_system(config)

    def test_connection_to_unknown_component(self):
        config = _config()
        config["connections"] = [{"src": "Ghost.y", "dst": "Int.u"}]
        with pytest.raises(ConfigError, match="unknown component 'Ghost'"):
            build_system(config)

    def test_invalid_endpoint_string(self):
        config = _config()
        config["connections"] = [{"src": "NoDotHere", "dst": "Int.u"}]
        with pytest.raises(ConfigError, match="Invalid connection endpoint"):
            build_system(config)

    def test_missing_run_settings(self):
        config = _config()
        del config["run"]
        with pytest.raises(ConfigError, match="Run settings missing"):
            run_from_config(config)


# ============================================================================
# File loading (YAML and JSON)
# ============================================================================
class TestFileLoading:
    def test_yaml_roundtrip(self, tmp_path):
        path = tmp_path / "system.yaml"
        path.write_text(yaml.safe_dump(_config()))
        system = build_system(path)
        assert system.name == "LoaderDemo"

    def test_json_roundtrip(self, tmp_path):
        path = tmp_path / "system.json"
        path.write_text(json.dumps(_config()))
        system = build_system(path)
        assert system.name == "LoaderDemo"

    def test_non_mapping_top_level_rejected(self, tmp_path):
        path = tmp_path / "bad.yaml"
        path.write_text("- just\n- a\n- list\n")
        with pytest.raises(ConfigError, match="must be a mapping"):
            load_config(path)


# ============================================================================
# run_from_config
# ============================================================================
class TestRunFromConfig:
    def test_runs_and_returns_result(self):
        result = run_from_config(_config())
        assert isinstance(result, SimulationResult)
        t_vals, ports = result["Int"]
        assert np.isclose(ports["y"][-1], 1.0)

    def test_overrides_take_precedence(self):
        result = run_from_config(_config(), tf=2.0)
        assert result.tf == 2.0
        _, ports = result["Int"]
        assert np.isclose(ports["y"][-1], 2.0)

    def test_from_file(self, tmp_path):
        path = tmp_path / "system.yaml"
        path.write_text(yaml.safe_dump(_config()))
        result = run_from_config(path)
        assert result.system_name == "LoaderDemo"


# ============================================================================
# CLI
# ============================================================================
class TestCLI:
    def _write_config(self, tmp_path):
        path = tmp_path / "system.yaml"
        path.write_text(yaml.safe_dump(_config()))
        return path

    def test_run_command(self, tmp_path, capsys):
        from syssimx.cli import main

        path = self._write_config(tmp_path)
        out_csv = tmp_path / "results.csv"
        code = main(["run", str(path), "--quiet", "-o", str(out_csv)])
        captured = capsys.readouterr()

        assert code == 0
        assert "Completed 'LoaderDemo'" in captured.out
        assert out_csv.exists()

    def test_run_command_with_overrides(self, tmp_path, capsys):
        from syssimx.cli import main

        path = self._write_config(tmp_path)
        code = main(["run", str(path), "--quiet", "--tf", "0.5"])
        captured = capsys.readouterr()
        assert code == 0
        assert "[0.0, 0.5]" in captured.out

    def test_describe_command(self, tmp_path, capsys):
        from syssimx.cli import main

        path = self._write_config(tmp_path)
        code = main(["describe", str(path), "--initialize"])
        captured = capsys.readouterr()
        assert code == 0
        assert "System 'LoaderDemo'" in captured.out
        assert "Generation 0" in captured.out

    def test_config_error_exit_code(self, tmp_path, capsys):
        from syssimx.cli import main

        path = tmp_path / "bad.yaml"
        path.write_text(
            yaml.safe_dump(
                {
                    "system": {"name": "Bad"},
                    "components": [{"name": "X", "class": "nonexistent.module:Y"}],
                    "run": {"t0": 0, "tf": 1, "dt": 0.1},
                }
            )
        )
        code = main(["run", str(path), "--quiet"])
        captured = capsys.readouterr()
        assert code == 2
        assert "error:" in captured.err
