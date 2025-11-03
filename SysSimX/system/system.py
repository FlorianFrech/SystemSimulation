from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Any, Tuple, Optional

import networkx as nx

from .connection import Connection
from ..core.base import CoSimComponent
from ..core.port import PortSpec, PortType

_ports_compatible = PortSpec.compatible

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
    
    #--------------------------------------------------------------
    # Register components

    def add_component(self, component: CoSimComponent):
        """
        Add a CoSimComponent to the system.
        """
        if component.name in self.components:
            raise ValueError(f"Component '{component.name}' already in system.")
        self.components[component.name] = component
        if component.group:
            self.groups.setdefault(component.group, []).append(component)
    
    #--------------------------------------------------------------
    # Connections

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
                existing.dst_comp == c.dst_comp and existing.dst_port == c.dst_port and
                existing.delay == c.delay):
                raise ValueError(
                    f"Duplicate connection: {c.src_comp}.{c.src_port} -> {c.dst_comp}.{c.dst_port} with delay {c.delay}"
                    )

    def add_connection(self, connection: Connection) -> None:
        """
        Add a Connection between two components in the system.
        """
        self._validate_connection(connection)
        self.connections.append(connection)

    #--------------------------------------------------------------
    # Graphs

    def build_graphs(self) -> None:
        """
        Build the full connection graph and the zero-delay DAG.
        """
        self.graph.clear()
        self._dag.clear()
        
        # nodes
        for name in self.components:
            self.graph.add_node(name)
            self._dag.add_node(name)

        # edges
        for c in self.connections:
            # annotated edges
            self.graph.add_edge(
                c.src_comp, c.dst_comp,
                src_port=c.src_port, dst_port=c.dst_port,
                delay=c.delay, unit=c.unit or None
            )

            # computational DAG (only zero-delay)
            if c.delay == 0:
                self._dag.add_edge(
                    c.src_comp, c.dst_comp,
                    src_port=c.src_port, dst_port=c.dst_port
                )
        
        # cycle check for 0-delay dependencies
        if not nx.is_directed_acyclic_graph(self._dag):
            cycles = list(nx.simple_cycles(self._dag))
            raise RuntimeError(
                "Cycle(s) detected among zero-delay dependencies, add a delay to break the cycle: " +
                "; ".join(" -> ".join(c) for c in cycles)
            )
            
    def compute_execution_order(self) -> None:
        """
        Compute a parallelizable execution order based on zero-delay dependencies.
        """
        if self._dag.number_of_nodes() == 0:
            self.build_graphs()
        gens = list(nx.topological_generations(self._dag))

        # normalize to list of lists
        self.execution_order = [sorted(list(gen)) for gen in gens] # sort for determinism
        self.execution_idx.clear()
        for idx, gen in enumerate(self.execution_order):
            for name in gen:
                self.execution_idx[name] = idx
    
    #--------------------------------------------------------------
    # Simulation Lifecycle

    def initialize(self, t0: float) -> None:
        for comp in self.components.values():
            comp.initialize(t0)
        self.build_graphs()
        self.compute_execution_order()
    
    def _get_latest_values(self, comp_name: str, port_name: str, delay_steps: int) -> Any:
        """
        Fetch a value from a component's OUTPUT port,
         - delay_steps == 0 -> current value (read from PortState.value)
         - delay_steps > 0  -> historical value (read from PortState.history)
        """
        comp = self.components[comp_name]
        ps = comp.outputs[port_name]

        if delay_steps <= 0:
            return ps.get()
        
        hist = list(ps.history)
        if len(hist) >= delay_steps:
            return hist[-delay_steps][1]  # (time, value)
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
                src_value = self._get_latest_values(c.src_comp, c.src_port, c.delay)
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
        # Phase 1: Set inputs for all generations
        for gen in self.execution_order:
            self._set_inputs_for_generation(gen, t)
        
        # Phase 2: Do step for all generations
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
        while t < tf - 1e-12:
            self.step(t, dt)
            t += dt