from graphviz import Digraph
from IPython.display import display
from ..system.system import System, Connection


# def _set_up_label(self) -> None:
#         """
#         Create a label for visualization in the system graph.
#         """
#         in_str = "{ " + " | ".join(f"<{name}> {name}" for name in self.inputs.keys()) + " }"
#         out_str = "{ " + " | ".join(f"<{name}> {name}" for name in self.outputs.keys()) + " }"
#         if in_str == "{  }":
#             in_str = ""
#         if out_str == "{  }":
#             out_str = ""
#         if in_str and out_str:
#             self.label = f"{{ {in_str} | {self.name} | {out_str} }}"
#         elif in_str:
#             self.label = f"{{ {in_str} | {self.name} }}"
#         elif out_str:
#             self.label = f"{{ {self.name} | {out_str} }}"
#         else:
#             self.label = f"{self.name}"

class SystemGraphVisualizer:
    def __init__(self, system: System):
        self.system = system

    def visualize(self, filename: str = "system_graph", format: str = "png") -> None:
        self.dot = Digraph(comment=f'System: {self.system.name}', format=format, engine='dot',
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
        self.palette = {
            "Reference": "#dbeafe",   
            "Sensors": "#dcfce7",     
            "Control": "#fee2e2",     
            "Actuator": "#fef3c7",   
            "Plant": "#e5e7eb",       
        }

        for group, nodes in self.system.groups.items():
            with self.dot.subgraph(name=f"cluster_{group}") as c:
                c.attr(
                    label=group,
                    style="rounded",
                    color="#9ca3af", 
                    bgcolor=self.palette.get(group, "white"),
                    fontname="Helvetica",
                    fontsize=f"10",
                )
                for mod in nodes:
                    gen = self.system.execution_idx[mod.name]
                    badge = f"#{gen}"
                    c.node(mod.name, label=mod.label, xlabel=badge)

        for conn in self.system.connections:
            label = f"[{conn.src_port.unit}]"
            if conn.delay > 0:
                label += f" delay({conn.delay})"

            src_port = f"{conn.src_port.name}:e"
            dst_port = f"{conn.dst_port.name}:w"

            edge_style = {
                "style": "dashed" if conn.delay > 0 else "solid",
                "color": "#6b7280" if conn.delay > 0 else "#111827",
            }

            self.dot.edge(tail_name=conn.src_comp.name, head_name=conn.dst_comp.name,
                    label=label,
                    tailport=src_port,
                    headport=dst_port,
                    tailclip="true", headclip="true",
                    **edge_style)

        # Render without auto-opening (view=False)
        self.dot.render(view=False)        
        display(self.dot)

        