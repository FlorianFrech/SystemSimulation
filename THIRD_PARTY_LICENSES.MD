# Third-Party Licenses and Attributions

This project (`syssimx`) is licensed under MIT (see `LICENSE`).

## Repository content status

- The legacy `examples/` directory has been removed.
- No third-party source files are currently vendored in the repository.
- Third-party obligations therefore primarily come from runtime/build dependencies.

## Dependency licenses (high-level)

The project depends on external libraries with their own licenses. Typical key licenses in use:

- OpenSim: Apache-2.0
- fmpy: BSD-2-Clause
- NGSolve / Netgen: LGPL-2.1
- NumPy / SciPy / pandas / NetworkX / traitlets / ipywidgets / matplotlib: permissive licenses (BSD/PSF-style)

Exact license terms depend on the installed package versions and distribution source.
If you redistribute binaries, containers, or bundled environments, include third-party notices and
license texts required by those dependencies.

## Practical compliance notes

- Keep this file updated when adding/removing dependencies in `pyproject.toml`.
- Do not relicense third-party code: preserve upstream headers/notices if any third-party files are added.
- For downstream redistribution, generate a version-specific dependency notice list from the locked environment.
