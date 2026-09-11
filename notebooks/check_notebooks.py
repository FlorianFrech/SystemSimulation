"""Static check: does any notebook cell read a name nothing ever binds?

Cheap pre-run gate for the evidence notebooks. The failure it exists to catch is
splitting or rewriting a cell and orphaning a name that a *later* cell consumes -
which surfaces only when the run reaches that cell, up to an hour in.

Scope matters here. An earlier version of this check collected every ``Store``
in a cell, including assignments inside function bodies, and so believed a
function-local name was available at module level. That let
``03_switching``'s record cell reference a `transfers` that only existed inside
``run_once``, and the check passed. Names bound inside a ``def``/``lambda``/
comprehension are now confined to that scope.

Run it from ``notebooks/``::

    python check_notebooks.py            # all evidence notebooks
    python check_notebooks.py 03_switching.ipynb
"""

from __future__ import annotations

import ast
import builtins
import json
import sys
from pathlib import Path

NOTEBOOKS = (
    "01_mechanism.ipynb",
    "02_baseline.ipynb",
    "03_switching.ipynb",
    "04_performance.ipynb",
    "05_placement.ipynb",
)

# Names the kernel provides that are not builtins.
KERNEL_GLOBALS = {"display", "get_ipython", "In", "Out", "_", "__", "___"}


class _ModuleScope(ast.NodeVisitor):
    """Collect module-level bindings and module-level loads, ignoring nested scopes."""

    def __init__(self) -> None:
        self.bound: set[str] = set()
        self.loaded: set[str] = set()

    # --- bindings that are module level even though they introduce a scope ---
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.bound.add(node.name)
        self._visit_decorators_and_defaults(node)

    visit_AsyncFunctionDef = visit_FunctionDef  # type: ignore[assignment]

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.bound.add(node.name)
        for child in [*node.bases, *node.keywords, *node.decorator_list]:
            self.visit(child)
        # A class body executes in its own namespace, but its loads resolve
        # outward, so they still have to be satisfied.
        for stmt in node.body:
            self.visit(stmt)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        self._visit_decorators_and_defaults(node)

    def _visit_decorators_and_defaults(self, node) -> None:
        """A nested scope's body is out of scope; its defaults and decorators are not."""
        for child in getattr(node, "decorator_list", []):
            self.visit(child)
        args = node.args
        for default in [*args.defaults, *(d for d in args.kw_defaults if d)]:
            self.visit(default)

    # --- comprehensions bind their targets only inside themselves ------------
    def _visit_comprehension(self, node) -> None:
        for i, generator in enumerate(node.generators):
            if i == 0:
                self.visit(generator.iter)  # the outermost iterable is evaluated here

    visit_ListComp = _visit_comprehension  # type: ignore[assignment]
    visit_SetComp = _visit_comprehension  # type: ignore[assignment]
    visit_GeneratorExp = _visit_comprehension  # type: ignore[assignment]
    visit_DictComp = _visit_comprehension  # type: ignore[assignment]

    # --- ordinary bindings and loads ----------------------------------------
    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Store):
            self.bound.add(node.id)
        elif isinstance(node.ctx, ast.Load):
            self.loaded.add(node.id)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.bound.add((alias.asname or alias.name).split(".")[0])

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            self.bound.add(alias.asname or alias.name)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.name:
            self.bound.add(node.name)
        self.generic_visit(node)

    def visit_Global(self, node: ast.Global) -> None:
        self.bound.update(node.names)


def check(path: Path) -> list[tuple[int, str]]:
    """Return `(cell index, name)` for every module-level load nothing binds."""
    notebook = json.loads(path.read_text(encoding="utf-8"))
    defined = set(dir(builtins)) | KERNEL_GLOBALS
    problems: list[tuple[int, str]] = []

    for index, cell in enumerate(c for c in notebook["cells"] if c["cell_type"] == "code"):
        source = "".join(cell["source"])
        try:
            tree = ast.parse(source)
        except SyntaxError as error:
            problems.append((index, f"SyntaxError: {error.msg} (line {error.lineno})"))
            continue
        scope = _ModuleScope()
        for statement in tree.body:
            scope.visit(statement)
        # A cell may use what it binds, in any order; cells run top to bottom.
        defined |= scope.bound
        problems.extend((index, name) for name in sorted(scope.loaded - defined))

    return problems


def main(argv: list[str]) -> int:
    targets = [Path(name) for name in argv[1:]] or [Path(n) for n in NOTEBOOKS]
    failed = False
    for path in targets:
        if not path.exists():
            print(f"{path.name:24s} MISSING")
            failed = True
            continue
        problems = check(path)
        if problems:
            failed = True
            print(f"{path.name:24s} {len(problems)} unbound")
            for index, name in problems:
                print(f"    code cell {index}: {name}")
        else:
            print(f"{path.name:24s} OK")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
