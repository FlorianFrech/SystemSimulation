"""Graphviz-based system graph visualization utilities.

This module renders SysSimX systems as Graphviz directed graphs with:
  - grouped component clusters,
  - port-aware record labels,
  - event connections styled distinctly,
  - algebraic loop connections highlighted, and
  - optional unit labels on edges.
"""

from __future__ import annotations

import colorsys
import hashlib
from collections.abc import Iterable

from graphviz import Digraph
from IPython.display import display

from ..core.base import CoSimComponent
from ..core.port import PortSpec, PortType
from ..system.connection import Connection
from ..system.graph import collect_active_outputs
from ..system.system import System

# -----------------------------------------------------------------------------
# Styling constants
# -----------------------------------------------------------------------------
COLOR_EDGE = "#111827"
COLOR_EDGE_LABEL = "#374151"
COLOR_EVENT = "#0b84ff"
COLOR_FEEDTHROUGH = "#ef4444"
COLOR_LEGEND_BORDER = "#d1d5db"
COLOR_LEGEND_BG = "#f9fafb"

FONT_DEFAULT = "Helvetica"
FONT_BOLD = "Helvetica-Bold"

DEFAULT_GROUP_PALETTE = {
    "Reference": "#dbeafe",  # light blue
    "Sensors": "#dcfce7",  # light green
    "Control": "#fee2e2",  # light red
    "Actuator": "#fef3c7",  # light yellow
    "Plant": "#e5e7eb",  # light gray
}


# ----------------------------------------------------------------------------
# Private helper functions
# ----------------------------------------------------------------------------
def _auto_color_for_group(
    group_name: str, base_saturation: float = 0.35, base_lightness: float = 0.85
) -> str:
    """Generate a deterministic pastel color for a group name.

    Args:
        group_name: Name of the group to color.
        base_saturation: Base saturation for the generated color.
        base_lightness: Base lightness for the generated color.

    Returns:
        Hex color string (e.g., "#aabbcc").
    """
    hash_val = int(hashlib.md5(group_name.encode()).hexdigest(), 16)
    hue = (hash_val % 360) / 360.0
    saturation = base_saturation + ((hash_val % 20) - 10) * 0.01
    lightness = base_lightness + (((hash_val >> 8) % 20) - 10) * 0.005
    r, g, b = colorsys.hls_to_rgb(hue, lightness, saturation)
    return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"


def _build_palette(system: System) -> dict[str, str]:
    """Build a group color palette for the system.

    Args:
        system: System whose groups are inspected.

    Returns:
        Mapping of group name to hex color.
    """
    palette = dict(DEFAULT_GROUP_PALETTE)
    for group in system.groups:
        if group not in palette:
            palette[group] = _auto_color_for_group(group)
    return palette


def _is_event_port(port: PortSpec) -> bool:
    """Return True if a port is an event-type port.

    Args:
        port: Port specification to inspect.

    Returns:
        True if the port is not a real-valued port.
    """
    return port.type != PortType.REAL


def _format_port_label(port_name: str, color: str | None = None) -> str:
    """Format a port label with optional color emphasis.

    Args:
        port_name: Port name to render.
        color: Optional hex color for the label.

    Returns:
        HTML fragment for the port label.
    """
    if color:
        return f'<FONT COLOR="{color}"><B>{port_name}</B></FONT>'
    return port_name


def _build_ports_column(
    port_names: Iterable[str],
    event_ports: set[str],
    feedthrough_ports: set[str] | None = None,
) -> str:
    """Build an HTML table cell for a port column.

    Args:
        port_names: Iterable of port names in display order.
        event_ports: Set of event port names.
        feedthrough_ports: Optional set of direct-feedthrough output ports.

    Returns:
        HTML fragment for the column cell.
    """
    port_list = list(port_names)
    feedthrough_ports = feedthrough_ports or set()

    def label_for(name: str) -> str:
        if name in event_ports:
            return _format_port_label(name, COLOR_EVENT)
        if name in feedthrough_ports:
            return _format_port_label(name, COLOR_FEEDTHROUGH)
        return _format_port_label(name)

    if not port_list:
        return "<TD></TD>"
    if len(port_list) == 1:
        name = port_list[0]
        return f'<TD PORT="{name}">{label_for(name)}</TD>'

    rows = []
    for name in port_list:
        rows.append(f'<TR><TD PORT="{name}">{label_for(name)}</TD></TR>')
    rows_str = "".join(rows)
    return (
        '<TD><TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="2">'
        f"{rows_str}</TABLE></TD>"
    )


