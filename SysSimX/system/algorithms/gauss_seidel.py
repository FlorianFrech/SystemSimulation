from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .base import Algorithm
from .ijcsa import solve_algebraic_scc_ijcsa

if TYPE_CHECKING:
    from ..system import System

#----------------------------------------------------------------------------
# Gauss-Seidel Algorithm
#----------------------------------------------------------------------------
@dataclass
class GaussSeidelAlgorithm(Algorithm):
    """
    Gauss-Seidel algorithm for solving systems with algebraic loops.

    This algorithm processes components in their execution order, solving any
    algebraic loops within each generation before stepping the components forward
    in time. Algebraic loops are identified and solved using
    the IJCSA (Interface Jacobian-base Co-Simulation Algorithm) method.

    The algorithm:
    1. Iterates through each generation in the system's execution order
    2. Sets up inputs for the current generation at time t
    3. Identifies and solves any algebraic loops that are fully contained within
        the current generation
    4. Executes the time step for each component in the generation

    This approach allows for efficient handling of systems with feedback loops
    while maintaining numerical stability through the Gauss-Seidel iteration pattern.
    """
    name: str = "Gauss-Seidel"

    def step(self, system: "System", t: float, dt: float) -> None:
        for gen in system.execution_order:
            system._set_inputs_for_generation(gen, t)
            gen_set = set(gen)
            for loop in system.algebraic_loops:
                if set(loop).issubset(gen_set):
                    solve_algebraic_scc_ijcsa(system, loop, t)
            for comp_name in gen:
                comp = system.components[comp_name]
                comp.do_step(t, dt)
