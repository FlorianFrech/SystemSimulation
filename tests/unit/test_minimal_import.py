"""Checks for the dependency boundary of the basic installation."""

from __future__ import annotations

import subprocess
import sys


def test_top_level_import_does_not_eagerly_import_optional_features():
    code = """
import sys
import syssimx

optional = {
    "pandas",
    "yaml",
    "graphviz",
    "IPython",
    "matplotlib",
    "ipywidgets",
    "traitlets",
}
loaded = sorted(optional.intersection(sys.modules))
if loaded:
    raise SystemExit(f"optional modules imported eagerly: {loaded}")
"""
    completed = subprocess.run(
        [sys.executable, "-c", code],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