def _record_label_for_component(comp: CoSimComponent, execution_idx: int = -1) -> str:
    """Build an HTML-like record label for a component.

    The label includes input and output port columns with explicit anchors.
    Output ports with direct feedthrough are highlighted in red; event ports
    are highlighted in blue.

    Args:
        comp: Component to render.
        execution_idx: Optional execution order index to display.

    Returns:
        Graphviz HTML-like label string.
    """
    inputs = sorted(comp.input_specs.keys())
    outputs = sorted(comp.output_specs.keys())

    event_inputs = {p.name for p in comp.input_specs.values() if _is_event_port(p)}
    event_outputs = {p.name for p in comp.output_specs.values() if _is_event_port(p)}
    feedthrough_outputs = {name for name, deps in comp.direct_feedthrough.items() if deps}

    header = "<TR><TD>in</TD><TD>name</TD><TD>out</TD></TR>"
    badge = f"#{execution_idx}" if execution_idx >= 0 else ""
    name_cell = f'<TD><B>{comp.name}</B><BR/><FONT POINT-SIZE="8">{badge}</FONT></TD>'
    inputs_cell = _build_ports_column(inputs, event_inputs)
    outputs_cell = _build_ports_column(outputs, event_outputs, feedthrough_outputs)

    label = (
        '<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4">'
        f"{header}<TR>{inputs_cell}{name_cell}{outputs_cell}</TR></TABLE>"
    )
    return f"<{label}>"


def _edge_unit_label(system: System, conn: Connection) -> str | None:
    """Return unit label from the destination port specification.

    Args:
        system: System containing the destination component.
        conn: Connection whose destination port is inspected.

    Returns:
        Unit label string if present, otherwise None.
    """
    dst_comp = system.components.get(conn.dst_comp)
    if dst_comp is None:
        return None
    dst_ps = dst_comp.input_specs.get(conn.dst_port)
    if dst_ps and dst_ps.unit:
        return f"{dst_ps.unit}"
    return None


def _is_zero_delay_connection(
    system: System, conn: Connection, active_outputs: dict[str, set[str]]
) -> bool:
    """Check if a connection participates in zero-delay direct feedthrough.

    Args:
        system: System containing the components.
        conn: Connection to evaluate.
        active_outputs: Mapping of components to output ports used by connections.

    Returns:
        True if this connection contributes to the zero-delay dependency graph.
    """
    dst_comp = system.components.get(conn.dst_comp)
    if dst_comp is None:
        return False
    relevant_outputs = active_outputs.get(conn.dst_comp, set())
    for out_port, deps in dst_comp.direct_feedthrough.items():
        if out_port not in relevant_outputs:
            continue
        if deps and conn.dst_port in deps:
            return True
    return False


def _is_direct_feedthrough_output(comp: CoSimComponent, port_name: str) -> bool:
    """Return True if the given output port is direct-feedthrough.

    Args:
        comp: Component to inspect.
        port_name: Output port name on the component.

    Returns:
        True if the output port has direct-feedthrough dependencies.
    """
    deps = comp.direct_feedthrough.get(port_name)
    return bool(deps)


def _is_direct_feedthrough_input(comp: CoSimComponent, port_name: str) -> bool:
    """Return True if the given input port feeds any direct-feedthrough output.

    Args:
        comp: Component to inspect.
        port_name: Input port name on the component.

    Returns:
        True if the input port appears in any direct-feedthrough dependency list.
    """
    for deps in comp.direct_feedthrough.values():
        if deps and port_name in deps:
            return True
    return False


def _build_loop_index(system: System) -> dict[str, int]:
    """Build a component-to-loop index mapping.

    Args:
        system: System containing detected algebraic loops.

    Returns:
        Mapping from component name to algebraic loop index.
    """
    loop_index: dict[str, int] = {}
    for idx, loop in enumerate(system.algebraic_loops):
        for name in loop:
            loop_index[name] = idx
    return loop_index


