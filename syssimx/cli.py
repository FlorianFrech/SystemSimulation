"""Command-line interface for SysSimX.

Provides the ``syssimx`` console script::

    syssimx run system.yaml                    # run with the file's run settings
    syssimx run system.yaml --tf 10 --dt 0.01  # override run settings
    syssimx run system.yaml -o results.csv     # export results (long format)
    syssimx describe system.yaml               # print the structural report
"""

from __future__ import annotations

import argparse
import os
import sys

from .system.loader import ConfigError, build_system, load_config, run_from_config


def _add_run_overrides(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("config", help="Path to a YAML/JSON system description")
    parser.add_argument("--t0", type=float, default=None, help="Override start time [s]")
    parser.add_argument("--tf", type=float, default=None, help="Override end time [s]")
    parser.add_argument("--dt", type=float, default=None, help="Override macro step size [s]")


def main(argv: list[str] | None = None) -> int:
    """Entry point for the ``syssimx`` console script."""
    parser = argparse.ArgumentParser(
        prog="syssimx",
        description="Run and inspect SysSimX co-simulation systems from declarative descriptions.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Assemble, initialize, and run a system")
    _add_run_overrides(run_parser)
    run_parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Write results to this CSV file (tidy long format)",
    )
    run_parser.add_argument(
        "--quiet", action="store_true", help="Suppress the progress line"
    )

    describe_parser = subparsers.add_parser(
        "describe", help="Print the structural report of a system description"
    )
    describe_parser.add_argument("config", help="Path to a YAML/JSON system description")
    describe_parser.add_argument(
        "--initialize",
        action="store_true",
        help="Initialize the system first so the execution order is included",
    )

    args = parser.parse_args(argv)

    # Make component modules that live relative to the invocation directory
    # (or next to the description file) importable by their module path.
    for extra in (os.getcwd(), str(os.path.dirname(os.path.abspath(args.config)))):
        if extra not in sys.path:
            sys.path.insert(0, extra)

    try:
        if args.command == "run":
            return _cmd_run(args)
        if args.command == "describe":
            return _cmd_describe(args)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    progress = None
    if not args.quiet:

        def progress(t: float, tf: float) -> None:
            print(f"\r  t = {t:.6g} / {tf:.6g} s", end="", file=sys.stderr)

    result = run_from_config(
        args.config, t0=args.t0, tf=args.tf, dt=args.dt, progress=progress
    )
    if not args.quiet:
        print(file=sys.stderr)

    print(
        f"Completed '{result.system_name}': t in [{result.t0}, {result.tf}] s, "
        f"dt = {result.dt} s, algorithm = {result.algorithm}, "
        f"wall time = {result.wall_time:.3f} s"
    )
    if args.output:
        path = result.to_csv(args.output)
        print(f"Results written to {path}")
    return 0


def _cmd_describe(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    system = build_system(config)
    if args.initialize:
        run_cfg = config.get("run", {}) or {}
        system.initialize(t0=float(run_cfg.get("t0", 0.0)))
    print(system.describe())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
