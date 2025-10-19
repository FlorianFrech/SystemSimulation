# Framework/ui/widgets/file_chooser.py
from __future__ import annotations
from pathlib import Path
import ipywidgets as W
from ipyfilechooser import FileChooser
from typing import Callable

class ModelicaSelector(W.VBox):
    """File chooser + list + preview (no export). Emits callbacks."""
    def __init__(self, on_added: Callable[[Path], None], on_removed: Callable[[list[Path]], None]):
        super().__init__()
        self.on_added = on_added
        self.on_removed = on_removed

        self.chooser = FileChooser(str(Path.cwd()),
                                   title="Select a Modelica file (.mo)",
                                   show_hidden=False, select_default=False, use_dir_icons=True)
        self.chooser.filter_pattern = "*.mo"

        self.btn_add = W.Button(description="Add", icon="plus", button_style="success")
        self.btn_remove = W.Button(description="Remove", icon="minus", button_style="warning")
        self.btn_clear = W.Button(description="Clear", icon="trash", button_style="danger")

        self.listbox = W.SelectMultiple(options=[], rows=8, description="Selected")
        self.preview = W.Textarea(disabled=True, layout=W.Layout(width="100%", height="240px"))

        self.btn_add.on_click(self._on_add)
        self.btn_remove.on_click(self._on_remove)
        self.btn_clear.on_click(self._on_clear)
        self.children = [self.chooser, W.HBox([self.btn_add, self.btn_remove, self.btn_clear]), self.listbox, self.preview]

    def _on_add(self, _):
        sel = self.chooser.selected
        if sel:
            p = Path(sel)
            if p.is_file() and p.suffix.lower() == ".mo":
                self.on_added(p)

    def _on_remove(self, _):
        paths = [Path(v) for v in self.listbox.value]
        if paths:
            self.on_removed(paths)

    def _on_clear(self, _):
        self.on_removed([Path(v) for v in self.listbox.options])

    # external updates
    def set_list(self, files: list[Path]):
        self.listbox.options = [str(p) for p in sorted(files)]

    def set_preview(self, text: str):
        self.preview.value = text
