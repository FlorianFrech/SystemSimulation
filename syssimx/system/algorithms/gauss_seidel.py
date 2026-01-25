"""Gauss-Seidel execution algorithm for system simulation.

This module provides an implementation of the Gauss-Seidel algorithm, which is used to advance a system simulation by processing components in a specific order. The algorithm ensures that direct-feedthrough components are handled correctly by making their outputs available within the same macro step to downstream components in the current execution order.

Classes:
    GaussSeidelAlgorithm: Implements the Gauss-Seidel algorithm for advancing a system simulation.

Usage:
    The `GaussSeidelAlgorithm` class is designed to be used as part of the system simulation framework. It processes components generation by generation, solving algebraic loops within each generation before stepping components forward.

Dependencies:
    - `Algorithm`: Base class for all algorithms.
    - `solve_algebraic_scc_ijcsa`: Function to solve algebraic strongly connected components.

Example:
    .. code-block:: python

        from syssimx.system.algorithms.gauss_seidel import GaussSeidelAlgorithm

        algorithm = GaussSeidelAlgorithm()
        algorithm.step(system, t, dt)

"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .base import Algorithm
from .ijcsa import solve_algebraic_scc_ijcsa

if TYPE_CHECKING:
    from ..system import System


# ----------------------------------------------------------------------------
# Gauss-Seidel Algorithm
# ----------------------------------------------------------------------------
@dataclass
class GaussSeidelAlgorithm(Algorithm):
    """Advance the system using Gauss-Seidel-style ordering.

    Components are processed generation by generation, with algebraic loops
    solved inside each generation before stepping components forward.

    This approach accounts for direct-feedthrough components by making their
    outputs available within the same macro step to downstream components in
    the current execution order.
    """

    name: str = "Gauss-Seidel"

    def step(self, system: System, t: float, dt: float) -> None:
        """Advance the system by one time step using Gauss-Seidel ordering.

        Args:
            system: System to advance.
            t: Current simulation time.
            dt: Step size.
        """
        for gen in system.execution_order:
            system._set_inputs_for_generation(gen, t)
            gen_set = set(gen)
            for loop in system.algebraic_loops:
                if set(loop).issubset(gen_set):
                    solve_algebraic_scc_ijcsa(system, loop, t)
            for comp_name in gen:
                comp = system.components[comp_name]
                comp.do_step(t, dt)
