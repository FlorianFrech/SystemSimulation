# Framework/ui/views/fmu_export_view.py
from __future__ import annotations
import ipywidgets as W
from ..state import AppState
from ..services.fmu_export import export_models_to_fmus
from ..widgets.dest_selector import DestinationSelector
from ..widgets.status_bar import StatusBar

class FMUExportView(W.VBox):
    def __init__(self, state: AppState):
        super().__init__()
        self.state = state
        self.dest = DestinationSelector(self._on_export)
        self.status = StatusBar()
        self.dest.dir.register_callback(lambda *_: self.dest.refresh_preview())
        self.dest.sub.observe(lambda ch: self.dest.refresh_preview() if ch["name"]=="value" else None, names="value")
        self.children = [W.HTML("<h3>Step 2 — Export to FMU</h3>"), self.dest, self.status]
        self.dest.refresh_preview()

    def _on_export(self):
        # copy UI values into state
        self.state.export_base = self.dest.compute_path().parent if self.dest.sub.value.strip() else self.dest.compute_path()
        self.state.export_subfolder = self.dest.sub.value.strip()
        self.state.create_missing_dirs = self.dest.create.value
        if not self.state.selected_models:
            self.status.set("No models selected.", ok=False); return
        try:
            export_dir, outputs = export_models_to_fmus(self.state)
            self.status.set(f"Exported {len(outputs)} FMU(s) to {export_dir}")
        except Exception as e:
            self.status.set(f"Export failed: {e}", ok=False)
