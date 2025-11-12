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

def _auto_color_for_group(group_name: str, base_saturation: float = 0.25, base_lightness: float = 0.90) -> str:
    """
    Generate a soft pastel color (hex) deterministically from the group name.
    HSL -> RGB conversion ensures distinct hues for different names.
    """
    # Deterministic hash → 0..1 hue
    h = int(hashlib.md5(group_name.encode()).hexdigest(), 16) % 360
    hue = (h / 360.0)
    r, g, b = colorsys.hls_to_rgb(hue, base_lightness, base_saturation)
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



def _record_label_for_component(comp: CoSimComponent) -> str:
    """
    Build an record-label with explicit port anchors:
    { { <in1> in1 | <in2> in2 } | comp_name | { <out1> out1 | <out2> out2 } }
    """
    ins = sorted(comp.input_specs.keys())
    outs = sorted(comp.output_specs.keys())

    def _ports_to_record(port_names: Iterable[str]) -> str:
        if not port_names:
            return ""
        return "{ " + " | ".join(f"<{name}> {name}" for name in port_names) + " }"
    
    in_rec = _ports_to_record(ins)
    out_rec = _ports_to_record(outs)

    # 3 cases: both sides, only left, only right
    if in_rec and out_rec:
        return f"{{ {in_rec} | {comp.name} | {out_rec} }}"
    elif in_rec:
        return f"{{ {in_rec} | {comp.name} }}"
    elif out_rec:
        return f"{{ {comp.name} | {out_rec} }}"
    else:
        return f"{comp.name}"

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
                        "pad": "0.75",
                        "nodesep": "1",
                        "ranksep": "0.75",
                        "esep": "0",
                        "sep": "0",
                        "fontsize": "16",
                        "fontname": "Helvetica",
                        "bgcolor": "white",
                        "margin": "0.2",
                        "labelloc": "t",
                        "label": self.system.name,
                        "compound": "true",
                        "smoothType": "graph_dist"
                       },
                    node_attr={
                        "shape": "record",
                        "style": "rounded,filled",
                        "fillcolor": "white",
                        "color": "#3b82f6",
                        "penwidth": "1.5",
                        "fontname": "Helvetica",
                        "fontsize": '10',
                        "width": "1.5",
                        "height": "0.7",
                        "margin": "0.12,0.1"
                          },
                    edge_attr={
                            "arrowsize": "0.5",
                            "penwidth": "1",
                            "color": "#111827",
                            "fontname": "Helvetica",
                            "fontsize": '10',
                            "labelfontcolor": "#374151",
                            "labelangle": "45",
                            "dir": "forward",
                            "arrowhead": "open",
                            "arrowtail": "none",
                            "style": "solid",
                            "minlen": "1.4"
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
                    color="#9ca3af", 
                    bgcolor=palette.get(group, "white"),
                    fontname="Helvetica",
                    fontsize=f"10",
                )
                for comp in comps:
                    comp: CoSimComponent = comp if isinstance(comp, CoSimComponent) else self.system.components[str(comp)]
                    grouped_names.add(comp.name)
                    gen = self.system.execution_idx.get(comp.name, -1)
                    badge = f"#{gen}"
                    c.node(comp.name, label=_record_label_for_component(comp), xlabel=badge)

        # Add any ungrouped components
        for comp_name, comp in self.system.components.items():
            if comp_name in grouped_names:
                continue
            gen = self.system.execution_idx.get(comp.name, -1)
            badge = f"#{gen}"
            self.dot.node(comp.name, label=_record_label_for_component(comp), xlabel=badge)

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
        