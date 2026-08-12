"""Jacobi-based execution algorithm for system simulation.

The algorithm freezes every component input before advancing component state,
so all components use outputs available at the start of the macro step rather
than outputs produced during that same step. The component advances are
mathematically independent after that exchange, but the current implementation
invokes them serially.

Classes:
    JacobiAlgorithm: Implements the Jacobi algorithm for advancing a system simulation.

Usage:
    ``JacobiAlgorithm`` provides lagged-input coupling. It does not propagate
    direct-feedthrough outputs to downstream components within the same macro
    step.

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

    All component advances are currently invoked serially. Jacobi semantics
    make those advances candidates for future parallel execution; they do not
    imply that this implementation executes concurrently.

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
