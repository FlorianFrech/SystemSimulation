"""Shared code for the evidence notebooks in `notebooks/`.

Before this package, notebooks 5, 6, 7 and 9 each redeclared the switching
plant, the control loop, the phase instrumentation, and the error metrics.
Notebooks 6 and 7 alone shared 25 definitions by copy, so a fix applied to one
did not reach the other.

Import from here; declare only what is genuinely specific to one scenario::

    from evidence import repo_root
    REPO = repo_root()           # puts the repo and notebooks/ on sys.path
    import evidence as ev        # heavy submodules resolve from here on

Every notebook builds exactly one :class:`~evidence.scenario.Scenario` in its
configuration cell and passes it down, so the parameters a run used travel with
the run and reach ``record()`` as provenance.

**Attribute access is lazy.** ``repo_root`` and ``Scenario`` must be importable
before ``sys.path`` points at the repository, and a notebook that needs neither
the FEM backend nor the FMU examples must not be made to import them. Everything
else is resolved on first use through :pep:`562`.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

from .scenario import CONTACT_SCENARIO, NO_CONTACT_SCENARIO, Scenario

# name -> submodule it lives in. Resolved on first attribute access, by which
# time repo_root() has run and the heavy dependencies are importable.
_LAZY = {
    "PLANT_NAME": "plant",
    "SwitchingPendulum": "plant",
    "FemToFemPendulum": "plant",
    "TimeGatedRegionKey": "plant",
    "region_key_for": "plant",
    "absolute_theta": "plant",
    "scalar_value": "plant",
    "make_fem_parameters": "plant",
    "discover_fmus": "loop",
    "PIDController": "loop",
    "wall_contact_indicator": "loop",
    "declare_plant_feedthrough": "loop",
    "create_common_components": "loop",
    "assemble_system": "loop",
    "PHASES": "instrument",
    "DISCARDED_PHASES": "instrument",
    "ACCEPTED": "instrument",
    "TRIAL": "instrument",
    "BISECTION": "instrument",
    "EVENTS": "instrument",
    "OTHER": "instrument",
    "PhaseTracker": "instrument",
    "PhaseTimer": "instrument",
    "instrument_algorithm": "instrument",
    "instrument_step": "instrument",
    "instrumented_hybrid": "instrument",
    "mode_intervals": "analysis",
    "mode_active_time": "analysis",
    "contact_event_times": "analysis",
    "fem_contact_closures": "analysis",
    "check_contact_dispatch": "analysis",
    "distance_to_grid": "analysis",
    "trajectory_error_metrics": "analysis",
    "run_measured_case": "analysis",
}

__all__ = ["repo_root", "Scenario", "CONTACT_SCENARIO", "NO_CONTACT_SCENARIO", *sorted(_LAZY)]


def __getattr__(name: str):
    try:
        module_name = _LAZY[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    module = importlib.import_module(f".{module_name}", __name__)
    value = getattr(module, name)
    globals()[name] = value  # resolve once
    return value


def __dir__():
    return sorted(__all__)


def repo_root(start: Path | None = None) -> Path:
    """Nearest ancestor holding `pyproject.toml`, with `notebooks/` on the path.

    Every notebook opens with this instead of its own four-line while-loop.
    `notebooks/` goes on the path too because `plot_setup.py` and `record.py`
    live next to the notebook, which is not the working directory when it is
    executed headlessly by nbmake or papermill.
    """
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").exists():
            for path in (candidate, candidate / "notebooks"):
                if str(path) not in sys.path:
                    sys.path.insert(0, str(path))
            return candidate
    raise RuntimeError("Could not locate the repository root from " + str(current))
