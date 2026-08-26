"""Reusable ipywidgets monitoring panel for the controlled-pendulum components.

``FEMPendulum`` and ``MasterPendulum`` present the same monitoring UI. This
module owns the widget construction, styling, and HTML layout once, so both
components share a single :class:`PendulumMonitor`.

The panel observes a :class:`PendulumMonitoringState` (traitlets) through
``dlink``\\s. The simulation loop only writes plain state fields — it never
touches widgets directly — which keeps the solver decoupled from the view.
"""

from __future__ import annotations

from typing import Any

import ipywidgets as widgets
from IPython.display import display
from ipywidgets import HTML, HBox, Layout, VBox
from traitlets import Float, HasTraits, Unicode

from syssimx.core.port import PortType

# Port fields mirrored from a component's I/O ports into the observable state.
_PORT_FIELDS = ("tau", "theta", "omega", "alpha")

# State traits linked one-to-one to the same-named widget.
_LINK_FIELDS = ("time", "dt", "mode", "tau", "theta", "omega", "alpha")

_MAIN_HEADER_HTML = (
    "<h3 style='color:#1565c0; font-family:Inter, sans-serif; margin:15px 0 20px 0; "
    "text-align:center; font-weight:600; border-bottom:2px solid #1565c0; padding-bottom:10px;'>"
    "Pendulum Monitoring</h3>"
)

_SCENE_HEADER_HTML = (
    "<h3 style='color:#1565c0; font-family:Inter, sans-serif; margin:15px 0 20px 0; "
    "text-align:center; font-weight:600; border-bottom:2px solid #1565c0; padding-bottom:10px;'>"
    "Stress Visualization (N/m²)</h3>"
)

_GROUP_HEADER_STYLE = (
    "color:#424242; font-family:Inter, sans-serif; font-size:14px; "
    "font-weight:600; margin:15px 0 8px 0; padding:8px 12px; "
    "background:linear-gradient(to right, #f5f5f5, #ffffff); "
    "border-left:4px solid #1565c0; border-radius:4px;"
)


class PendulumMonitoringState(HasTraits):
    """Observable state of the pendulum for live monitoring."""

    # Simulation status
    time = Float(0.0)
    dt = Float(0.01)
    mode = Unicode("FEM")

    # Input signals
    tau = Float(0.0)

    # Output signals
    theta = Float(0.0)
    omega = Float(0.0)
    alpha = Float(0.0)

    # Optional: contact
    gap = Float(0.0)


