from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, TYPE_CHECKING

import numpy as np

from .base import Algorithm
from ..graph import collect_global_interface_unknowns
from ...utilities.units import Quantity

if TYPE_CHECKING:
    from ..system import System

#----------------------------------------------------------------------------
# Interface Jacobian-based Co-Simulation Algorithm (IJCSA)
#----------------------------------------------------------------------------
@dataclass
class IJCSAAlgorithm(Algorithm):
    """
    Interface Jacobian-based Co-Simulation Algorithm (IJCSA).
    This algorithm solves all algebraic loops in the system simultaneously
    using a global Newton iteration on the interface variables.

    References:
    - Sicklinger
    """
    name: str = "IJCSA"
    max_iter: int = 50
    tol: float = 1e-6

    #----------------------------------------------------------------------------
    # Global IJCSA Step
    #----------------------------------------------------------------------------
    def step(self, system: "System", t: float, dt: float) -> None:
        solve_global_interface_ijcsa(system, t, max_iter=self.max_iter, tol=self.tol)

        for gen in system.execution_order:
            system._set_inputs_for_generation(gen, t)
            for comp_name in gen:
                comp = system.components[comp_name]
                comp.do_step(t, dt)

#----------------------------------------------------------------------------
# Local IJCSA Step for solving algebraic loops in SCCs
#----------------------------------------------------------------------------
def solve_algebraic_scc_ijcsa(
    system: "System",
    scc: List[str],
    t: float,
    max_iter: int = 50,
    tol: float = 1e-6,
    verbose : bool = False,
) -> None:
    """
    Solve algebraic loop for a strongly coupled SCC using an interface
    Jacobian-based Newton iteration, following Sicklinger et al.

    Unknowns: interface inputs on zero-delay internal connections:
      U = [ (dst_comp, dst_port) ... ]

    Residual for each interface input u_i:
      r_i(U) = u_i - y_i(U)
    where y_i(U) is the output on the driving side of that connection
    evaluated with frozen internal states.
    """
    scc_set = set(scc)
    if verbose: print(60 * "=", f"\nSolving algebraic SCC {scc}:")

    # 1) Collect interface variables
    interface_inputs: List[Tuple[str, str]] = []  # (dst_comp_name, input_port)
    for c in system.connections:
        if c.dst_comp not in scc_set or c.src_comp not in scc_set:
            continue

        dst_comp = system.components[c.dst_comp]
        zero_delay = any(
            c.dst_port in deps
            for deps in dst_comp.direct_feedthrough.values()
            if deps
        )
        if zero_delay:
            interface_inputs.append((c.dst_comp, c.dst_port))

    interface_inputs = sorted(set(interface_inputs))
    if not interface_inputs:
        return  # nothing to solve

    idx_of_input = {key: i for i, key in enumerate(interface_inputs)}
    n = len(interface_inputs)

    # 2) Build internal and external zero-delay edges for SCC
    internal_connections = []  # (src_comp, src_port, dst_comp, dst_port)
    external_in_connections = []  # zero-delay edges from outside into SCC

    for c in system.connections:
        dst_comp = system.components[c.dst_comp]
        zero_delay = any(
            c.dst_port in deps
            for deps in dst_comp.direct_feedthrough.values()
            if deps
        )
        if not zero_delay:
            continue

        if c.src_comp in scc_set and c.dst_comp in scc_set:
            internal_connections.append((c.src_comp, c.src_port, c.dst_comp, c.dst_port))
        elif c.src_comp not in scc_set and c.dst_comp in scc_set:
            external_in_connections.append((c.src_comp, c.src_port, c.dst_comp, c.dst_port))

    # 3) Map each interface input to its single driver (src_comp, src_port)
    driver_for_input: Dict[Tuple[str, str], Tuple[str, str]] = {}
    for src_c, src_p, dst_c, dst_p in internal_connections:
        key = (dst_c, dst_p)
        if key in idx_of_input:
            driver_for_input[key] = (src_c, src_p)

    # Debug info: involved components and interface inputs
    if verbose:
        print("\nConnections:")
        print(f"  Interface inputs: {interface_inputs}")
        print(f"  Internal zero-delay connections: {internal_connections}")
        print(f"  External zero-delay inputs: {external_in_connections}")

    # 4) Initial guess U0 from current input values
    u0 = np.zeros(n, dtype=float)
    for (dst_c, dst_p), i in idx_of_input.items():
        val = system.components[dst_c].inputs[dst_p].get()
        val = val.magnitude if isinstance(val, Quantity) else val
        u0[i] = float(val) if val is not None else 0.0
        if verbose: print(f"\nInitial guess for {dst_c}.{dst_p} = {u0[i]}")

    # 5) Residual Evaluation F(U)
    def compute_interface_residual(u_vec: np.ndarray) -> np.ndarray:
        """
        Given interface input values u_vec, evaluate residual F(U) = U - Y(U).

        Uses comp._evaluate_outputs(in_vals) to keep FMU state unchanged.
        """
        # Build per-component input values
        comp_inputs: Dict[str, Dict[str, Any]] = {name: {} for name in scc}

        # 5.1) External zero-delay drivers into SCC
        for scrc_c, src_p, dst_c, dst_p in external_in_connections:
            val = system.components[scrc_c].outputs[src_p].get()
            val = val.magnitude if isinstance(val, Quantity) else val
            comp_inputs[dst_c][dst_p] = float(val)

        # 5.2) Internal interface inputs (unknowns U)
        for (dst_c, dst_p), i in idx_of_input.items():
            comp_inputs[dst_c][dst_p] = float(u_vec[i])

        # 5.3) Evaluate outputs of all components in SCC (internal and external inputs set)
        computed_out: Dict[Tuple[str, str], float] = {}
        for comp_name in scc:
            comp = system.components[comp_name]
            in_vals = comp_inputs.get(comp_name, {})
            out_vals = comp.evaluate_outputs(in_vals)
            if out_vals is None:
                continue
            for port_name, val in out_vals.items():
                computed_out[(comp_name, port_name)] = float(val)

        # 5.4) Build residuals: F_i = U_i - Y_i(U)
        r = np.zeros(n, dtype=float)
        for i, (dst_c, dst_p) in enumerate(interface_inputs):
            src_c, src_p = driver_for_input[(dst_c, dst_p)]
            y = computed_out.get((src_c, src_p))
            if y is None:
                val = system.components[src_c].outputs[src_p].get()
                val = val.magnitude if isinstance(val, Quantity) else val
                y = float(val) if val is not None else 0.0
            r[i] = u_vec[i] - y
            if verbose: print(f"    Residual for {dst_c}.{dst_p}: {r[i]}")
        return r

    # 6) Interface Jacobian by finite differences
    def compute_interface_jacobian(u_vec: np.ndarray, r_vec: np.ndarray) -> np.ndarray:
        """
        Approximate J = dF/dU by finite differences:
            J[:, j] ≈ ( F(U + eps e_j) - F(U) ) / eps
        """
        J = np.zeros((n, n), dtype=float)
        eps = 1e-6

        for j in range(n):
            u_pert = u_vec.copy()
            u_pert[j] += eps
            r_pert = compute_interface_residual(u_pert)
            J[:, j] = (r_pert - r_vec) / eps

        return J

    # 7) Newton iteration on F(U) = 0
    u_current = u0.copy()

    if verbose: print("\nStarting IJCSA iterations:")
    for k in range(max_iter):
        if verbose: print(f"  Iteration {k}: u = {u_current}")

        # Compute residual
        r_current = compute_interface_residual(u_current)

        # Check convergence
        if np.linalg.norm(r_current) < tol:
            if verbose: print(f"  Converged in {k} iterations.")
            break

        # Compute Jacobian
        J_current = compute_interface_jacobian(u_current, r_current)
        if verbose: print(f"    Jacobian J = {J_current}")

        # Solve for correction: J * Δu = -r
        try:
            delta_u = np.linalg.solve(J_current, -r_current)
        except np.linalg.LinAlgError:
            raise RuntimeError(f"Singular Jacobian in IJCSA for SCC {scc}")

        # Apply correction
        u_current += delta_u
        if verbose: print(f"    Correction Δu = {delta_u}")
    else:
        raise RuntimeError(f"IJCSA did not converge for SCC {scc} after {max_iter} iterations")

    # 8) Commit solved interface inputs to components
    for (dst_c, dst_p), i in idx_of_input.items():
        system.components[dst_c].inputs[dst_p].set(float(u_current[i]), t)
        if verbose: print(f"\nCommitted solved input {dst_c}.{dst_p} = {float(u_current[i])}")

