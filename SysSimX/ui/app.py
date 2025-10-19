# Framework/ui/app.py
from __future__ import annotations
import ipywidgets as W
from .state import AppState
from .views.model_selection import ModelSelectionView
from .views.fmu_export_view import FMUExportView
from .views.fmu_instantiator import FMUInstantiatorView

class UiApp(W.VBox):
    def __init__(self, state: AppState | None = None):
        super().__init__()
        self.state = state or AppState()
        self.sel = ModelSelectionView(self.state)
        self.exp = FMUExportView(self.state)
        self.ins = FMUInstantiatorView(self.state)

        steps = W.Accordion(children=[self.sel, self.exp, self.ins])
        steps.set_title(0, "Step 1 — Model Selection")
        steps.set_title(1, "Step 2 — Export to FMU")
        steps.set_title(2, "Step 3 — Instantiate FMU")
        steps.selected_index = 0

        self.children = [W.HTML("<h2>SysSimX — Simulation Workflow</h2>"), steps]
