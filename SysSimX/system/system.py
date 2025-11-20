from __future__ import annotations
from collections import defaultdict
from typing import Dict, List, Any, Tuple

import networkx as nx
import numpy as np

from .connection import Connection
from ..core.base import CoSimComponent
from ..core.port import PortSpec
from ..core.history import SystemHistory
from ..utilities.units import Quantity

_ports_compatible = PortSpec.compatible

#----------------------------------------------------------------------------
# System Class
#----------------------------------------------------------------------------
class System:
    """
    Represents a system of interconnected CoSimComponents:
     - Manages components and their connections
     - Validates connections
     - Builds a zero-delay directed acyclic graph (DAG) to compute parallelizable execution order
     - Runs two-phase simulation steps (set inputs -> do step)
    """
    
    def __init__(self, name: str):
        self.name = name
        self.components: Dict[str, CoSimComponent] = {}
        self.connections: List[Connection] = []
        self.graph = nx.MultiDiGraph()  # All connections (including delayed)
        self._dag = nx.DiGraph()        # Zero-delay connections only
        
        self.groups: Dict[str, List[CoSimComponent]] = {}
        self.execution_order: List[List[str]] = []  # [ [comp names in gen0], [gen1], ...]
        self.execution_idx: Dict[str, int] = {}     # comp name -> gen index

        # Algebraic loop diagnostics (SCCs with size > 1 on the direct feed-through graph)
        self.algebraic_loops: List[List[str]] = []  # Detected algebraic loops (if any)
        self._scc_index: Dict[str, int] = {}        # comp name -> scc index
        
        # Pre-computed connection lookups
        self._incoming_by_dst: Dict[str, List[Connection]] = {}

        # Algorithm
        self.algorithm: str = "Gauss-Seidel"  # or "Jacobi" or "IJCSA"

        # History Management
        self.history = SystemHistory(system_name=name)
    
    #----------------------------------------------------------------------------
    # Register components
    #----------------------------------------------------------------------------
    def add_component(self, component: CoSimComponent):
        """
        Add a CoSimComponent to the system.
        """
        if component.name in self.components:
            raise ValueError(f"Component '{component.name}' already in system.")
        self.components[component.name] = component
        
        # Register component history
        self.history.add_component(component.name, component.history)
        
        if component.group:
            self.groups.setdefault(component.group, []).append(component)
    
    #----------------------------------------------------------------------------
    # Connections
    #----------------------------------------------------------------------------
    def _validate_connection(self, c: Connection) -> None:
        # 1) existence
        if c.src_comp not in self.components or c.dst_comp not in self.components:
            raise ValueError(f"Both '{c.src_comp}' and '{c.dst_comp}' must be added to the system before connecting them.")
        
        src = self.components[c.src_comp]
        dst = self.components[c.dst_comp]

        # 2) port existence
        if c.src_port not in src.output_specs:
            raise KeyError(f"Source port '{c.src_port}' is not an OUTPUT port of component '{src.name}'.")
        if c.dst_port not in dst.input_specs:
            raise KeyError(f"Destination port '{c.dst_port}' is not an INPUT port of component '{dst.name}'.")
        
        src_ps: PortSpec = src.output_specs[c.src_port]
        dst_ps: PortSpec = dst.input_specs[c.dst_port]

        # 3) type and unit compatibility
        if not _ports_compatible(src_ps, dst_ps):
            src_unit = src_ps.unit if src_ps.unit else "unitless"
            dst_unit = dst_ps.unit if dst_ps.unit else "unitless"
            raise TypeError(
                f"Port incompatibility: {c.src_comp}.{c.src_port} ({src_ps.type}, {src_unit}) "
                f"-> {c.dst_comp}.{c.dst_port} ({dst_ps.type}, {dst_unit})"
            )

        # 5) duplicate check
        for existing in self.connections:
            if (existing.src_comp == c.src_comp and existing.src_port == c.src_port and
                existing.dst_comp == c.dst_comp and existing.dst_port == c.dst_port):
                raise ValueError(
                    f"Duplicate connection: {c.src_comp}.{c.src_port} -> {c.dst_comp}.{c.dst_port}"
                )

    def add_connection(self, connection: Connection) -> None:
        """
        Add a Connection between two components in the system.
        """
        self._validate_connection(connection)
        self.connections.append(connection)
        self._incoming_by_dst.clear()

    #----------------------------------------------------------------------------
    # Graphs
    #----------------------------------------------------------------------------
    def build_graphs(self) -> None:
        """
        Build:
          - self.graph: all connections (annotated)
          - self._dag: zero-delay true-direct-feedthrough dependencies only
          - self.algebraic_loops: SCCs (>1) on self._dag
        """
        self.graph.clear()
        self._dag.clear()
        self.algebraic_loops.clear()
        self._scc_index.clear()
        self._incoming_by_dst.clear()
        
        # nodes
        for name in self.components:
            self.graph.add_node(name)
            self._dag.add_node(name)

        for c in self.connections:
            self._incoming_by_dst.setdefault(c.dst_comp, []).append(c)
            self.graph.add_edge(
                c.src_comp, c.dst_comp,
                src_port=c.src_port, dst_port=c.dst_port,
                unit=c.unit or None
            )

            dst_comp = self.components[c.dst_comp]
            zero_delay = False
            relevant_outputs = self._compute_used_outputs().get(c.dst_comp, set())
            for out_port, deps in dst_comp.direct_feedthrough.items():
                if out_port not in relevant_outputs:
                    continue
                if deps and c.dst_port in deps:
                    zero_delay = True
                    break
            if zero_delay:
                self._dag.add_edge(
                    c.src_comp, c.dst_comp,
                    src_port=c.src_port, dst_port=c.dst_port
                )

        # Identify algebraic loops (SCCs with size > 1)
        sccs = list(nx.strongly_connected_components(self._dag))
        self.algebraic_loops = [list(scc) for scc in sccs if len(scc) > 1]

        # Identify single-node SCCs with self-loops as well
        for node in self._dag.nodes:
            if self._dag.has_edge(node, node) and node not in self.algebraic_loops:
                self.algebraic_loops.append([node])

    def compute_execution_order(self) -> None:
        """
        Compute a parallelizable execution order based on zero-delay dependencies.
        """
        if self._dag.number_of_nodes() == 0:
            self.build_graphs()

        # Condensation: nodes are SCC ids (0..k-1), edges reflect inter-SCC dependencies
        condensed = nx.condensation(self._dag)
        mapping: Dict[str, int] = condensed.graph.get("mapping", {})  # original node -> scc id
        
        # Reverse mapping: scc id -> list of original component names
        scc_members: Dict[int, List[str]] = {}
        for comp_name, scc_id in mapping.items():
            scc_members.setdefault(scc_id, []).append(comp_name)
        for cid in scc_members:
            scc_members[cid] = sorted(scc_members[cid])

        self._scc_index = {name: mapping[name] for name in self.components.keys() if name in mapping}

        gens_c = list(nx.topological_generations(condensed))

        self.execution_order = []
        self.execution_idx.clear()

        idx = 0
        for gen in gens_c:
            expanded: List[str] = []
            for cid in gen:
                members = scc_members.get(cid, [])
                expanded.extend(members)
            expanded = sorted(expanded)
            self.execution_order.append(expanded)
            for name in expanded:
                self.execution_idx[name] = idx
            idx += 1

        self._move_delayed_producers_to_last_generation()
    
    #----------------------------------------------------------------------------
    # Simulation Lifecycle
    #----------------------------------------------------------------------------
    def initialize(self, t0: float, t_end: float) -> None:
        """
        Initialize all components in the system at start time t0.
        Also build graphs and compute execution order.
        Store t_end for reference.
        """
        self.time = t0
        self.t_end = t_end
        for comp in self.components.values():
            comp.initialize(t0)
        self.build_graphs()
        self.compute_execution_order()
    
    def _set_inputs_for_generation(self, gen: List[str], t: float) -> None:
        """
        For each component in the generation, set its INPUT by scanning connections whose
        dst_comp is the component. For delay > 0, use history; for delay == 0, use current value.
        """        
        for comp_name in gen:
            comp = self.components[comp_name]
            to_set: Dict[str, Any] = {}

            for c in self._incoming_by_dst.get(comp_name, []):
                # Detect multiple drivers for the same input port
                if c.dst_port in to_set:
                    raise RuntimeError(
                        f"Multiple drivers for input port '{comp_name}.{c.dst_port}' "
                        f"from '{to_set[c.dst_port]}' and '{c.src_comp}.{c.src_port}'"
                    )
                # Get source value
                src_value = self.components[c.src_comp].outputs[c.src_port].get()
                if src_value is not None:
                    to_set[c.dst_port] = src_value
            
            if to_set:
                comp.set_inputs(to_set, t=t)

    #----------------------------------------------------------------------------
    # Gauss-Seidel Co-Simulation Step
    #----------------------------------------------------------------------------
    def step_gs(self, t: float, dt: float) -> None:
        """
        Sequential GS-like step:
        - Use zero-delay DAG to respect algebraic dependencies.
        - Within each generation, process components in order, 
            always feeding them the latest outputs available.
        """    
        for gen in self.execution_order:
            self._set_inputs_for_generation(gen, t)
            gen_set = set(gen)
            for loop in self.algebraic_loops:
                if set(loop).issubset(gen_set):
                    self._solve_algebraic_scc_ijcsa(loop, t)
            for comp_name in gen:
                comp = self.components[comp_name]
                comp.do_step(t, dt)
        
    #----------------------------------------------------------------------------
    # Jacobi Co-Simulation Step
    #----------------------------------------------------------------------------
    def step_jacobi(self, t: float, dt: float) -> None:
        """
        Perform a simulation step:
         1) For each generation in execution order, set inputs for all components in the generation
         2) For each generation, call do_step on all components in the generation
        """
        for gen in self.execution_order:
            self._set_inputs_for_generation(gen, t)

            gen_set = set(gen)
            for loop in self.algebraic_loops:
                if set(loop).issubset(gen_set):
                    self._solve_algebraic_scc_ijcsa(loop, t)

        for gen in self.execution_order:
            for comp_name in gen:
                comp = self.components[comp_name]
                comp.do_step(t, dt)

    #----------------------------------------------------------------------------
    # Global Interface Jacobian-based Co-Simulation Step
    #----------------------------------------------------------------------------
    def step_ijcsa_global(self, t: float, dt: float) -> None:
        """
        Perform one global co-simulation step using IJCSA:

        1) Global interface-Newton at t with dt=0 to get consistent interface values.
        2) Single explicit integration step t -> t+dt using those interface values.
        """
        # 1) Global IJCSA on all zero-delay connections
        self._solve_global_interface_ijcsa(t)

        # 2) Actual time step for all components
        for gen in self.execution_order:
            self._set_inputs_for_generation(gen, t)

            for comp_name in gen:
                comp = self.components[comp_name]
                comp.do_step(t, dt)

    #----------------------------------------------------------------------------
    # Run System Simulation
    #----------------------------------------------------------------------------
    def run(self, t0: float, tf: float, dt: float):
        """
        Run the simulation from t0 to tf with step size dt.
        """
        #self.initialize(t0)
        t = t0
        self.t_end = tf
        if self.algorithm == "Gauss-Seidel":
            step_func = self.step_gs
        elif self.algorithm == "Jacobi":
            step_func = self.step_jacobi
        elif self.algorithm == "IJCSA":
            step_func = self.step_ijcsa_global
        while t < tf - 1e-12:
            step_func(t, dt)
            t += dt
    
    #----------------------------------------------------------------------------
    # Get history of all components
    #----------------------------------------------------------------------------
    def get_history(self) -> Dict[str, Dict[str, List[Any]]]:
        """
        Retrieve the history of all components in the system.

        Returns:
            A dictionary mapping component names to their history dictionaries.
        """
        history: Dict[str, Dict[str, List[Any]]] = {}
        for comp_name, comp in self.components.items():
            history[comp_name] = comp.get_history_arrays()
        return history

    #----------------------------------------------------------------------------
    # Interface Jacobian-based Co-Simulation Algorithm (IJCSA)
    #----------------------------------------------------------------------------
    def _solve_algebraic_scc_ijcsa(self, scc: List[str], t: float) -> None:
        """
        Solve algebraic loop for a strongly coupled SCC using an interface
        Jacobian-based Newton iteration, following Sicklinger et al.

        Unknowns: interface inputs on zero-delay internal connections:
          U = [ (dst_comp, dst_port) ... ]

        Residual for each interface input u_i:
          r_i(U) = u_i - y_i(U)
        where y_i(U) is the *output* on the driving side of that connection
        evaluated with frozen internal states.
        """
        scc_set = set(scc)
        
        # 1) Collect interface variables
        interface_inputs: List[Tuple[str, str]] = []   # (dst_comp_name, input_port)
        for c in self.connections:
            if c.dst_comp not in scc_set or c.src_comp not in scc_set:
                continue

            dst_comp = self.components[c.dst_comp]
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
        internal_connections = []     # (src_comp, src_port, dst_comp, dst_port)
        external_in_connections = []  # zero-delay edges from outside into SCC

        for c in self.connections:
            dst_comp = self.components[c.dst_comp]
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
        
        # 4) Initial guess U0 from current input values
        u0 = np.zeros(n, dtype=float)
        for (dst_c, dst_p), i in idx_of_input.items():
            val = self.components[dst_c].inputs[dst_p].get()
            val = val.magnitude if isinstance(val, Quantity) else val
            u0[i] = float(val) if val is not None else 0.0

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
                val = self.components[scrc_c].outputs[src_p].get()
                val = val.magnitude if isinstance(val, Quantity) else val
                comp_inputs[dst_c][dst_p] = float(val)

            # 5.2) Internal interface inputs (unknowns U)
            for (dst_c, dst_p), i in idx_of_input.items():
                comp_inputs[dst_c][dst_p] = float(u_vec[i])
            
            # 5.3) Evaluate outputs of all components in SCC
            computed_out: Dict[Tuple[str, str], float] = {}
            for comp_name in scc:
                comp = self.components[comp_name]
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
                    val = self.components[src_c].outputs[src_p].get()
                    val = val.magnitude if isinstance(val, Quantity) else val
                    y = float(val) if val is not None else 0.0
                r[i] = u_vec[i] - y
            return r
        
        # 6) Interface Jacobian by finite differences        
        def compute_interface_jacobian(u_vec: np.ndarray,
                                       r_vec: np.ndarray) -> np.ndarray:
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
        max_iter = 50
        tol = 1e-6
        u_current = u0.copy()
        
        for k in range(max_iter):
            # Compute residual
            r_current = compute_interface_residual(u_current)
            
            # Check convergence
            if np.linalg.norm(r_current) < tol:
                break
            
            # Compute Jacobian
            J_current = compute_interface_jacobian(u_current, r_current)
            
            # Solve for correction: J * Δu = -r
            try:
                delta_u = np.linalg.solve(J_current, -r_current)
            except np.linalg.LinAlgError:
                raise RuntimeError(f"Singular Jacobian in IJCSA for SCC {scc}")
            
            # Apply correction
            u_current += delta_u
        else:
            raise RuntimeError(f"IJCSA did not converge for SCC {scc} after {max_iter} iterations")
        
        # 8) Commit solved interface inputs to components
        for (dst_c, dst_p), i in idx_of_input.items():
            self.components[dst_c].inputs[dst_p].set(float(u_current[i]), t)
            
    #----------------------------------------------------------------------------
    # Helpers
    #----------------------------------------------------------------------------
    def _compute_used_outputs(self):
        used = defaultdict(set)
        for c in self.connections:
            used[c.src_comp].add(c.src_port)
        return used
    
    def _is_delayed_producer(self, name: str) -> bool:
        """
        Heuristic: detect components that
          - have no zero-delay (direct-feedthrough) incident edges in self._dag
          - but DO eventually feed into components that participate in zero-delay structure.

        These are typically actuator-like components: their outputs influence the
        closed loop, but only via *state* of downstream FMUs/controllers.
        """
        # 1) Must NOT be involved in any zero-delay edges
        if self._dag.in_degree(name) > 0 or self._dag.out_degree(name) > 0:
            return False

        # 2) Precompute: nodes that *do* participate in any zero-delay structure
        zero_delay_nodes = {
            n for n in self._dag.nodes
            if self._dag.in_degree(n) > 0 or self._dag.out_degree(n) > 0
        }
        if not zero_delay_nodes:
            return False

        # 3) There must be a path in the full connection graph from this node
        #    to at least one zero-delay node.
        for target in zero_delay_nodes:
            if nx.has_path(self.graph, name, target):
                return True

        return False

    def _move_delayed_producers_to_last_generation(self) -> None:
        """
        Post-process self.execution_order:
          - Find all 'delayed producers' (see _is_delayed_producer).
          - Remove them from their current generations.
          - Append them as a new last generation (sorted).
        """
        if not self.execution_order:
            return

        # Collect candidates
        delayed_producers = {
            name
            for name in self.components.keys()
            if self._is_delayed_producer(name)
        }
        if not delayed_producers:
            return

        # Remove them from existing gens
        new_gens: list[list[str]] = []
        for gen in self.execution_order:
            keep = [name for name in gen if name not in delayed_producers]
            if keep:
                new_gens.append(keep)

        # Append them as the last generation
        last_gen = sorted(delayed_producers)
        new_gens.append(last_gen)

        # Store back and rebuild index map
        self.execution_order = new_gens
        self.execution_idx.clear()
        for idx, gen in enumerate(self.execution_order):
            for name in gen:
                self.execution_idx[name] = idx

    def _collect_global_interface_unknowns(self) -> Tuple[List[Tuple[str, str]], Dict[Tuple[str, str], Tuple[str, str]]]:
        """
        Collect all interface inputs that participate in zero-delay couplings.

        Returns:
        interface_inputs: list of (dst_comp_name, dst_port_name)
        driver_map: mapping (dst_comp, dst_port) -> (src_comp, src_port)
        """
        interface_inputs: List[Tuple[str, str]] = []
        driver_map: Dict[Tuple[str, str], Tuple[str, str]] = {}

        if self._dag is None:
            return interface_inputs, driver_map
        
        for src, dst, data in self._dag.edges(data=True):
            src_port = data.get('src_port')
            dst_port = data.get('dst_port')
            key = (dst, dst_port)
            interface_inputs.append(key)
            driver_map[key] = (src, src_port)

        interface_inputs = sorted(set(interface_inputs))
        return interface_inputs, driver_map

    #----------------------------------------------------------------------------
    # Global Interface Jacobian-based Co-Simulation Step Helpers
    #----------------------------------------------------------------------------  
    def _compute_interface_residual_global(
            self,
            U: np.ndarray,
            interface_inputs: List[Tuple[str, str]],
            driver_map: Dict[Tuple[str, str], Tuple[str, str]],
            t: float
    ) -> np.ndarray:
        """
        Compute R(U) = U - Y(U) for ALL zero-delay connections in the system
        with frozen FMU states at time t.

        U: vector of size n, ordered like interface_inputs.
        """
        # Map from input (dst_comp, dst_port) -> scalar value
        input_values: Dict[Tuple[str, str], float] = {}
        for key, val in zip(interface_inputs, U):
            input_values[key] = val

        # 1) Build input dicts per component for this evaluation
        comp_inputs: Dict[str, Dict[str, float]] = {name: {} for name in self.components.keys()}

        # 2) Set all interface inputs from U
        for (dst_c, dst_p), val in input_values.items():
            comp_inputs[dst_c][dst_p] = val
        
        # 3) Evaluate outputs of all components
        for comp_name, comp in self.components.items():
            inputs = comp_inputs.get(comp_name, {})
            comp.evaluate_outputs(inputs)
        
        # 4) Build residuals
        R = np.zeros(len(interface_inputs), dtype=float)
        for i, (dst_c, dst_p) in enumerate(interface_inputs):
            src_c, src_p = driver_map[(dst_c, dst_p)]
            y_val = self.components[src_c].outputs[src_p].get()
            y_val = y_val.magnitude if isinstance(y_val, Quantity) else y_val
            y = float(y_val) if y_val is not None else 0.0
            R[i] = U[i] - y
        
        return R
    
    def _compute_interface_jacobian_global(
            self,
            U: np.ndarray,
            interface_inputs: List[Tuple[str, str]],
            driver_map: Dict[Tuple[str, str], Tuple[str, str]],
            t: float,
            eps: float = 1e-6
    ) -> np.ndarray:
        """
        Finite-difference Jacobian J ≈ ∂R/∂U for the global interface system.
        """
        n = len(U)
        J = np.zeros((n, n), dtype=float)

        # Base residual
        R0 = self._compute_interface_residual_global(U, interface_inputs, driver_map, t)

        for j in range(n):
            U_pert = U.copy()
            delta = eps * max(1.0, abs(U[j]))
            U_pert[j] += delta

            R_pert = self._compute_interface_residual_global(U_pert, interface_inputs, driver_map, t)
            J[:, j] = (R_pert - R0) / delta
        
        return J

    def _solve_global_interface_ijcsa(self, t: float) -> None:
        """
        Global Interface-Newton (IJCSA) at time t:

        - Unknowns: all zero-delay interface inputs in the system.
        - States are frozen at t (no progression of time).
        - After convergence, component input and output PortStates are consistent.
        """
        interface_inputs, driver_map = self._collect_global_interface_unknowns()
        n = len(interface_inputs)
        if n == 0:
            return  # nothing to solve
        
        # 1) Build initial guess U0 from current input values
        U0 = np.zeros(n, dtype=float)
        for i, (dst_c, dst_p) in enumerate(interface_inputs):
            val = self.components[dst_c].inputs[dst_p].get()
            val = val.magnitude if isinstance(val, Quantity) else val
            U0[i] = float(val) if val is not None else 0.0
        
        # 2) Newton iteration on R(U) = 0
        max_iter = 50
        tol = 1e-6
        U = U0.copy()

        for k in range(max_iter):
            R = self._compute_interface_residual_global(U, interface_inputs, driver_map, t)
            norm_R = np.linalg.norm(R, ord=2)

            # Optional debug logging
            # print(f"IJCSA Iter {k}: ||R|| = {np.linalg.norm(R)}")

            # Check convergence
            if norm_R < tol:
                break

            J = self._compute_interface_jacobian_global(U, interface_inputs, driver_map, t)

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
        comp_inputs: Dict[str, Dict[str, float]] = {name: {} for name in self.components.keys()}
        for (dst_c, dst_p), val in input_values.items():
            comp_inputs[dst_c][dst_p] = val
        
        # Apply to components and evaluate outputs
        for comp_name, comp in self.components.items():
            inputs = comp_inputs.get(comp_name, {})
            if inputs:
                comp.set_inputs(inputs, t)
            comp.evaluate_outputs(inputs)