#----------------------------------------------------------------------------
# Helpers for Global IJCSA
#----------------------------------------------------------------------------
def compute_interface_residual_global(
    system: "System",
    U: np.ndarray,
    interface_inputs: List[Tuple[str, str]],
    driver_map: Dict[Tuple[str, str], Tuple[str, str]],
    t: float,
) -> np.ndarray:
    """
    Compute R(U) = U - Y(U) for ALL zero-delay connections in the system
    with frozen component states at time t.

    U: vector of size n, ordered like interface_inputs.
    """
    # Map from input (dst_comp, dst_port) -> scalar value
    input_values: Dict[Tuple[str, str], float] = {}
    for key, val in zip(interface_inputs, U):
        input_values[key] = val

    # 1) Build input dicts per component for this evaluation
    comp_inputs: Dict[str, Dict[str, float]] = {name: {} for name in system.components.keys()}

    # 2) Set all interface inputs from U
    for (dst_c, dst_p), val in input_values.items():
        comp_inputs[dst_c][dst_p] = val

    # 3) Evaluate outputs of all components
    for comp_name, comp in system.components.items():
        inputs = comp_inputs.get(comp_name, {})
        comp.evaluate_outputs(inputs)

    # 4) Build residuals
    R = np.zeros(len(interface_inputs), dtype=float)
    for i, (dst_c, dst_p) in enumerate(interface_inputs):
        src_c, src_p = driver_map[(dst_c, dst_p)]
        y_val = system.components[src_c].outputs[src_p].get()
        y_val = y_val.magnitude if isinstance(y_val, Quantity) else y_val
        y = float(y_val) if y_val is not None else 0.0
        R[i] = U[i] - y

    return R