def _legend_label() -> str:
    """Return the HTML label used for the legend node.

    Returns:
        Graphviz HTML-like label string.
    """
    return """<
    <TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="0">
        <TR>
            <TD ALIGN="LEFT" VALIGN="TOP">
                <TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="1">
                    <TR><TD ALIGN="LEFT"><FONT POINT-SIZE="9"><B>Edges:</B></FONT></TD></TR>
                    <TR><TD ALIGN="LEFT"><FONT POINT-SIZE="8">───&gt; Data flow</FONT></TD></TR>
                    <TR><TD ALIGN="LEFT"><FONT POINT-SIZE="8" COLOR="#ef4444">───&gt; Algebraic loop</FONT></TD></TR>
                    <TR><TD ALIGN="LEFT"><FONT POINT-SIZE="8" COLOR="#0b84ff">┄┄┄o Event connection</FONT></TD></TR>
                </TABLE>
            </TD>
            <TD WIDTH="6"></TD>
            <TD ALIGN="LEFT" VALIGN="TOP">
                <TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="1">
                    <TR><TD ALIGN="LEFT"><FONT POINT-SIZE="9"><B>Ports:</B></FONT></TD></TR>
                    <TR><TD ALIGN="LEFT"><FONT POINT-SIZE="8" COLOR="#ef4444"><B>red</B></FONT> Direct feedthrough</TD></TR>
                    <TR><TD ALIGN="LEFT"><FONT POINT-SIZE="8" COLOR="#0b84ff"><B>blue</B></FONT> Event port</TD></TR>
                </TABLE>
            </TD>
        </TR>
    </TABLE>
    >"""


