from typing import Dict, List, Callable, Optional, Any
from dataclasses import dataclass, field
import ipywidgets as widgets
from ipywidgets import Layout, HBox, VBox, HTML
from IPython.display import display

from ..core.port import PortType
# from ..system.system import System
# from ..system.connection import Connection

@dataclass
class MonitorableState:
    """
    Defines a state variable of a simulation that can be monitored in the UI.
    """
    name: str
    component_name: str
    getter: Callable[[], Any]
    type: PortType
    unit: Optional[str] = None
    description: Optional[str] = None
    fromat_spec: str = ".4f"

class SimulationMonitor:
    """
    Central monitoring system for live simulation outputs.
    Manages display of connection states and internal component states.
    """

    def __init__(self, system: System):
        self.system = system
        self._connection_monitors: Dict[str, widgets.Text] = {}
        self._state_monitors: Dict[str, widgets.Text] = {}
        self._custom_states: list[MonitorableState] = []
        self._widget_container: Optional[VBox] = None

    def add_connection_monitor(self, connection: Connection) -> None:
        """
        Monitor a specific connection's current value
        """
        key = f"{connection.src_comp}.{connection.src_port} -> {connection.dst_comp}.{connection.dst_port}"
        src_comp = self.system.components[connection.src_comp]
        src_port_spec = src_comp.output_specs[connection.src_port]
        
        unit = src_port_spec.unit
        desc = key
        if unit:
            desc += f" ({unit})"
        
        widget = widgets.Text(
            value = "",
            description = desc,
            disabled = True,
            layout = Layout(width='400px')
        )

        self._connection_monitors[key] = widget

    def add_component_state(self, state: MonitorableState) -> None:
        """
        Add a custom internal state from a component.
        """
        self._custom_states.append(state)
        key = f"{state.component_name}.{state.name}"
        desc = state.description or state.name
        if state.unit:
            desc += f" {state.unit}"
        
        widget = widgets.Text(
            value = "",
            description = desc,
            disabled = True,
            layout = Layout(width="400px")
        )

        self._state_monitors[key] = widget

    def setup_display(self) -> None:
        """
        Create and display the monitoring dashboard.
        """ 
        header = HTML("<h3 style='color:#1565c0; text-align:center;'>System Monitor</h3>")
        widget_list = []

        # Time widget
        w_time = widgets.FloatText(
            value = 0.0,
            description = "t in (s)",
            disabled = True
        )
        widget_list.append(w_time)

        # Connection Monitors
        if self._connection_monitors:
            conn_header = HTML("<h4>Connection States</h4>")
            widget_list.append(conn_header)
            widget_list.extend(self._connection_monitors.values())

        # State Monitors
        if self._state_monitors:
            state_header = HTML("<h4>Component States</h4>")
            widget_list.append(state_header)
            widget_list.extend(self._state_monitors.values())

        for w in widget_list:
            w.layout.width = '350px'
            w.layout.margin = '8px 0px 8px 0px'
            w.layout.align_self = 'center'
            w.layout.display = 'flex'
            w.layout.flex_direction = 'column'
            w.style.description_width = '300px'
            w.style.font_weight = 'bold'
            w.style.font_size = '16px'
            w.style.background = '#f5f7fa'
            w.style.border = '1px solid #cfd8dc'
            w.style.border_radius = '8px'
            w.style.padding = '6px 12px'
            w.style.color = '#263238'
            w.style.text_align = 'right'
        
        self._widget_container = VBox([header] + widget_list)
        display(self._widget_container)

    def update(self, t: float) -> None:
        """
        Update all monitored values (called during simulation step).
        """
        # Update all connection monitors
        for connection in self.system.connections:
            key = f"{connection.src_comp}.{connection.src_port} -> {connection.dst_comp}.{connection.dst_port}"
            if key in self._connection_monitors:
                value = self.system.components[connection.src_comp].outputs[connection.src_port].get()
                if value is not None:
                    display_val = value.magnitude if hasattr(value, 'magnitude') else value
                    display_val = f"{display_val}"
                    self._connection_monitors[key].value = display_val
        
         # Update custom state monitors
        for state in self._custom_states:
            key = f"{state.component_name}.{state.name}"
            if key in self._state_monitors:
                try:
                    value = state.getter()
                    display_val = value.magnitude if hasattr(value, 'magnitude') else value
                    display_val = f"{display_val}"
                    self._state_monitors[key].value = display_val
                except Exception as e:
                    print(f"Error updating {key}: {e}")       