def compute_interface_jacobian_global(
    system: "System",
    U: np.ndarray,
    interface_inputs: List[Tuple[str, str]],
    driver_map: Dict[Tuple[str, str], Tuple[str, str]],
    t: float,
    eps: float = 1e-6,
) -> np.ndarray:
    """
    Finite-difference Jacobian J ≈ ∂R/∂U for the global interface system.
    """
    n = len(U)
    J = np.zeros((n, n), dtype=float)

    # Base residual
    R0 = compute_interface_residual_global(system, U, interface_inputs, driver_map, t)

    for j in range(n):
        U_pert = U.copy()
        delta = eps * max(1.0, abs(U[j]))
        U_pert[j] += delta

        R_pert = compute_interface_residual_global(system, U_pert, interface_inputs, driver_map, t)
        J[:, j] = (R_pert - R0) / delta

    return J


def solve_global_interface_ijcsa(
    system: "System",
    t: float,
    max_iter: int = 50,
    tol: float = 1e-6,
) -> None:
    """
    Global Interface-Newton (IJCSA) at time t:

    - Unknowns: all zero-delay interface inputs in the system.
    - States are frozen at t (no progression of time).
    - After convergence, component input and output PortStates are consistent.
    """
    interface_inputs, driver_map = collect_global_interface_unknowns(system)
    n = len(interface_inputs)
    if n == 0:
        return  # nothing to solve

    # 1) Build initial guess U0 from current input values
    U0 = np.zeros(n, dtype=float)
    for i, (dst_c, dst_p) in enumerate(interface_inputs):
        val = system.components[dst_c].inputs[dst_p].get()
        val = val.magnitude if isinstance(val, Quantity) else val
        U0[i] = float(val) if val is not None else 0.0

    # 2) Newton iteration on R(U) = 0
    U = U0.copy()

    for _k in range(max_iter):
        R = compute_interface_residual_global(system, U, interface_inputs, driver_map, t)
        norm_R = np.linalg.norm(R, ord=2)

        # Check convergence
        if norm_R < tol:
            break

        J = compute_interface_jacobian_global(system, U, interface_inputs, driver_map, t)

        try:
            delta = np.linalg.solve(J, -R)
        except np.linalg.LinAlgError:
            # Fallback: damped gradient step
            delta = -0.1 * R

        U += delta

    else:
        raise RuntimeError(f"Global IJCSA did not converge after {max_iter} iterations")

    # 3) Write back converged inputs and re-evaluate outputs once
    input_values = {key: float(val) for key, val in zip(interface_inputs, U)}

    # Set inputs per component
    comp_inputs: Dict[str, Dict[str, float]] = {name: {} for name in system.components.keys()}
    for (dst_c, dst_p), val in input_values.items():
        comp_inputs[dst_c][dst_p] = val

    # Apply to components and evaluate outputs
    for comp_name, comp in system.components.items():
        inputs = comp_inputs.get(comp_name, {})
        if inputs:
            comp.set_inputs(inputs, t)
        comp.evaluate_outputs(inputs)