# ----------------------------------------------------------------------------
# SystemGraphVisualizer class
# ----------------------------------------------------------------------------
class SystemGraphVisualizer:
    """Render a System as a Graphviz directed graph."""

    def __init__(self, system: System):
        """Initialize the visualizer.

        Args:
            system: System instance to visualize.
        """
        self.system = system
        self.dot: Digraph | None = None
        self._grouped_names: set[str] = set()

    def visualize(self, filename: str = "system_graph", format: str = "svg") -> None:
        """Build and render a Graphviz system graph.

        This method constructs a new Graphviz Digraph, adds component nodes,
        connection edges, and renders to disk without opening a viewer.

        Args:
            filename: Output filename; an extension is optional and will be stripped.
            format: Graphviz output format (e.g., "svg", "png").
        """
        self.dot = Digraph(
            comment=f"System: {self.system.name}",
            format=format,
            engine="dot",
            graph_attr={
                "rankdir": "LR",
                "splines": "true",
                "pad": "0.5",
                "nodesep": "0.8",
                "ranksep": "0.8",
                "esep": "0",
                "sep": "0",
                "fontsize": "18",
                "fontname": FONT_BOLD,
                "bgcolor": "white",
                "margin": "0.2",
                "labelloc": "t",
                "label": self.system.name,
                "compound": "true",
            },
            node_attr={
                "shape": "plaintext",
                "style": "",
                "fillcolor": "white",
                "fontname": FONT_DEFAULT,
                "fontsize": "10",
                "margin": "0.05,0.05",
            },
            edge_attr={
                "arrowsize": "0.7",
                "penwidth": "1.2",
                "color": COLOR_EDGE,
                "fontname": FONT_DEFAULT,
                "fontsize": "10",
                "labelfontcolor": COLOR_EDGE_LABEL,
                "labelangle": "45",
                "dir": "forward",
                "arrowhead": "vee",
                "arrowtail": "none",
                "minlen": "1.2",
            },
        )

        if self.system.connections and self.system._dag.number_of_nodes() == 0:
            self.system.build_graphs()
        active_outputs = collect_active_outputs(self.system)
        loop_index = _build_loop_index(self.system)
        palette = _build_palette(self.system)

        self._add_legend()
        self._add_grouped_components(palette)
        self._add_ungrouped_components()
        self._add_data_edges(active_outputs, loop_index)
        self._add_event_edges()

        render_name = filename.rsplit(".", 1)[0]
        self.dot.render(filename=render_name, view=False)
        display(self.dot)

    def save(self, filepath: str) -> None:
        """Save the current graph to a file.

        Args:
            filepath: Output path with extension (e.g., "graph.svg").

        Raises:
            RuntimeError: If visualize() was not called before saving.
        """
        if not self.dot:
            raise RuntimeError("Graph has not been visualized yet. Call visualize() before saving.")
        self.dot.format = filepath.split(".")[-1]
        filepath = filepath.rsplit(".", 1)[0]
        self.dot.render(filename=filepath, view=False, cleanup=True)

    def _add_legend(self) -> None:
        """Add a legend subgraph to the current Graphviz graph."""
        if not self.dot:
            return
        with self.dot.subgraph(name="cluster_legend") as legend:
            legend.attr(
                label="Legend",
                style="rounded",
                color=COLOR_LEGEND_BORDER,
                bgcolor=COLOR_LEGEND_BG,
                fontname=FONT_BOLD,
                fontsize="10",
                penwidth="1.5",
                margin="8",
                rank="sink",
            )
            legend.node("legend_node", label=_legend_label(), shape="plaintext", fontsize="8")

    def _add_grouped_components(self, palette: dict[str, str]) -> None:
        """Add grouped components as clustered subgraphs.

        Args:
            palette: Group name to color mapping.
        """
        if not self.dot:
            return
        grouped_names: set[str] = set()
        for group, comps in self.system.groups.items():
            with self.dot.subgraph(name=f"cluster_{group}") as cluster:
                cluster.attr(
                    label=group,
                    style="rounded",
                    color=COLOR_LEGEND_BORDER,
                    bgcolor=palette.get(group, "white"),
                    fontname=FONT_BOLD,
                    fontsize="11",
                    penwidth="2",
                    margin="12",
                )
                for comp in comps:
                    comp = (
                        comp
                        if isinstance(comp, CoSimComponent)
                        else self.system.components[str(comp)]
                    )
                    grouped_names.add(comp.name)
                    gen = self.system.execution_idx.get(comp.name, -1)
                    cluster.node(comp.name, label=_record_label_for_component(comp, gen))

        self._grouped_names = grouped_names

    def _add_ungrouped_components(self) -> None:
        """Add any components that were not placed in a group cluster."""
        if not self.dot:
            return
        grouped_names = self._grouped_names
        for comp_name, comp in self.system.components.items():
            if comp_name in grouped_names:
                continue
            gen = self.system.execution_idx.get(comp.name, -1)
            self.dot.node(comp.name, label=_record_label_for_component(comp, gen))

    def _add_data_edges(
        self, active_outputs: dict[str, set[str]], loop_index: dict[str, int]
    ) -> None:
        """Add standard data connection edges.

        Args:
            active_outputs: Mapping of component names to active output ports.
            loop_index: Mapping of component names to algebraic loop index.
        """
        if not self.dot:
            return
        for conn in self.system.connections:
            src_anchor = f"{conn.src_port}:e"
            dst_anchor = f"{conn.dst_port}:w"
            label = _edge_unit_label(self.system, conn)
            label = f"[{label}]" if label else ""

            color = COLOR_EDGE
            penwidth = "1.2"
            src_loop = loop_index.get(conn.src_comp)
            dst_loop = loop_index.get(conn.dst_comp)
            src_comp = self.system.components.get(conn.src_comp)
            dst_comp = self.system.components.get(conn.dst_comp)
            if (
                src_loop is not None
                and src_loop == dst_loop
                and src_comp is not None
                and dst_comp is not None
                and _is_direct_feedthrough_output(src_comp, conn.src_port)
                and _is_direct_feedthrough_input(dst_comp, conn.dst_port)
                and _is_zero_delay_connection(self.system, conn, active_outputs)
            ):
                color = COLOR_FEEDTHROUGH
                penwidth = "2.0"

            self.dot.edge(
                tail_name=conn.src_comp,
                head_name=conn.dst_comp,
                label=label,
                tailport=src_anchor,
                headport=dst_anchor,
                tailclip="true",
                headclip="true",
                style="solid",
                color=color,
                penwidth=penwidth,
            )

    def _add_event_edges(self) -> None:
        """Add event connection edges with a distinct style."""
        if not self.dot:
            return
        for event_conn in self.system.event_connections:
            src_anchor = f"{event_conn.src_port}:e"
            dst_anchor = f"{event_conn.dst_port}:w"
            self.dot.edge(
                tail_name=event_conn.src_comp,
                head_name=event_conn.dst_comp,
                label="",
                tailport=src_anchor,
                headport=dst_anchor,
                tailclip="true",
                headclip="true",
                style="dashed",
                color=COLOR_EVENT,
                penwidth="2.0",
                arrowhead="odot",
                fontcolor=COLOR_EVENT,
            )
