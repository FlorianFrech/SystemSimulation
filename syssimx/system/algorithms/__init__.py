"""
This module provides implementations of various algorithms used in the system simulation framework.

Classes:
    Algorithm: Base class for all algorithms.
    GaussSeidelAlgorithm: Implementation of the Gauss-Seidel algorithm.
    HybridAlgorithm: Implementation of a hybrid algorithm for system simulation.
    IJCSAAlgorithm: Implementation of the IJCSA algorithm.
    JacobiAlgorithm: Implementation of the Jacobi algorithm.

Functions:
    solve_algebraic_scc_ijcsa: Solves algebraic strongly connected components using the IJCSA algorithm.

This module is part of the `syssimx.system.algorithms` package.
"""

from .base import Algorithm
from .gauss_seidel import GaussSeidelAlgorithm
from .hybrid import HybridAlgorithm
from .ijcsa import IJCSAAlgorithm, solve_algebraic_scc_ijcsa
from .jacobi import JacobiAlgorithm

__all__ = [
    "Algorithm",
    "GaussSeidelAlgorithm",
    "HybridAlgorithm",
    "IJCSAAlgorithm",
    "JacobiAlgorithm",
    "solve_algebraic_scc_ijcsa",
]