class PendulumMonitor:
    """ipywidgets monitoring panel bound to a :class:`PendulumMonitoringState`.

    Args:
        input_specs: Mapping of input port name to ``PortSpec``.
        output_specs: Mapping of output port name to ``PortSpec``.
        t_end: Simulation end time, shown in the time-widget description.
        tau: Initial macro step, shown in the dt widget.
        mode: Initial simulation mode label.
        with_contact: When True, add a minimum-gap widget and link.
        state: Optional shared state object; a new one is created if omitted.
    """

    def __init__(
        self,
        input_specs: dict[str, Any],
        output_specs: dict[str, Any],
        *,
        t_end: float,
        tau: float,
        mode: str = "",
        with_contact: bool = False,
        state: PendulumMonitoringState | None = None,
    ):
        self.input_specs = input_specs
        self.output_specs = output_specs
        self._t_end = t_end
        self._tau = tau
        self._with_contact = with_contact

        self.state = state if state is not None else PendulumMonitoringState()
        if mode:
            self.state.mode = mode

        self.widgets: dict[str, Any] = {}
        self._links: list = []

        self._build_widgets()
        self._format_widgets()
        self._link_state()
        self._build_layout()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------
    def _build_widgets(self) -> None:
        for name, spec in self.input_specs.items():
            if spec.type == PortType.REAL:
                self.widgets[name] = widgets.FloatText(
                    value=0.0, description=f"{name} ({spec.unit}):", step=0.01, disabled=True
                )
        for name, spec in self.output_specs.items():
            if spec.type == PortType.REAL:
                self.widgets[name] = widgets.FloatText(
                    value=0.0, description=f"{name} ({spec.unit}):", step=0.01, disabled=True
                )
        self.widgets["time"] = widgets.FloatText(
            value=0, description=f"Time: t / {self._t_end} s", step=0.001, disabled=True
        )
        self.widgets["dt"] = widgets.FloatText(
            value=self._tau, description="Time Step: dt in s", step=0.0001, disabled=True
        )
        self.widgets["mode"] = widgets.Text(
            value=self.state.mode, description="Simulation Mode:", disabled=True
        )
        if self._with_contact:
            self.widgets["gap"] = widgets.FloatText(
                value=0.0, description="Min. Gap in m", step=0.0001, disabled=True
            )

    def _format_widgets(self) -> None:
        for w in self.widgets.values():
            w.layout.width = "300px"
            w.layout.margin = "5px"
            w.style.description_width = "150px"
            w.readout_format = ".5g"

            # Professional color scheme
            w.style.font_family = "Inter"
            w.style.font_size = "13px"
            w.style.font_weight = "500"

            # Modern input field styling
            w.style.background = "white"
            w.style.border = "1px solid #e0e0e0"
            w.style.border_radius = "4px"
            w.style.padding = "8px 12px"

            # Text styling
            w.style.color = "#424242"
            w.style.description_color = "#757575"

    def _link_state(self) -> None:
        """Bind state traits to their widgets via one-directional dlinks."""
        for link in self._links:
            link.unlink()
        self._links.clear()

        link_fields = list(_LINK_FIELDS)
        if self._with_contact:
            link_fields.append("gap")

        for field in link_fields:
            if field in self.widgets:
                self._links.append(
                    widgets.dlink((self.state, field), (self.widgets[field], "value"))
                )

    def _build_layout(self) -> None:
        main_header = HTML(_MAIN_HEADER_HTML)
        input_header = HTML(f"<div style='{_GROUP_HEADER_STYLE} text-align:center;'>Input Signals</div>")
        output_header = HTML(f"<div style='{_GROUP_HEADER_STYLE} text-align:center;'>Output Signals</div>")
        simulation_header = HTML(
            f"<div style='{_GROUP_HEADER_STYLE} text-align:center;'>Simulation Status</div>"
        )

        input_widgets = [self.widgets[name] for name in self.input_specs if name in self.widgets]
        output_widgets = [self.widgets[name] for name in self.output_specs if name in self.widgets]
        simulation_widgets = [self.widgets["time"], self.widgets["dt"], self.widgets["mode"]]
        if self._with_contact:
            simulation_widgets.append(self.widgets["gap"])

        input_box = VBox([input_header] + input_widgets, layout=Layout(margin="0 0 20px 10px"))
        output_box = VBox([output_header] + output_widgets, layout=Layout(margin="0 0 20px 10px"))
        simulation_box = VBox(
            [simulation_header] + simulation_widgets, layout=Layout(margin="0 0 20px 10px")
        )

        widget_box = HBox(
            [simulation_box, input_box, output_box], layout=Layout(justify_content="space-between")
        )

        self.layout = VBox(
            [main_header, widget_box],
            layout=Layout(
                padding="20px",
                border="1px solid #e0e0e0",
                border_radius="8px",
                background="#fafafa",
                width="fit-content",
                margin="0 auto",
                height="auto",
                box_shadow="0 4px 8px rgba(0, 0, 0, 0.1)",
            ),
        )
        self.scene_header = HTML(_SCENE_HEADER_HTML)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def display(self) -> None:
        """Render the monitoring panel."""
        display(self.layout)

    def sync_from_ports(self, inputs: dict[str, Any], outputs: dict[str, Any]) -> None:
        """Mirror current REAL port values into the observable state.

        Output ports take precedence over input ports for a given field.
        Pint quantities are reduced to their magnitude.
        """
        for field in _PORT_FIELDS:
            port = outputs.get(field) or inputs.get(field)
            if port is None:
                continue
            value = port.get()
            if value is None:
                continue
            magnitude = value.magnitude if hasattr(value, "magnitude") else value
            setattr(self.state, field, float(magnitude))

    def close(self) -> None:
        """Release all widget links."""
        for link in self._links:
            link.unlink()
        self._links.clear()
