"""Emit a paper number as a machine-readable artifact.

Every value that reaches the manuscript goes through :func:`record`. It writes
``results/<figure_id>.json`` with the value *and* the provenance needed to decide
whether the value may still be quoted: the framework revision it was measured
at, the interpreter and machine, the producing notebook, and whether the run was
a smoke run.

The rule this file exists to enforce is in
``guideline/planning/evidence_plan.md`` section 6: a number that was transcribed
from notebook stdout cannot be re-checked without rerunning the notebook, and
notebook 6 costs about 65 minutes. Numbers are emitted, not read off a plot.

Usage::

    from record import record

    record(
        "F1",
        {"placement_error_s": errors, "macro_steps_s": steps},
        notebook="09_switch_placement_convergence",
        smoke=SMOKE,
    )
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

__all__ = [
    "record",
    "provenance",
    "results_dir",
    "paper_results_dir",
    "MEASUREMENT_PATHS",
]


def _repository_root(start: Path | None = None) -> Path:
    """Nearest ancestor holding ``AGENTS.md`` (paper repo) or ``pyproject.toml``.

    Both markers are accepted because the evidence notebooks run from the
    SysSimX source repository while their artifacts belong to the paper
    repository; whichever tree the notebook sits in, the root resolves.
    """
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "AGENTS.md").exists() or (candidate / "pyproject.toml").exists():
            return candidate
    return current


def results_dir(start: Path | None = None) -> Path:
    """``results/`` under the resolved repository root, created on demand."""
    directory = _repository_root(start) / "results"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _threading_provenance() -> dict[str, Any]:
    """How the FEM backend was threaded, which decides whether a run repeats.

    `issues.md` REPRO-02: `FEMPendulum._do_step_internal` enters `TaskManager()`
    without pinning a thread count, so NGSolve's parallel reductions accumulate
    in scheduling-dependent order and an identical run does not reproduce
    itself. The author decided on 2026-09-11 not to pin it - a serial
    configuration is not one anyone would deploy - so evidence is made robust by
    repetition instead.

    NGSolve exposes `SetNumThreads` but no getter, so the count cannot be read
    back. What is recordable is whether anything pinned it and how many cores
    were available. Absence of a pin is itself the fact worth recording: it says
    a single run of this artifact is not reproducible.
    """
    pinned = os.environ.get("NGS_NUM_THREADS")
    return {
        "ngsolve_threads_pinned": pinned is not None,
        "ngsolve_num_threads_env": pinned,
        "cpu_count": os.cpu_count(),
        "reproducible_single_run": pinned is not None,
    }


def _assert_quotable(payload_provenance: dict, smoke: bool) -> None:
    """Refuse to write a campaign file from a tree that cannot be recovered.

    ``evidence_plan.md`` D1: until the measured revision is pushed and tagged, a
    reader cannot obtain it, so a file without the ``.smoke`` suffix - which
    ``results/README.md`` declares quotable - is a promise the repository cannot
    keep. Uncommitted changes are the same problem in stronger form: the revision
    string names a commit that does not describe what actually ran.

    Only the *measured surface* counts, `MEASUREMENT_PATHS`. An edited notebook,
    `issues.md`, a doc or a test does not change a recorded number, and refusing
    on those made the check an obstacle. Editing the framework, a plant, the
    Modelica sources, the FMU artifacts, or the shared evidence code does.

    Set ``SYSSIMX_ALLOW_DIRTY_RESULTS=1`` to override, deliberately.
    """
    if smoke or os.environ.get("SYSSIMX_ALLOW_DIRTY_RESULTS") == "1":
        return

    revision = payload_provenance.get("syssimx_revision") or ""
    dirty = payload_provenance.get("dirty_measurement_paths")

    if dirty is None:
        # Not a source checkout, or git could not answer. The revision string is
        # then the only evidence, and an artifact whose revision is unknown
        # cannot be obtained by a reader either.
        if revision and not revision.endswith("-dirty"):
            return
        raise RuntimeError(
            f"Cannot establish which revision produced this result "
            f"(revision {revision or 'unknown'}). A file without the .smoke suffix "
            f"is quotable by the convention in results/README.md. Run from a clean "
            f"source checkout, use smoke=True, or set SYSSIMX_ALLOW_DIRTY_RESULTS=1."
        )

    if dirty:
        listed = "\n  ".join(dirty[:10])
        more = f"\n  ... and {len(dirty) - 10} more" if len(dirty) > 10 else ""
        raise RuntimeError(
            f"Refusing to write a campaign result: {len(dirty)} uncommitted change(s) "
            f"on the measured surface, so revision {revision} does not describe what "
            f"ran and a reader cannot obtain it.\n  {listed}{more}\n"
            f"Commit these, run with smoke=True, or set SYSSIMX_ALLOW_DIRTY_RESULTS=1. "
            f"Changes outside record.MEASUREMENT_PATHS - notebooks, docs, tests, "
            f"issues.md - do not trigger this."
        )


def paper_results_dir(start: Path | None = None) -> tuple[Path, str]:
    """Where recorded numbers belong: the paper repository's ``results/``.

    The notebooks run from the SysSimX checkout because that is the only tree
    that can execute them, while their artifacts belong to the paper. Resolving
    that by walking up for a repository marker finds ``pyproject.toml`` first and
    writes into the framework repo, which is not where the manuscript reads.

    ``SYSSIMX_PAPER_RESULTS`` names the destination explicitly. Unset, this falls
    back to a sibling ``SysSimX-Framework-Paper`` checkout, which is a
    convenience for the usual layout and not a contract: it assumes a fixed
    directory name next to this one. Set the variable in CI and on any machine
    whose checkout is laid out differently.

    Returns:
        The directory, created on demand, and a short string naming how it was
        resolved, for the notebook to print.
    """
    override = os.environ.get("SYSSIMX_PAPER_RESULTS")
    if override:
        directory = Path(override).expanduser().resolve()
        source = "SYSSIMX_PAPER_RESULTS"
    else:
        directory = _repository_root(start).parent / "SysSimX-Framework-Paper" / "results"
        source = "sibling SysSimX-Framework-Paper checkout"
    directory.mkdir(parents=True, exist_ok=True)
    return directory, source


def _git_describe(path: Path) -> str | None:
    """``git describe`` for the repository containing *path*, or ``None``."""
    try:
        completed = subprocess.run(
            ["git", "describe", "--tags", "--always", "--dirty"],
            cwd=str(path),
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    output = completed.stdout.strip()
    return output or None


# Paths whose content decides what a measurement computes. A dirty tree only
# invalidates a campaign result when the dirt is in one of these; editing a
# notebook's prose, `issues.md`, the docs or the tests changes nothing a number
# depends on, and blocking on that made the guard an obstacle rather than a
# check.
#
# The inclusions are deliberate and each is measured, not merely nearby:
#   syssimx/                the framework under measurement
#   syssimx_examples/       the FEM, FMU and OpenSim plants that *are* the models
#   demos/.../src/          the Modelica sources of the monolithic reference
#   demos/.../artifacts/    the exported FMUs the loop actually runs
#   notebooks/evidence/     shared measurement code: plant, loop, instrumentation
#   notebooks/              the instruments themselves, code only - see below
#
# Notebooks were excluded at first, on the argument that their
# measurement-relevant state travels into the provenance block. That argument is
# not airtight: a notebook can also change its own analysis, and the analysis is
# what produces the number. They are included as of 2026-09-12.
#
# Included on their **code only**. A notebook file changes every time it runs,
# because execution counts and outputs are stored in it, so comparing the file
# would make the guard self-defeating: running an instrument would invalidate
# the result it produced. `_notebook_code_changed` compares only the source of
# the code cells against HEAD.
MEASUREMENT_PATHS: tuple[str, ...] = (
    "syssimx/",
    "syssimx_examples/",
    "demos/ControlledPendulum/src/",
    "demos/ControlledPendulum/artifacts/",
    "notebooks/",
)


def _notebook_code(blob: str) -> list[str]:
    """Source of every code cell, ignoring outputs, counts and metadata."""
    try:
        document = json.loads(blob)
    except (json.JSONDecodeError, TypeError):
        return []
    return [
        "".join(cell.get("source", []))
        for cell in document.get("cells", [])
        if cell.get("cell_type") == "code"
    ]


def _notebook_code_changed(repo: Path, path: str) -> bool:
    """Did `path`'s code cells change against HEAD, ignoring stored outputs?

    An untracked notebook, or one git cannot read at HEAD, counts as changed:
    absence of a committed version is exactly the case where a reader cannot
    obtain the instrument.
    """
    try:
        committed = subprocess.run(
            ["git", "show", f"HEAD:{path}"],
            cwd=str(repo), capture_output=True, text=True, timeout=15, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return True
    if committed.returncode != 0:
        return True
    try:
        current = (repo / path).read_text(encoding="utf-8")
    except OSError:
        return True
    return _notebook_code(current) != _notebook_code(committed.stdout)


def _dirty_measurement_paths(repo: Path | None) -> list[str] | None:
    """Repository-relative paths under `MEASUREMENT_PATHS` with uncommitted changes.

    Returns an empty list when the measured surface is clean, and ``None`` when
    the question cannot be answered - no git, no checkout, or an installed wheel
    rather than a source tree. ``None`` is not "clean": it means the artifact
    cannot say, which is itself recorded.
    """
    if repo is None:
        return None
    try:
        completed = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=str(repo),
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None

    dirty: list[str] = []
    for line in completed.stdout.splitlines():
        if len(line) < 4:
            continue
        path = line[3:].strip().strip('"')
        # Renames read "old -> new"; the destination is what exists now.
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        path = path.replace("\\", "/")
        if not any(path.startswith(prefix) for prefix in MEASUREMENT_PATHS):
            continue
        # A notebook counts only when its *code* moved; stored outputs and
        # execution counts change on every run and mean nothing here.
        if path.endswith(".ipynb") and not _notebook_code_changed(repo, path):
            continue
        # Figures are outputs of the instruments, not inputs to them.
        if "/figures/" in path:
            continue
        dirty.append(path)
    return sorted(dirty)


def _framework_provenance() -> dict[str, Any]:
    """Version and source revision of the framework under measurement.

    ``revision`` is present only when SysSimX is imported from a source
    checkout. An installed wheel has no git tree, and that absence is itself
    worth recording: it means the exact revision cannot be recovered from the
    artifact alone.
    """
    info: dict[str, Any] = {}
    try:
        from importlib.metadata import PackageNotFoundError, version

        try:
            info["syssimx_version"] = version("syssimx")
        except PackageNotFoundError:
            info["syssimx_version"] = "not installed"
    except ImportError:  # pragma: no cover - importlib.metadata is stdlib
        info["syssimx_version"] = "unknown"

    try:
        import syssimx

        source = Path(syssimx.__file__).resolve().parent.parent
        info["syssimx_path"] = str(source)
        info["syssimx_revision"] = _git_describe(source)
        info["dirty_measurement_paths"] = _dirty_measurement_paths(source)
    except ImportError:
        info["syssimx_path"] = None
        info["syssimx_revision"] = None
        info["dirty_measurement_paths"] = None
    return info


def provenance(
    *,
    notebook: str | None = None,
    smoke: bool = False,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """The provenance block attached to every recorded payload."""
    block: dict[str, Any] = {
        "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "notebook": notebook,
        "smoke": bool(smoke),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "processor": platform.processor(),
    }
    block.update(_framework_provenance())
    block.update(_threading_provenance())
    if extra:
        block["extra"] = _jsonable(extra)
    return block


def _jsonable(value: Any) -> Any:
    """Coerce NumPy scalars, arrays, and Paths into JSON-serialisable values."""
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (str, bool, int, float)) or value is None:
        return value

    # NumPy and pandas without importing them: both expose tolist/item.
    for attribute in ("tolist", "item"):
        method = getattr(value, attribute, None)
        if callable(method):
            try:
                return _jsonable(method())
            except (TypeError, ValueError):
                continue
    return str(value)


def record(
    figure_id: str,
    payload: dict[str, Any],
    *,
    notebook: str | None = None,
    smoke: bool = False,
    directory: Path | None = None,
    extra_provenance: dict[str, Any] | None = None,
) -> Path:
    """Write ``<figure_id>.json`` and return its path.

    Args:
        figure_id: Register id from ``evidence_plan.md`` section 3, e.g. ``"F1"``.
        payload: The values themselves. Keys carry units in their names.
        notebook: Producing notebook stem, recorded in the provenance block.
        smoke: ``True`` marks a reduced run whose numbers must not be quoted.
        directory: Override the destination; defaults to ``results/``.
        extra_provenance: Run configuration worth keeping beside the values.

    A smoke payload is written to ``<figure_id>.smoke.json`` so it can never be
    mistaken for, or silently overwrite, a campaign result.
    """
    if not figure_id or "/" in figure_id or "\\" in figure_id:
        raise ValueError(f"figure_id must be a plain register id, got {figure_id!r}")

    target_dir = directory or results_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    suffix = ".smoke.json" if smoke else ".json"
    path = target_dir / f"{figure_id}{suffix}"

    prov = provenance(notebook=notebook, smoke=smoke, extra=extra_provenance)
    _assert_quotable(prov, smoke)

    document = {
        "id": figure_id,
        "provenance": prov,
        "values": _jsonable(payload),
    }
    path.write_text(json.dumps(document, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return path
