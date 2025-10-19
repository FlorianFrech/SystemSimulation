# Framework/ui/views/model_selection.py
from __future__ import annotations
from pathlib import Path
import ipywidgets as W
from ..state import AppState
from ..widgets.file_chooser import ModelicaSelector
from ..widgets.status_bar import StatusBar

class ModelSelectionView(W.VBox):
    def __init__(self, state: AppState):
        super().__init__()
        self.state: AppState = state
        self.status: StatusBar = StatusBar()
        self.sel: ModelicaSelector = ModelicaSelector(self._on_added, self._on_removed)
        self.children = [W.HTML("<h3>Step 1 — Model Selection</h3>"), self.sel, self.status]
        self._refresh()

    def _on_added(self, p: Path):
        if p in self.state.selected_models:
            self.status.set("Already selected."); return
        self.state.selected_models.add(p)
        self._refresh()
        self.status.set(f"Added: {p.name}")

    def _on_removed(self, paths: list[Path]):
        for p in paths:
            self.state.selected_models.discard(p)
        self._refresh()
        self.status.set("Selection updated.")

    def _refresh(self):
        self.sel.set_list(sorted(self.state.selected_models))
        # preview last added (optional)
        if self.state.selected_models:
            p = sorted(self.state.selected_models)[-1]
            try:
                txt = Path(p).read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                txt = f"[Error reading {p}]: {e}"
            self.sel.set_preview(txt)
        else:
            self.sel.set_preview("")
