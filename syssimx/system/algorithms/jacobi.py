"""Jacobi-based execution algorithm for System simulation."""

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
