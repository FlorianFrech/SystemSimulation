from __future__ import annotations
from typing import Dict, Iterable, Optional
import colorsys
import hashlib

from graphviz import Digraph
from IPython.display import display

from ..system.system import System
from ..system.connection import Connection
from ..core.base import CoSimComponent
from ..core.port import PortSpec

def _auto_color_for_group(group_name: str, base_saturation: float = 0.35, base_lightness: float = 0.85) -> str:
    """
    Generate a soft pastel color (hex) deterministically from the group name.
    HSL -> RGB conversion ensures distinct hues for different names.
    """
    # Deterministic hash → 0..1 hue
    h = int(hashlib.md5(group_name.encode()).hexdigest(), 16) % 360
    hue = (h / 360.0)
    
    # Vary saturation and lightness slightly based on hash to create more variation
    hash_val = int(hashlib.md5(group_name.encode()).hexdigest(), 16)
    saturation = base_saturation + ((hash_val % 20) - 10) * 0.01  # ±0.1 variation
    lightness = base_lightness + ((hash_val >> 8) % 20 - 10) * 0.005  # ±0.05 variation
    
    r, g, b = colorsys.hls_to_rgb(hue, lightness, saturation)
    return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"

def _build_palette(system) -> dict[str, str]:
    """
    Build a palette for the current system:
      - known groups use predefined engineering colors
      - unknown groups get auto-generated pastel colors
    """
    base_palette = {
        "Reference": "#dbeafe",  # light blue
        "Sensors":   "#dcfce7",  # light green
        "Control":   "#fee2e2",  # light red
        "Actuator":  "#fef3c7",  # light yellow
        "Plant":     "#e5e7eb",  # light gray
    }

    palette = dict(base_palette)
    for group in system.groups:
        if group not in palette:
            palette[group] = _auto_color_for_group(group)
    return palette

def _record_label_for_component(comp: CoSimComponent, execution_idx: int = -1) -> str:
    """
    Build an HTML-like record label with explicit port anchors.
    Outputs with direct feedthrough are colored red.
    Inputs are stacked vertically on the left (if multiple), outputs on the right (if multiple).
    """
    ins = sorted(comp.input_specs.keys())
    outs = sorted(comp.output_specs.keys())

    # Build HTML table with three columns: inputs | name | outputs
    label = '<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4">'
    
    # Header row
    label += '<TR>'
    label += '<TD>in</TD>'
    label += '<TD>name</TD>'
    label += '<TD>out</TD>'
    label += '</TR>'
    
    # Content row
    label += '<TR>'
    
    # Input column (left side)
    if len(ins) == 0:
        label += '<TD></TD>'
    elif len(ins) == 1:
        # Single input - just one cell
        port_name = ins[0]
        label += f'<TD PORT="{port_name}">{port_name}</TD>'
    else:
        # Multiple inputs - nested table for vertical stacking
        label += '<TD><TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="2">'
        for port_name in ins:
            label += f'<TR><TD PORT="{port_name}">{port_name}</TD></TR>'
        label += '</TABLE></TD>'
    
    # Component name (middle) with execution order below
    badge = f"#{execution_idx}" if execution_idx >= 0 else ""
    label += f'<TD><B>{comp.name}</B><BR/><FONT POINT-SIZE="8">{badge}</FONT></TD>'
    
    # Output column (right side)
    if len(outs) == 0:
        label += '<TD></TD>'
    elif len(outs) == 1:
        # Single output - just one cell
        port_name = outs[0]
        has_feedthrough = port_name in comp.direct_feedthrough and comp.direct_feedthrough[port_name]
        if has_feedthrough:
            label += f'<TD PORT="{port_name}"><FONT COLOR="#ef4444"><B>{port_name}</B></FONT></TD>'
        else:
            label += f'<TD PORT="{port_name}">{port_name}</TD>'
    else:
        # Multiple outputs - nested table for vertical stacking
        label += '<TD><TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="2">'
        for port_name in outs:
            has_feedthrough = port_name in comp.direct_feedthrough and comp.direct_feedthrough[port_name]
            if has_feedthrough:
                label += f'<TR><TD PORT="{port_name}"><FONT COLOR="#ef4444"><B>{port_name}</B></FONT></TD></TR>'
            else:
                label += f'<TR><TD PORT="{port_name}">{port_name}</TD></TR>'
        label += '</TABLE></TD>'
    
    label += '</TR>'
    label += '</TABLE>'
    
    return f'<{label}>'

