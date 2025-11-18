from __future__ import annotations
from collections import defaultdict
from typing import Dict, List, Any, Tuple

import networkx as nx
import numpy as np

from .connection import Connection
from ..core.base import CoSimComponent
from ..core.port import PortSpec

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
        self.algorithm: str = "Gauss-Seidel"  # or "Jacobi"
    
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
    # Step methods for Gauss-Seidel and Jacobi algorithms
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
        while t < tf - 1e-12:
            step_func(t, dt)
            t += dt

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
            val = self.components[dst_c].inputs[dst_p].value.magnitude
            u0[i] = float(val) if val is not None else 0.0

        # 5) Residual Evaluation F(U)
        def compute_interface_residual(u_vec: np.ndarray) -> np.ndarray:
            """
            Given interface input values u_vec, evaluate residual F(U) = U - Y(U).

            Uses _eval_component_outputs() to keep FMU state unchanged.
            """
            # Build per-component input values
            comp_inputs: Dict[str, Dict[str, Any]] = {name: {} for name in scc}

            # 5.1) External zero-delay drivers into SCC
            for scrc_c, src_p, dst_c, dst_p in external_in_connections:
                val = self.components[scrc_c].outputs[src_p].value.magnitude
                comp_inputs[dst_c][dst_p] = float(val)

            # 5.2) Internal interface inputs (unknowns U)
            for (dst_c, dst_p), i in idx_of_input.items():
                comp_inputs[dst_c][dst_p] = float(u_vec[i])
            
            # 5.3) Evaluate outputs of all components in SCC
            computed_out: Dict[Tuple[str, str], float] = {}
            for comp_name in scc:
                comp = self.components[comp_name]
                in_vals = comp_inputs.get(comp_name, {})
                #out_vals = self._eval_component_outputs(comp, in_vals, t)
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
                    y = float(self.components[src_c].outputs[src_p].value.magnitude or 0.0)
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