#!/usr/bin/env python3
"""Bump syssimx package version in syssimx/__version__.py.

Usage:
    python scripts/bump_version.py patch
    python scripts/bump_version.py minor
    python scripts/bump_version.py major
    python scripts/bump_version.py patch --dry-run
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

VERSION_FILE = Path("syssimx/__version__.py")
VERSION_PATTERN = re.compile(r'__version__\s*=\s*"(\d+)\.(\d+)\.(\d+)"')


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bump syssimx version.")
    parser.add_argument(
        "part",
        choices=("major", "minor", "patch"),
        help="Version part to bump.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show proposed change without writing files.",
    )
    return parser.parse_args()


def bump_version(major: int, minor: int, patch: int, part: str) -> tuple[int, int, int]:
    if part == "major":
        return major + 1, 0, 0
    if part == "minor":
        return major, minor + 1, 0
    return major, minor, patch + 1


def main() -> int:
    args = parse_args()

    if not VERSION_FILE.exists():
        raise FileNotFoundError(f"Version file not found: {VERSION_FILE}")

    text = VERSION_FILE.read_text(encoding="utf-8")
    match = VERSION_PATTERN.search(text)
    if not match:
        raise ValueError(f"Could not find __version__ in {VERSION_FILE}")

    current = tuple(int(p) for p in match.groups())
    new = bump_version(*current, args.part)

    old_str = ".".join(str(p) for p in current)
    new_str = ".".join(str(p) for p in new)

    print(f"Current version: {old_str}")
    print(f"New version:     {new_str}")

    if args.dry_run:
        print("Dry run only: no files changed.")
        return 0

    updated = VERSION_PATTERN.sub(f'__version__ = "{new_str}"', text, count=1)
    VERSION_FILE.write_text(updated, encoding="utf-8")
    print(f"Updated {VERSION_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
