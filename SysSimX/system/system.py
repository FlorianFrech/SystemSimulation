from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Any, Tuple, Optional

import networkx as nx
import numpy as np
from scipy.optimize import root

from .connection import Connection
from ..core.base import CoSimComponent
from ..core.port import PortSpec, PortType

from IPython.display import display, Markdown
import ipywidgets as widgets
from ipywidgets import Layout, HBox, VBox, HTML

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
        
        # nodes
        for name in self.components:
            self.graph.add_node(name)
            self._dag.add_node(name)

        for c in self.connections:
            self.graph.add_edge(
                c.src_comp, c.dst_comp,
                src_port=c.src_port, dst_port=c.dst_port,
                unit=c.unit or None
            )

            dst_comp = self.components[c.dst_comp]
            # direct_feedthrough mapping: output_port -> [input_ports it depends on]
            # We need to know if ANY output of dst_comp depends on c.dst_port.
            zero_delay = False
            for out_port, in_list in dst_comp.direct_feedthrough.items():
                if in_list:  # only consider non-empty feedthrough lists
                    if c.dst_port in in_list:
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
            scc_members[cid] = sorted(scc_members[cid])  # deterministic

        # Save per-node SCC index for later use (e.g., coupled solving)
        self._scc_index = {name: mapping[name] for name in self.components.keys() if name in mapping}

        # Topological generations on condensed DAG
        gens_c = list(nx.topological_generations(condensed))

        # Expand generations back to component names; SCCs appear as grouped lists
        # Keep shape: List[List[str]] so existing callers continue to work.
        self.execution_order = []
        self.execution_idx.clear()

        idx = 0
        for gen in gens_c:
            # gen is a list of SCC ids that can run in parallel
            expanded: List[str] = []
            for cid in gen:
                members = scc_members.get(cid, [])
                # Important: members of the same SCC are not parallelizable in general;
                # we return them as a single generation entry to be handled by a coupled solver later.
                # For now we append all; the stepper can be extended to detect SCCs and iterate.
                expanded.extend(members)
            expanded = sorted(expanded)  # stable deterministic order across SCCs in the same layer
            self.execution_order.append(expanded)
            for name in expanded:
                self.execution_idx[name] = idx
            idx += 1
    
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
    
    def _get_latest_values(self, comp_name: str, port_name: str) -> Any:
        """
        Fetch a value from a component's OUTPUT port,
         - delay_steps == 0 -> current value (read from PortState.value)
         - delay_steps > 0  -> historical value (read from PortState.history)
        """
        comp = self.components[comp_name]
        ps = comp.outputs[port_name]
        return ps.get() # fallback to last known value
    
    def _set_inputs_for_generation(self, gen: List[str], t: float) -> None:
        """
        For each component in the generation, set its INPUT by scanning connections whose
        dst_comp is the component. For delay > 0, use history; for delay == 0, use current value.
        """
        # Pre-group edges by destination component
        incoming_by_dst: Dict[str, List[Connection]] = {}
        for c in self.connections:
            incoming_by_dst.setdefault(c.dst_comp, []).append(c)
        
        for comp_name in gen:
            comp = self.components[comp_name]
            to_set: Dict[str, Any] = {}

            for c in incoming_by_dst.get(comp_name, []):
                # Detect multiple drivers for the same input port
                if c.dst_port in to_set:
                    raise RuntimeError(
                        f"Multiple drivers for input port '{comp_name}.{c.dst_port}' "
                        f"from '{to_set[c.dst_port]}' and '{c.src_comp}.{c.src_port}'"
                    )
                src_value = self._get_latest_values(c.src_comp, c.src_port)
                if src_value is not None:
                    to_set[c.dst_port] = src_value
            
            if to_set:
                comp.set_inputs(to_set, t=t)

    def step(self, t: float, dt: float) -> None:
        """
        Perform a simulation step:
         1) For each generation in execution order, set inputs for all components in the generation
         2) For each generation, call do_step on all components in the generation
        """
        for gen in self.execution_order:
            # Phase 1: Set inputs for all generations
            self._set_inputs_for_generation(gen, t)

            # Phase 2: solve algebraic loops if any in this generation
            gen_set = set(gen)
            for loop in self.algebraic_loops:
                if set(loop).issubset(gen_set):
                    self._solve_algebraic_scc(loop, t)

        # Phase 3: Do step for all generations
        for gen in self.execution_order:
            for comp_name in gen:
                comp = self.components[comp_name]
                comp.do_step(t, dt)

    def run(self, t0: float, tf: float, dt: float):
        """
        Run the simulation from t0 to tf with step size dt.
        """
        #self.initialize(t0)
        t = t0
        self.t_end = tf
        while t < tf - 1e-12:
            self.step(t, dt)
            t += dt

    #----------------------------------------------------------------------------
    # Resolve algebraic loops
    #----------------------------------------------------------------------------
    # Evaluate a component's outputs with provided inputs, no side effects if possible
    def _eval_component_outputs(self, comp: CoSimComponent, in_vals: Dict[str, Any], t: float) -> Dict[str, Any]:
        # Preferred: user-provided pure function
        if hasattr(comp, 'eval_outputs') and callable(getattr(comp, 'eval_outputs')):
            return comp.eval_outputs(**in_vals)

        # Fallback: minimal side-effect evaluation via _do_step_internal
        # Save old inputs/outputs
        old_inputs = {k: p.get() for k, p in comp.inputs.items()}
        old_outputs = {k: p.get() for k, p in comp.outputs.items()}

        # Set given inputs, keep others unchanged
        for name, val in in_vals.items():
            if name in comp.inputs:
                comp.inputs[name].set(val, t)

        # Evaluate at dt=0
        comp._do_step_internal(t, 0.0)
        out_now = {k: p.get() for k, p in comp.outputs.items()}

        # Restore
        for k, v in old_outputs.items():
            comp.outputs[k].set(v, t)
        for k, v in old_inputs.items():
            comp.inputs[k].set(v, t)

        return out_now

    # Collect unknowns for an SCC as the set of (src_comp, src_port) used on zero-delay edges inside SCC
    def _collect_scc_unknowns(self, scc: List[str]) -> List[Tuple[str, str]]:
        scc_set = set(scc)
        unknowns = []
        for c in self.connections:
            if c.src_comp in scc_set and c.dst_comp in scc_set:
                dst_comp = self.components[c.dst_comp]
                # zero-delay if any output depends on this input port
                zero_delay = any(
                    c.dst_port in in_list
                    for in_list in dst_comp.direct_feedthrough.values()
                    if in_list
                )
                if zero_delay:
                    unknowns.append((c.src_comp, c.src_port))
        # unique and stable
        return sorted(set(unknowns), key=lambda x: (x[0], x[1]))

    def _solve_algebraic_scc(self, scc: List[str], t: float) -> None:
        if not scc:
            return

        unknowns = self._collect_scc_unknowns(scc)
        if not unknowns:
            return

        idx_of = {key: i for i, key in enumerate(unknowns)}
        x0 = np.array([
            self.components[c].outputs[out].get() if self.components[c].outputs[out].get() is not None else 0.0
            for (c, out) in unknowns
        ], dtype=float)

        scc_set = set(scc)
        internal_edges = []      # (src_comp, src_port, dst_comp, dst_port)
        external_in_edges = []   # (src_comp, src_port, dst_comp, dst_port)
        for c in self.connections:
            dst_comp = self.components[c.dst_comp]
            zero_delay = any(
                c.dst_port in in_list
                for in_list in dst_comp.direct_feedthrough.values()
                if in_list
            )
            if not zero_delay:
                continue
            if c.src_comp in scc_set and c.dst_comp in scc_set:
                internal_edges.append((c.src_comp, c.src_port, c.dst_comp, c.dst_port))
            elif c.src_comp not in scc_set and c.dst_comp in scc_set:
                external_in_edges.append((c.src_comp, c.src_port, c.dst_comp, c.dst_port))

        def residual(z_vec: np.ndarray) -> np.ndarray:
            in_vals_by_comp: Dict[str, Dict[str, Any]] = {name: {} for name in scc}
            # external drivers
            for src_c, src_p, dst_c, dst_p in external_in_edges:
                val = self._get_latest_values(src_c, src_p)
                in_vals_by_comp[dst_c][dst_p] = val
            # internal drivers (from z)
            for src_c, src_p, dst_c, dst_p in internal_edges:
                idx = idx_of.get((src_c, src_p))
                if idx is not None:
                    in_vals_by_comp[dst_c][dst_p] = float(z_vec[idx])

            # evaluate outputs
            computed_out: Dict[Tuple[str, str], float] = {}
            for comp_name in scc:
                comp = self.components[comp_name]
                out_vals = self._eval_component_outputs(comp, in_vals_by_comp.get(comp_name, {}), t)
                for (cname, out_port) in unknowns:
                    if cname == comp_name and out_port in out_vals:
                        computed_out[(cname, out_port)] = float(out_vals[out_port])

            r = np.zeros(len(unknowns), dtype=float)
            for i, (cname, out_port) in enumerate(unknowns):
                fi = computed_out.get((cname, out_port), 0.0)
                r[i] = z_vec[i] - fi
            return r

        sol = root(residual, x0, method='hybr')
        if not sol.success:
            raise RuntimeError(f"Algebraic loop solve failed for SCC {scc}: {sol.message}")

        # commit solved outputs
        for (cname, out_port), val in zip(unknowns, sol.x):
            self.components[cname].outputs[out_port].set(float(val), t)

        # write back to downstream inputs inside SCC for consistency
        for src_c, src_p, dst_c, dst_p in internal_edges:
            idx = idx_of.get((src_c, src_p))
            val = float(sol.x[idx]) if idx is not None else float(self._get_latest_values(src_c, src_p))
            self.components[dst_c].inputs[dst_p].set(val, t)