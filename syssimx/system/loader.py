"""Declarative system descriptions: build a ``System`` from YAML/JSON.

A system description is a mapping with the following shape (YAML shown;
JSON with the same structure is equally supported)::

    system:
      name: Quickstart
    components:
      - name: Source
        class: "my_package.components:LinearSource"   # "module:ClassName"
        args: {a: 1.0, b: 0.0}                        # constructor kwargs
        parameters: {gain: 2.0}                       # set_parameters(...) after construction
    connections:
      - src: Source.y            # "Component.port" (split at the first dot) ...
        dst: Integrator.u
      - src: {component: A, port: out}                # ... or explicit mapping form
        dst: {component: B, port: in}
    event_connections:                                # optional
      - src: Plant.wall_hit
        dst: Controller.reset
    algorithm:                                        # optional (default gauss_seidel)
      type: gauss_seidel        # jacobi | gauss_seidel | hybrid | ijcsa
    run:                                              # optional defaults for run_from_config/CLI
      t0: 0.0
      tf: 5.0
      dt: 0.1

Component classes are resolved by import path, so any installed
``CoSimComponent`` subclass — including user-defined ones — can be used
without registration. Use :func:`build_system` to assemble a ``System`` and
:func:`run_from_config` to assemble, initialize, and run it in one call.
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any

import yaml

from ..core.base import CoSimComponent
from .algorithms import (
    Algorithm,
    GaussSeidelAlgorithm,
    HybridAlgorithm,
    IJCSAAlgorithm,
    JacobiAlgorithm,
)
from .connection import Connection, EventConnection
from .results import SimulationResult
from .system import System

ALGORITHMS: dict[str, type[Algorithm]] = {
    "jacobi": JacobiAlgorithm,
    "gauss_seidel": GaussSeidelAlgorithm,
    "hybrid": HybridAlgorithm,
    "ijcsa": IJCSAAlgorithm,
}


class ConfigError(ValueError):
    """Raised when a system description is invalid."""


# ----------------------------------------------------------------------------
# Config loading
# ----------------------------------------------------------------------------
def load_config(path: str | Path) -> dict[str, Any]:
    """Load a system description from a YAML or JSON file.

    The format is chosen by file extension: ``.json`` is parsed as JSON,
    everything else (``.yaml``/``.yml``) as YAML.

    Args:
        path: Path to the description file.

    Returns:
        The parsed configuration mapping.

    Raises:
        ConfigError: If the file does not contain a mapping at top level.
    """
    path = Path(path)
    text = path.read_text()
    if path.suffix.lower() == ".json":
        config = json.loads(text)
    else:
        config = yaml.safe_load(text)
    if not isinstance(config, dict):
        raise ConfigError(f"{path}: top level of a system description must be a mapping")
    return config


# ----------------------------------------------------------------------------
# System assembly
# ----------------------------------------------------------------------------
def build_system(config: dict[str, Any] | str | Path) -> System:
    """Assemble a :class:`System` from a description.

    Args:
        config: A parsed configuration mapping, or a path to a YAML/JSON
            file (which is loaded via :func:`load_config`).

    Returns:
        The assembled (not yet initialized) system.

    Raises:
        ConfigError: On any invalid or missing configuration entry.
    """
    if isinstance(config, (str, Path)):
        config = load_config(config)

    name = config.get("system", {}).get("name", "System")
    system = System(name=name)

    components = config.get("components")
    if not components:
        raise ConfigError("System description must define at least one component")

    for entry in components:
        system.add_component(_build_component(entry))

    for entry in config.get("connections", []) or []:
        src_comp, src_port = _parse_endpoint(entry, "src")
        dst_comp, dst_port = _parse_endpoint(entry, "dst")
        _require_component(system, src_comp, entry)
        _require_component(system, dst_comp, entry)
        system.add_connection(
            Connection(src_comp=src_comp, src_port=src_port, dst_comp=dst_comp, dst_port=dst_port)
        )

    for entry in config.get("event_connections", []) or []:
        src_comp, src_event = _parse_endpoint(entry, "src")
        dst_comp, dst_port = _parse_endpoint(entry, "dst")
        _require_component(system, src_comp, entry)
        _require_component(system, dst_comp, entry)
        system.add_event_connection(
            EventConnection(
                src_comp=src_comp, src_port=src_event, dst_comp=dst_comp, dst_port=dst_port
            )
        )

    algo_cfg = config.get("algorithm")
    if algo_cfg:
        algo_type = algo_cfg.get("type")
        if algo_type not in ALGORITHMS:
            raise ConfigError(
                f"Unknown algorithm type '{algo_type}'. "
                f"Available: {', '.join(sorted(ALGORITHMS))}"
            )
        system.set_algorithm(ALGORITHMS[algo_type]())

    return system


def run_from_config(
    config: dict[str, Any] | str | Path,
    t0: float | None = None,
    tf: float | None = None,
    dt: float | None = None,
    progress: Any = None,
) -> SimulationResult:
    """Assemble, initialize, and run a system from a description.

    Run settings are taken from the description's ``run`` section; the
    ``t0``/``tf``/``dt`` arguments override individual entries.

    Args:
        config: Configuration mapping or path to a YAML/JSON file.
        t0: Override for the start time.
        tf: Override for the end time.
        dt: Override for the macro step size.
        progress: Optional progress callback forwarded to ``System.run``.

    Returns:
        The :class:`SimulationResult` of the run.

    Raises:
        ConfigError: If any of ``t0``/``tf``/``dt`` is neither configured
            nor provided as an argument.
    """
    if isinstance(config, (str, Path)):
        config = load_config(config)

    run_cfg = dict(config.get("run", {}) or {})
    if t0 is not None:
        run_cfg["t0"] = t0
    if tf is not None:
        run_cfg["tf"] = tf
    if dt is not None:
        run_cfg["dt"] = dt

    missing = [key for key in ("t0", "tf", "dt") if key not in run_cfg]
    if missing:
        raise ConfigError(
            f"Run settings missing: {', '.join(missing)} "
            "(add a 'run:' section to the description or pass them as arguments)"
        )

    system = build_system(config)
    system.initialize(t0=float(run_cfg["t0"]))
    return system.run(
        t0=float(run_cfg["t0"]),
        tf=float(run_cfg["tf"]),
        dt=float(run_cfg["dt"]),
        progress=progress,
    )


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def _build_component(entry: dict[str, Any]) -> CoSimComponent:
    """Instantiate one component from its description entry."""
    if "name" not in entry:
        raise ConfigError(f"Component entry missing 'name': {entry}")
    if "class" not in entry:
        raise ConfigError(f"Component '{entry['name']}' missing 'class' (module:ClassName)")

    cls = _resolve_class(entry["class"])
    args = entry.get("args", {}) or {}
    try:
        component = cls(name=entry["name"], **args)
    except TypeError as exc:
        raise ConfigError(
            f"Component '{entry['name']}': cannot construct {entry['class']} "
            f"with args {args}: {exc}"
        ) from exc

    if not isinstance(component, CoSimComponent):
        raise ConfigError(
            f"Component '{entry['name']}': {entry['class']} is not a CoSimComponent"
        )

    parameters = entry.get("parameters")
    if parameters:
        component.set_parameters(**parameters)
    return component


def _resolve_class(spec: str) -> type:
    """Resolve a ``"module.path:ClassName"`` import spec to a class."""
    if ":" not in spec:
        raise ConfigError(
            f"Invalid class spec '{spec}': expected 'module.path:ClassName'"
        )
    module_path, class_name = spec.rsplit(":", 1)
    try:
        module = importlib.import_module(module_path)
    except ImportError as exc:
        raise ConfigError(f"Cannot import module '{module_path}': {exc}") from exc
    try:
        cls = getattr(module, class_name)
    except AttributeError as exc:
        raise ConfigError(
            f"Module '{module_path}' has no attribute '{class_name}'"
        ) from exc
    if not isinstance(cls, type):
        raise ConfigError(f"'{spec}' does not resolve to a class")
    return cls


def _parse_endpoint(entry: dict[str, Any], key: str) -> tuple[str, str]:
    """Parse a connection endpoint: ``"Comp.port"`` or ``{component, port}``."""
    if key not in entry:
        raise ConfigError(f"Connection entry missing '{key}': {entry}")
    value = entry[key]
    if isinstance(value, dict):
        try:
            return str(value["component"]), str(value["port"])
        except KeyError as exc:
            raise ConfigError(
                f"Connection endpoint mapping needs 'component' and 'port': {value}"
            ) from exc
    if isinstance(value, str) and "." in value:
        comp, port = value.split(".", 1)
        return comp, port
    raise ConfigError(
        f"Invalid connection endpoint '{value}': "
        "use 'Component.port' or {component: ..., port: ...}"
    )


def _require_component(system: System, comp_name: str, entry: dict[str, Any]) -> None:
    """Raise a helpful error when a connection references an unknown component."""
    if comp_name not in system.components:
        raise ConfigError(
            f"Connection {entry} references unknown component '{comp_name}'. "
            f"Defined components: {', '.join(system.components)}"
        )
