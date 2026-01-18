from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

import networkx as nx

if TYPE_CHECKING:
    from .system import System


def collect_active_outputs(system: System) -> dict[str, set[str]]:
    used = defaultdict(set)
    for c in system.connections:
        used[c.src_comp].add(c.src_port)
    return used


def build_graphs(system: System) -> None:
    """
    Build:
      - system.graph: all connections (annotated)
      - system._dag: zero-delay true-direct-feedthrough dependencies only
      - system.algebraic_loops: SCCs (>1) on system._dag
    """
    # 1) Clear existing gaph data
    system.graph.clear()
    system._dag.clear()
    system.algebraic_loops.clear()
    system._scc_index.clear()
    system._incoming_by_dst.clear()
    system._input_sources.clear()

    # 2) Add components as nodes
    for name in system.components:
        system.graph.add_node(name)
        system._dag.add_node(name)
    active_outputs = collect_active_outputs(system)

    # 3) Add connections as edges
    for c in system.connections:
        # a) Record incoming connections and input sources
        system._incoming_by_dst.setdefault(c.dst_comp, []).append(c)
        dst_map = system._input_sources.setdefault(c.dst_comp, {})

        # b) Check for multiple drivers for same input port
        if c.dst_port in dst_map:
            raise RuntimeError(
                f"Multiple drivers for input port '{c.dst_comp}.{c.dst_port}' "
                f"from '{dst_map[c.dst_port].src_comp}.{dst_map[c.dst_port].src_port}' "
                f"and '{c.src_comp}.{c.src_port}'"
            )
        dst_map[c.dst_port] = c

        # c) Add edges to graphs
        system.graph.add_edge(c.src_comp, c.dst_comp, src_port=c.src_port, dst_port=c.dst_port)

        # d) Determine if this is a zero-delay direct-feedthrough edge
        dst_comp = system.components[c.dst_comp]
        zero_delay = False
        relevant_outputs = active_outputs.get(c.dst_comp, set())
        for out_port, deps in dst_comp.direct_feedthrough.items():
            if out_port not in relevant_outputs:
                continue
            if deps and c.dst_port in deps:
                zero_delay = True
                break
        if zero_delay:
            system._dag.add_edge(c.src_comp, c.dst_comp, src_port=c.src_port, dst_port=c.dst_port)

    # 4) Identify algebraic loops (SCCs with size > 1)
    sccs = list(nx.strongly_connected_components(system._dag))
    system.algebraic_loops = [list(scc) for scc in sccs if len(scc) > 1]

    # 5) Identify single-node SCCs with self-loops as well
    for node in system._dag.nodes:
        if system._dag.has_edge(node, node) and node not in system.algebraic_loops:
            system.algebraic_loops.append([node])


def compute_execution_order(system: System) -> None:
    """
    Compute a parallelizable execution order based on zero-delay dependencies.
    """
    # 1) Ensure graphs are built
    if system._dag.number_of_nodes() == 0:
        build_graphs(system)

    # 2) Condensation: nodes are SCC ids (0..k-1), edges reflect inter-SCC dependencies
    condensed = nx.condensation(system._dag)
    mapping: dict[str, int] = condensed.graph.get("mapping", {})  # original node -> scc id

    # 3) Reverse mapping: scc id -> list of original component names
    scc_members: dict[int, list[str]] = {}
    for comp_name, scc_id in mapping.items():
        scc_members.setdefault(scc_id, []).append(comp_name)
    for cid in scc_members:
        scc_members[cid] = sorted(scc_members[cid])
    system._scc_index = {
        name: mapping[name] for name in system.components.keys() if name in mapping
    }

    # 4) Topological generations on condensed graph to get execution order
    gens_c = list(nx.topological_generations(condensed))

    # 5) Expand SCC ids back to component names for final execution order
    system.execution_order = []
    system.execution_idx.clear()
    idx = 0
    for gen in gens_c:
        expanded: list[str] = []
        for cid in gen:
            members = scc_members.get(cid, [])
            expanded.extend(members)
        expanded = sorted(expanded)
        system.execution_order.append(expanded)
        for name in expanded:
            system.execution_idx[name] = idx
        idx += 1

    # 6) Post-process: move 'delayed producers' to last generation
    move_delayed_producers_to_last_generation(system)


def is_delayed_producer(system: System, name: str) -> bool:
    """
    Heuristic: detect components that
      - have no zero-delay (direct-feedthrough) incident edges in system._dag
      - but DO eventually feed into components that participate in zero-delay structure.

    These are typically actuator-like components: their outputs influence the
    closed loop, but only via *state* of downstream FMUs/controllers.
    """
    # 1) Must NOT be involved in any zero-delay edges
    if system._dag.in_degree(name) > 0 or system._dag.out_degree(name) > 0:
        return False

    # 2) Precompute: nodes that *do* participate in any zero-delay structure
    zero_delay_nodes = {
        n
        for n in system._dag.nodes
        if system._dag.in_degree(n) > 0 or system._dag.out_degree(n) > 0
    }
    if not zero_delay_nodes:
        return False

    # 3) There must be a path in the full connection graph from this node
    #    to at least one zero-delay node.
    for target in zero_delay_nodes:
        if nx.has_path(system.graph, name, target):
            return True

    return False


def move_delayed_producers_to_last_generation(system: System) -> None:
    """
    Post-process system.execution_order:
      - Find all 'delayed producers' (see is_delayed_producer).
      - Remove them from their current generations.
      - Append them as a new last generation (sorted).
    """
    if not system.execution_order:
        return

    # 1) Collect candidates
    delayed_producers = {
        name for name in system.components.keys() if is_delayed_producer(system, name)
    }
    if not delayed_producers:
        return

    # 2) Remove them from existing gens
    new_gens: list[list[str]] = []
    for gen in system.execution_order:
        keep = [name for name in gen if name not in delayed_producers]
        if keep:
            new_gens.append(keep)

    # 3) Append them as the last generation
    last_gen = sorted(delayed_producers)
    new_gens.append(last_gen)

    # 4) Store back and rebuild index map
    system.execution_order = new_gens
    system.execution_idx.clear()
    for idx, gen in enumerate(system.execution_order):
        for name in gen:
            system.execution_idx[name] = idx


def collect_global_interface_unknowns(
    system: System,
) -> tuple[list[tuple[str, str]], dict[tuple[str, str], tuple[str, str]]]:
    """
    Collect all interface inputs that participate in zero-delay couplings.

    Returns:
    interface_inputs: list of (dst_comp_name, dst_port_name)
    driver_map: mapping (dst_comp, dst_port) -> (src_comp, src_port)
    """
    interface_inputs: list[tuple[str, str]] = []
    driver_map: dict[tuple[str, str], tuple[str, str]] = {}

    if system._dag is None:
        return interface_inputs, driver_map

    # 1) Collect interface inputs and their drivers from zero-delay edges
    for src, dst, data in system._dag.edges(data=True):
        src_port = data.get("src_port")
        dst_port = data.get("dst_port")
        key = (dst, dst_port)
        interface_inputs.append(key)
        driver_map[key] = (src, src_port)

    # 2) Remove duplicates and sort
    interface_inputs = sorted(set(interface_inputs))
    return interface_inputs, driver_map
