from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .base import Algorithm
from .ijcsa import solve_algebraic_scc_ijcsa

if TYPE_CHECKING:
    from ..system import System


@dataclass
class JacobiAlgorithm(Algorithm):
    """
    Execute one simulation step using the Jacobi algorithm.

    The Jacobi algorithm processes the system in two phases:
    1. Input setting phase: For each generation in the execution order, set inputs
        and solve any algebraic loops that are completely contained within that generation.
    2. Step execution phase: Execute the do_step method for all components in order.

    Note:
        This algorithm uses the Jacobi method where all components read their inputs
        based on the previous time step's outputs before updating their own states.
        Algebraic loops within each generation are solved using the IJCSA method.
    """
    name: str = "Jacobi"

    def step(self, system: "System", t: float, dt: float) -> None:
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
