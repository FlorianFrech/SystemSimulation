from __future__ import annotations
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass

import networkx as nx

from .connection import Connection, EventConnection
from . import graph
from .algorithms.base import Algorithm
from .algorithms.gauss_seidel import GaussSeidelAlgorithm
from .algorithms.hybrid_jacobi import HybridJacobiAlgorithm
from .algorithms.ijcsa import solve_algebraic_scc_ijcsa
from ..core.base import CoSimComponent
from ..core.events import Event
from ..core.port import PortSpec
from ..core.history import SystemHistory

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
    """
    
    def __init__(self, name: str):
        self.name = name
        self.components: Dict[str, CoSimComponent] = {}
        self.connections: List[Connection] = []
        self.event_connections: List[EventConnection] = []
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
        self._input_sources: Dict[str, Dict[str, Connection]] = {}
        self._event_targets_by_source: Dict[Tuple[str, str], List[str]] = {}

        # Algorithm
        self.algorithm: Algorithm = GaussSeidelAlgorithm()

        # History Management
        self.history = SystemHistory(system_name=name)
    
    #----------------------------------------------------------------------------
    # Algorithm
    #----------------------------------------------------------------------------
    def set_algorithm(self, algorithm: Algorithm) -> None:
        """
        Set the co-simulation stepping algorithm.
        """
        if not isinstance(algorithm, Algorithm):
            raise TypeError("algorithm must implement Algorithm")
        self.algorithm = algorithm
    
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
        self._input_sources.clear()

    #----------------------------------------------------------------------------
    # Event Connections
    #----------------------------------------------------------------------------
    def _validate_event_connection(self, connection: EventConnection) -> None:
        if connection.src_comp not in self.components:
            raise ValueError(f"Event source '{connection.src_comp}' is not in the system.")
        if connection.dst_comp not in self.components:
            raise ValueError(f"Event target '{connection.dst_comp}' is not in the system.")

        source = self.components[connection.src_comp]
        target = self.components[connection.dst_comp]
        event_name = connection.src_port
        if event_name not in source.event_indicators:
            raise KeyError(
                f"Event '{event_name}' not found on source component '{source.name}'."
            )

        has_subscription = False
        for event in target.event_subscriptions:
            if event.name == event_name:
                has_subscription = True
                break
        
        if not has_subscription:
            raise KeyError(
                f"Target '{target.name}' is not subscribed to event '{source.name}:{event_name}'."
            )

        for existing in self.event_connections:
            if existing == connection:
                raise ValueError(
                    f"Duplicate event connection: {connection.src_comp}:{connection.event_name} -> {connection.target_comp}"
                )

    def add_event_connection(self, connection: EventConnection) -> None:
        self._validate_event_connection(connection)
        self.event_connections.append(connection)
        key = (connection.src_comp, connection.src_port)
        self._event_targets_by_source.setdefault(key, []).append(connection.dst_comp)

    def get_event_targets(self, source_comp: str, event_name: str) -> List[str]:
        return self._event_targets_by_source.get((source_comp, event_name), []).copy()

    def dispatch_event(self, event: Event, t: float, notify: bool = True) -> List[str]:
        """
        Resolve event listeners for a given event and optionally notify them.
        """
        if event.source not in self.components:
            raise ValueError(f"Event source '{event.source}' is not in the system.")

        targets = self.get_event_targets(event.source, event.name)
        if notify:
            for comp_name in targets:
                self.components[comp_name].handle_event([event.name], t)
        return targets

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
        graph.build_graphs(self)

    def compute_execution_order(self) -> None:
        """
        Compute a parallelizable execution order based on zero-delay dependencies.
        """
        graph.compute_execution_order(self)

    def classify_components(self) -> Dict[str, List[str]]:
        """
        Classify components for hybrid co-simulation handling.

        Returns:
            Dict with keys:
            - "event_sources": components with indicators (rollback required)
            - "event_listeners": components subscribed to events only
            - "continuous_only": components without hybrid capabilities
        """
        self.event_sources: List[str] = []
        self.event_listeners: List[str] = []
        self.continuous_only: List[str] = []

        for comp in self.components.values():
            if comp.has_state_events:
                self.event_sources.append(comp)
            if comp.has_event_subscriptions:
                self.event_listeners.append(comp)
            if not comp.has_state_events and not comp.has_event_subscriptions:
                self.continuous_only.append(comp)
        return {
            "event_sources": self.event_sources,
            "event_listeners": self.event_listeners,
            "continuous_only": self.continuous_only,
        }
    
    #----------------------------------------------------------------------------
    # Simulation Lifecycle
    #----------------------------------------------------------------------------
    def initialize(self, t0: float) -> None:
        """
        Initialize all components in the system at start time t0.
        Also build graphs and compute execution order.
        Store t_end for reference.
        """
        # 1) Set simulation time parameters
        self.time = t0

        # 2) Initialize all CoSimComponents
        for comp in self.components.values():
            comp.initialize(t0)

        # 2.5) Auto-select hybrid algorithm if needed
        self.classify_components()
        if self.event_sources:
            self.algorithm = HybridJacobiAlgorithm()
        
        # 3) Build connections and compute execution order
        self.build_graphs()
        self.compute_execution_order()
        
        # 4) Set initial inputs and solve for consistent initial state
        for gen in self.execution_order:
            self._set_inputs_for_generation(gen, t0)

            gen_set = set(gen)
            for loop in self.algebraic_loops:
                if set(loop).issubset(gen_set):
                    solve_algebraic_scc_ijcsa(self, loop, t0)
            
            for comp_name in gen:
                comp = self.components[comp_name]
                comp.do_step(0, 0)
    
    def _set_inputs_for_generation(self, gen: List[str], t: float) -> None:
        """
        For each component in the generation, set its INPUT by scanning connections whose
        dst_comp is the component. For delay > 0, use history; for delay == 0, use current value.
        """        
        for comp_name in gen:
            comp = self.components[comp_name]
            to_set: Dict[str, Any] = {}
            input_map = self._input_sources.get(comp_name, {})
            for dst_port, c in input_map.items():
                src_value = self.components[c.src_comp].outputs[c.src_port].get()
                if src_value is not None:
                    to_set[dst_port] = src_value
            
            if to_set:
                comp.set_inputs(to_set, t=t)

    #----------------------------------------------------------------------------
    # Run System Simulation
    #----------------------------------------------------------------------------
    def run(self, t0: float, tf: float, dt: float):
        """
        Run the simulation from t0 to tf with step size dt.
        """
        t = t0
        self.t_end = tf
        while t < tf - 1e-12:
            dt = min(dt, tf - t)
            self.algorithm.step(self, t, dt)
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
        history['Events'] = self.history.get_all_event_histories()
        return history