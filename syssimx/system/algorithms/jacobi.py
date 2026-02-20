"""Jacobi-based execution algorithm for system simulation.

This module provides an implementation of the Jacobi algorithm, which is used to advance a system simulation by processing components in a parallelized order. The algorithm sets all inputs for a generation before advancing any component in that generation, solving algebraic loops within the generation, and then advancing the component states.

Classes:
    JacobiAlgorithm: Implements the Jacobi algorithm for advancing a system simulation.

Usage:
    The `JacobiAlgorithm` class is designed to be used as part of the system simulation framework. It processes components in a parallelized manner, which does not handle direct-feedthrough components whose outputs could become available within the same macro step to downstream components.

Dependencies:
    - `Algorithm`: Base class for all algorithms.
    - `solve_algebraic_scc_ijcsa`: Function to solve algebraic strongly connected components.

Example:
    .. code-block:: python

        from syssimx.system.algorithms.jacobi import JacobiAlgorithm

        algorithm = JacobiAlgorithm()
        algorithm.step(system, t, dt)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .base import Algorithm
from .ijcsa import solve_algebraic_scc_ijcsa

if TYPE_CHECKING:
    from ..system import System


@dataclass
class JacobiAlgorithm(Algorithm):
    """Advance the system using a Jacobi-style execution order.

    The algorithm sets all inputs for a generation before any component in that
    generation advances, then solves any algebraic loops contained in that
    generation, and finally advances component state.

    This approach does not handle direct-feedthrough components whose outputs
    could become available within the same macro step to downstream components.
    """

    name: str = "Jacobi"

    def step(self, system: System, t: float, dt: float) -> None:
        """Advance the system by one time step using Jacobi ordering.

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

        for gen in system.execution_order:
            for comp_name in gen:
                comp = system.components[comp_name]
                comp.do_step(t, dt)
