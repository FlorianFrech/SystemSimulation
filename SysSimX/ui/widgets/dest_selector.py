# Framework/ui/widgets/dest_selector.py
from __future__ import annotations
from pathlib import Path
import ipywidgets as W
from ipyfilechooser import FileChooser

class DestinationSelector(W.VBox):
    def __init__(self, on_export_clicked):
        super().__init__()
        self.dir = FileChooser(str(Path.cwd()), title="Export directory", show_hidden=False, select_default=True, use_dir_icons=True)
        self.dir.show_only_dirs = True
        self.sub = W.Text(value="exported_fmus", description="Subfolder:", layout=W.Layout(width="60%"))
        self.create = W.Checkbox(value=True, description="Create if missing")
        self.preview = W.HTML()
        self.btn_export = W.Button(description="Export to FMU", icon="download", button_style="info")

        self.btn_export.on_click(lambda _: on_export_clicked())
        self.children = [self.dir, W.HBox([self.sub, self.create]), self.preview, self.btn_export]

    def compute_path(self) -> Path:
        base = self.dir.selected or self.dir._select.value or self.dir.getcwd()
        p = Path(str(base)).expanduser().resolve()
        if self.sub.value.strip():
            p = (p / self.sub.value.strip()).resolve()
        return p

    def refresh_preview(self):
        self.preview.value = f"<code>{self.compute_path()}</code>"
