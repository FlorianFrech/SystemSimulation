from __future__ import annotations
from typing import Dict, List
import networkx as nx
from .connection import Connection
from ..core.base import CoSimComponent

class System:
    def __init__(self, name: str):
        self.name = name
        self.components: Dict[str, CoSimComponent] = {}
        self.connections: List[Connection] = []
        self.graph = nx.MultiDiGraph()
        self.groups: Dict[str, List[CoSimComponent]] = {}
        self.execution_order: List[List[str]] = []  # Parallelizable layers of component names
        self.execution_idx: Dict[str, int] = {}  # Map component to its execution layer index
    
    def add_component(self, component: CoSimComponent):
        """
        Add a CoSimComponent to the system.
        """
        if component.name in self.components:
            raise ValueError(f"Component with name {component.name} already exists in the system.")
        self.components[component.name] = component
        if component.group:
            if component.group not in self.groups:
                self.groups[component.group] = []
            self.groups[component.group].append(component)

    def _validate_connection(self, connection: Connection):
        """
        Validate a Connection between two components in the system.
        """
        # Check if the connection already exists
        for conn in self.connections:
            if conn.src_comp == connection.src_comp and conn.dst_comp == connection.dst_comp:
                if conn.src_port == connection.src_port and conn.dst_port == connection.dst_port:
                    raise ValueError(f"Connection from {connection.src_comp.name}.{connection.src_port.name} to"
                                     f" {connection.dst_comp.name}.{connection.dst_port.name} already exists.")

        # Check that both components are part of the system
        if connection.src_comp not in self.components.values() or connection.dst_comp not in self.components.values():
            raise ValueError(f"Both {connection.src_comp.name} and {connection.dst_comp.name} must be part of the system.")
        
    def add_connection(self, connection: Connection):
        """
        Add a Connection between two components in the system.
        """
        try:
            self._validate_connection(connection)
        except ValueError as e:
            print(f"Connection validation error:\n{e}")
            return        
        self.connections.append(connection)
    
    def compute_execution_order(self) -> None:
        dag = nx.DiGraph()
        dag.add_nodes_from(self.components.keys())

        # Only zero-delay connections enforce same-tick ordering
        for conn in self.connections:
            if conn.delay == 0:
                dag.add_edge(conn.src_comp.name, conn.dst_comp.name)
        
        # Check for cycles
        if not nx.is_directed_acyclic_graph(dag):
            cycles = list(nx.simple_cycles(dag))
            raise RuntimeError(
                "Cycle(s) detected among zero-delay dependencies: " +
                "; ".join(" -> ".join(c) for c in cycles)
            )

        # Parallelizable execution order
        self.execution_order = list(nx.topological_generations(dag))

        # Map components to their execution layer index
        for idx, gen in enumerate(self.execution_order):
            for comp_name in gen:
                self.execution_idx[comp_name] = idx + 1

    def set_inputs(self) -> None:
        f
    
