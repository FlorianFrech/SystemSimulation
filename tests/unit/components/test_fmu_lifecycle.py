"""Release policy and extraction cache for FMU archives.

Covers issues.md HARD-05 step 1 and HARD-07 step 1. Neither needs a platform
binary: the policy is derived from the archive's metadata, and the cache is
exercised against a stubbed extractor, so both run in the fast job on every
platform.
"""

import json
import zipfile
from types import SimpleNamespace

import pytest

fmpy = pytest.importorskip("fmpy")

from syssimx.components import fmu as fmu_module  # noqa: E402
from syssimx.components.fmu import (  # noqa: E402
    FMUReleasePolicy,
    _read_solver_flag,
    clear_extraction_cache,
    extract_cached,
    resolve_release_policy,
)


def _archive(tmp_path, name="Model", solver="cvode", with_flags=True):
    """Build a minimal .fmu carrying only the solver flags an export records."""
    path = tmp_path / f"{name}.fmu"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("modelDescription.xml", "<fmiModelDescription/>")
        if with_flags:
            archive.writestr(f"resources/{name}_flags.json", json.dumps({"s": solver}))
    return path


def _description(continuous_states):
    return SimpleNamespace(numberOfContinuousStates=continuous_states)


# ============================================================================
# Release policy (HARD-05 step 1)
# ============================================================================
class TestReleasePolicy:
    """The predicate is: OpenModelica CVODE plus at least one continuous state."""

    @pytest.mark.parametrize(
        ("solver", "states", "releasable"),
        [
            ("cvode", 2, False),  # allocates a solver; teardown corrupts the heap
            ("cvode", 1, False),  # one state is enough
            ("cvode", 0, True),  # no solver is ever allocated
            ("euler", 2, True),  # not the defective teardown path
            ("euler", 0, True),
        ],
    )
    def test_predicate(self, tmp_path, solver, states, releasable):
        path = _archive(tmp_path, solver=solver)
        policy = resolve_release_policy(str(path), _description(states))

        assert policy.releasable is releasable
        assert policy.solver == solver
        assert policy.continuous_states == states
        assert policy.reason

    def test_archive_without_flags_is_releasable(self, tmp_path):
        """A non-OpenModelica export is not subject to this defect."""
        path = _archive(tmp_path, with_flags=False)
        policy = resolve_release_policy(str(path), _description(4))

        assert policy.releasable is True
        assert policy.solver is None

    def test_unreadable_archive_does_not_raise(self, tmp_path):
        """A corrupt archive yields no flag rather than propagating."""
        path = tmp_path / "broken.fmu"
        path.write_bytes(b"not a zip")

        assert _read_solver_flag(str(path)) is None
        assert resolve_release_policy(str(path), _description(2)).releasable is True

    def test_missing_state_count_is_treated_as_zero(self, tmp_path):
        """A description without the attribute must not crash the predicate."""
        path = _archive(tmp_path, solver="cvode")
        policy = resolve_release_policy(str(path), SimpleNamespace())

        assert policy.continuous_states == 0
        assert policy.releasable is True

    def test_policy_is_immutable(self, tmp_path):
        policy = resolve_release_policy(str(_archive(tmp_path)), _description(0))
        assert isinstance(policy, FMUReleasePolicy)
        with pytest.raises(AttributeError):
            policy.releasable = True  # type: ignore[misc]


# ============================================================================
# Extraction cache (HARD-07 step 1)
# ============================================================================
class TestExtractionCache:
    """Extraction depends only on the file, so it is done once per file."""

    @pytest.fixture(autouse=True)
    def _isolate_cache(self):
        fmu_module._EXTRACTION_CACHE.clear()
        yield
        fmu_module._EXTRACTION_CACHE.clear()

    @pytest.fixture
    def counting_extract(self, tmp_path, monkeypatch):
        calls = []

        def fake_extract(path):
            target = tmp_path / f"unzip_{len(calls)}"
            target.mkdir()
            calls.append(str(path))
            return str(target)

        monkeypatch.setattr(fmu_module, "extract", fake_extract)
        return calls

    def test_repeated_extraction_reuses_one_directory(self, tmp_path, counting_extract):
        path = str(_archive(tmp_path))

        first = extract_cached(path)
        assert [extract_cached(path) for _ in range(4)] == [first] * 4
        assert len(counting_extract) == 1, "the archive was unpacked more than once"

    def test_distinct_archives_get_distinct_directories(self, tmp_path, counting_extract):
        a = str(_archive(tmp_path, name="A"))
        b = str(_archive(tmp_path, name="B"))

        assert extract_cached(a) != extract_cached(b)
        assert len(counting_extract) == 2

    def test_rebuilt_archive_is_extracted_again(self, tmp_path, counting_extract):
        """Identity is path plus size plus mtime, so a rebuild invalidates."""
        path = _archive(tmp_path, name="Model")
        first = extract_cached(str(path))

        path.unlink()
        rebuilt = _archive(tmp_path, name="Model", solver="euler")
        # Force a distinct mtime even on a coarse-resolution filesystem.
        import os

        stat = rebuilt.stat()
        os.utime(rebuilt, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000_000))

        assert extract_cached(str(rebuilt)) != first
        assert len(counting_extract) == 2

    def test_vanished_directory_is_re_extracted(self, tmp_path, counting_extract):
        """A cached directory removed underneath us must not be handed out."""
        import shutil

        path = str(_archive(tmp_path))
        first = extract_cached(path)
        shutil.rmtree(first)

        assert extract_cached(path) != first
        assert len(counting_extract) == 2

    def test_clear_empties_the_cache(self, tmp_path, counting_extract):
        from pathlib import Path

        path = str(_archive(tmp_path))
        unzipdir = extract_cached(path)
        assert Path(unzipdir).is_dir()

        clear_extraction_cache()

        assert fmu_module._EXTRACTION_CACHE == {}
        assert not Path(unzipdir).exists()