def _edge_unit_label(sys: System, conn: Connection) -> Optional[str]:
    if conn.unit:
        return f"[{conn.unit}]"
    
    # Unit should be consistent, but prefer dst if both defined
    dst_ps: Optional[PortSpec ] = None
    dst_comp = sys.components.get(conn.dst_comp)
    dst_ps = dst_comp.input_specs[conn.dst_port]
    unit = dst_ps.unit if dst_ps else None
    return unit

class SystemGraphVisualizer:
    def __init__(self, system: System):
        self.system = system

    def visualize(self, filename: str = "system_graph", format: str = "svg") -> None:
        self.dot = Digraph(
                    comment=f'System: {self.system.name}',
                    format=format,
                    engine='dot',
                    graph_attr={
                        "rankdir": "LR",
                        "splines": "true",
                        "pad": "0.5",
                        "nodesep": "0.8",
                        "ranksep": "0.8",
                        "esep": "0",
                        "sep": "0",
                        "fontsize": "18",
                        "fontname": "Helvetica-Bold",
                        "bgcolor": "white",
                        "margin": "0.2",
                        "labelloc": "t",
                        "label": self.system.name,
                        "compound": "true",
                        #"smoothType": "graph_dist"
                       },
                    node_attr={
                        "shape": "plaintext",
                        "style": "",
                        "fillcolor": "white",
                        #"color": "#3b82f6",
                        #"penwidth": "1.5",
                        "fontname": "Helvetica",
                        "fontsize": '10',
                        #"width": "1.5",
                        #"height": "0.7",
                        "margin": "0.05,0.05"
                          },
                    edge_attr={
                            "arrowsize": "0.7",
                            "penwidth": "1.2",
                            "color": "#111827",
                            "fontname": "Helvetica",
                            "fontsize": '10',
                            "labelfontcolor": "#374151",
                            "labelangle": "45",
                            "dir": "forward",
                            "arrowhead": "vee",
                            "arrowtail": "none",
                            #"style": "solid",
                            "minlen": "1.2"
                        },
                    )
        palette = _build_palette(self.system)
        
        # Add nodes grouped by their group attribute
        grouped_names = set()
        for group, comps in self.system.groups.items():
            with self.dot.subgraph(name=f"cluster_{group}") as c:
                c.attr(
                    label=group,
                    style="rounded",
                    color="#d1d5db",
                    bgcolor=palette.get(group, "white"),
                    fontname="Helvetica-Bold",
                    fontsize=f"11",
                    penwidth="2",
                    margin="12",
                )
                for comp in comps:
                    comp: CoSimComponent = comp if isinstance(comp, CoSimComponent) else self.system.components[str(comp)]
                    grouped_names.add(comp.name)
                    gen = self.system.execution_idx.get(comp.name, -1)
                    c.node(comp.name, label=_record_label_for_component(comp, gen))

        # Add any ungrouped components
        for comp_name, comp in self.system.components.items():
            if comp_name in grouped_names:
                continue
            gen = self.system.execution_idx.get(comp.name, -1)
            self.dot.node(comp.name, label=_record_label_for_component(comp, gen))

        # Add edges with port anchors and unit labels
        for conn in self.system.connections:
            src_name = conn.src_comp
            dst_name = conn.dst_comp
            src_anchor = f"{conn.src_port}:e"
            dst_anchor = f"{conn.dst_port}:w"
            
            unit_label = _edge_unit_label(self.system, conn)
            label = f"[{unit_label}]" if unit_label else ""

            style = "solid"
            color = "#111827"

            self.dot.edge(tail_name=src_name, 
                          head_name=dst_name,
                          label=label,
                          tailport=src_anchor,
                          headport=dst_anchor,
                          tailclip="true", headclip="true",
                          style=style,
                          color=color)

        # Render without auto-opening (view=False)
        self.dot.render(view=False)        
        display(self.dot)

    def save(self, filepath: str) -> None:
        """
        Save the current graph to a file.
        Supported formats depend on Graphviz installation (e.g., png, svg, pdf).
        """
        if not hasattr(self, 'dot'):
            raise RuntimeError("Graph has not been visualized yet. Call visualize() before saving.")
        self.dot.format = filepath.split('.')[-1]
        filepath = filepath.rsplit('.', 1)[0]
        self.dot.render(filename=filepath, view=False)
        