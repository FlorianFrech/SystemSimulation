# Framework/ui/views/fmu_instantiator.py
from __future__ import annotations
from pathlib import Path
import ipywidgets as W
import pandas as pd
from ipyfilechooser import FileChooser
from ..state import AppState
from ..widgets.status_bar import StatusBar
from ..services.fmu_introspect import preview_fmu
from SysSimX.core.fmu_comp import FMUComponent

class FMUInstantiatorView(W.HBox):
    def __init__(self, state: AppState):
        super().__init__()
        self.state = state
        self.status = StatusBar()

        # left
        self.dir = FileChooser(str(Path.cwd()), title="FMU directory", show_hidden=False, select_default=True, use_dir_icons=True)
        self.dir.show_only_dirs = True
        self.file = FileChooser(str(Path.cwd()), title="Pick FMU (*.fmu)", show_hidden=False, select_default=False, use_dir_icons=True)
        self.file.filter_pattern = "*.fmu"
        self.btn_load = W.Button(description="Load FMU", icon="search", button_style="info")

        self.inst_name = W.Text(description="Name:", placeholder="pendulum_fmu")
        self.inst_group = W.Text(description="Group:", placeholder="Plant / Control / Sensors")
        self.btn_inst = W.Button(description="Instantiate", icon="check", button_style="success")

        self.left = W.VBox([W.HTML("<h3>Step 3 — Instantiate FMU</h3>"),
                            W.HTML("<b>Directory</b>"), self.dir,
                            W.HTML("<b>File</b>"), self.file,
                            self.btn_load, W.HTML("<hr>"),
                            W.HTML("<b>Instance</b>"), self.inst_name, self.inst_group, self.btn_inst,
                            self.status], layout=W.Layout(width="45%"))

        # right
        self.io_out = W.Output()
        self.param_box = W.VBox()
        self.reg_out = W.Output()
        self.right = W.VBox([W.HTML("<b>I/O</b>"), self.io_out,
                             W.HTML("<b>Parameters</b>"), self.param_box,
                             W.HTML("<hr>"), self.reg_out])

        self.children = [self.left, W.HTML("&nbsp;"), self.right]

        # wire
        self.dir.register_callback(lambda *_: self._reset_file_root())
        self.btn_load.on_click(self._on_load)
        self.btn_inst.on_click(self._on_instantiate)
        self._refresh_registry()

    def _reset_file_root(self):
        root = self.dir.selected or self.dir._select.value or self.dir.getcwd()
        self.file.reset(path=root)

    def _on_load(self, _):
        sel = self.file.selected
        if not sel:
            self.status.set("Select an FMU file.", ok=False); return
        path = Path(sel)
        if not (path.exists() and path.suffix.lower() == ".fmu"):
            self.status.set("Pick a valid .fmu file.", ok=False); return
        self.state.current_fmu_path = path
        try:
            df_in, df_out, params = preview_fmu(path)
            with self.io_out:
                self.io_out.clear_output()
                display(W.HTML("<b>Inputs</b>")); display(df_in)
                display(W.HTML("<b>Outputs</b>")); display(df_out)
            # minimal param editors
            rows = []
            for name, var in sorted(params.items()):
                base = getattr(var, "_python_type", float)
                unit = getattr(var, "unit", None)
                start = var.start
                w = (W.FloatText(value=float(start) if start is not None else 0.0, description=name)
                     if base is float else
                     W.IntText(value=int(start) if start is not None else 0, description=name)
                     if base is int else
                     W.Checkbox(value=bool(start) if start is not None else False, description=name, indent=False)
                     if base is bool else
                     W.Text(value=str(start) if start is not None else "", description=name))
                rows.append(W.HBox([w, W.Label(f"[{unit}]")]) if unit else w)
            self.param_box.children = rows or [W.HTML("<i>No parameters.</i>")]
            self.status.set(f"Loaded {path.name}")
        except Exception as e:
            self.status.set(f"Failed to load FMU: {e}", ok=False)

    def _on_instantiate(self, _):
        p = self.state.current_fmu_path
        if p is None:
            self.status.set("Load an FMU first.", ok=False); return
        name = (self.inst_name.value or "").strip()
        if not name:
            self.status.set("Provide an instance name.", ok=False); return
        if name in self.state.registry:
            self.status.set(f"Instance '{name}' already exists.", ok=False); return
        try:
            comp = FMUComponent(name=name, fmu_path=str(p), group=(self.inst_group.value or None))
            # grab values from editors
            overrides = {}
            for child in self.param_box.children:
                w = child.children[0] if isinstance(child, W.HBox) else child
                overrides[w.description] = getattr(w, "value", None)
            if overrides:
                comp.set_parameters(**overrides)
            self.state.registry[name] = comp
            self.state.system.add_component(comp)
            self.status.set(f"Instantiated '{name}'.")
            self._refresh_registry()
        except Exception as e:
            self.status.set(f"Instantiation failed: {e}", ok=False)

    def _refresh_registry(self):
        with self.reg_out:
            self.reg_out.clear_output()
            rows = [{"name": n,
                     "group": c.group or "",
                     "n_inputs": len(c.input_specs),
                     "n_outputs": len(c.output_specs),
                     "kind": "FMU"} for n, c in self.state.registry.items()]
            df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=["name","group","n_inputs","n_outputs","kind"])
            display(W.HTML("<b>Instantiated Components</b>"))
            display(df)
