from pathlib import Path
from turtle import color
from ipyfilechooser import FileChooser
import ipywidgets as W
from IPython.display import display, clear_output, HTML
import pandas as pd

from ..core.port import PortType
from ..core.fmu_comp import FMUComponent
from ..system.system import System

from ..utilities.update_fmus import create_modelica_system, create_fmu, move_file

#---------------------------------------------------
# State
SYSTEM = System("MySystem")
REGISTRY: dict[str, FMUComponent] = {}
CURRENT_FMU_PATH: Path | None = None
PARAM_WIDGETS: dict[str, W.Widget] = {}

# Set of unique paths to modelica files
SELECTED = set()

#---------------------------------------------------
# Header Widgets
header_main = W.HTML("""
        <div style='background-color: #DFF2FD; color: #006699; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px;'>
            <h1>SysSimX: System Simulation Framework</h1>
            <h2>Demo User Interface</h2>
        </div>
        """)

header_1_model_selection = W.HTML("""
        <div style='background-color: #E0F2FE; color: #0369A1; padding: 15px; border-radius: 8px; text-align: center; margin-bottom: 15px;'>
            <h2>Step 1: Model Selection</h2>
        </div>
        """)

header_2_fmu_export = W.HTML("""
        <div style='background-color: #E0F2FE; color: #0369A1; padding: 15px; border-radius: 8px; text-align: center; margin-bottom: 15px;'>
            <h2>Step 2: FMU Export</h2>
        </div>
        """)

header_2_fmu_instantiation = W.HTML("""
        <div style='background-color: #E0F2FE; color: #0369A1; padding: 15px; border-radius: 8px; text-align: center; margin-bottom: 15px;'>
            <h2>Step 3: FMU Instantiation</h2>
        </div>
        """)

#---------------------------------------------------
# Widgets:

chooser = FileChooser(
    str(Path.cwd()),
    title="<h2><b>1. Browse & select a Modelica file (.mo)</b></h2>",
    show_hidden=False,
    select_default=False,
    use_dir_icons=True,
)
chooser.pattern = "*.mo"

btn_add = W.Button(description="Add Selected Model", button_style='success', icon='plus',
                   layout=W.Layout(width='200px'))
btn_remove = W.Button(description="Remove Selected Model", button_style='warning', icon='minus',
                      layout=W.Layout(width='200px'))
btn_clear = W.Button(description="Clear All Models", button_style='danger', icon='trash',
                     layout=W.Layout(width='200px'))
btn_export = W.Button(description="Export Selected Models to FMU", button_style='info', icon='download', tooltip="Return the list",
                      layout=W.Layout(width='300px'))

# Live list of selected model files
listbox = W.SelectMultiple(
    options=[],
    rows=10,
    description='Selected:',
    disabled=False,
    layout=W.Layout(width='60%')
)

status = W.Textarea(
    value="No models selected.",
    placeholder="",
    description="Status:",
    disabled=True,
    layout=W.Layout(width='60%', height='50px')
)

# Dropdown widget for model code preview selection
preview_label = W.HTML(value="<h3><b>Model Code Preview:</b></h3>")
preview_selected = W.Dropdown(options=[], description='File:', layout=W.Layout(width='60%'))
preview_text = W.Textarea(
    value='',
    placeholder='Select a model to preview its code here.',
    description='',
    disabled=True,
    layout=W.Layout(width='100%', height='300px')
)

# Destination directory for export
dest_header = W.HTML(value="<h2><b>2. Export Selected Models to FMU:</b></h2>")
dest_chooser = FileChooser(
    str(Path.cwd()),
    title="Select Export Directory",
    show_hidden=False,
    select_default=True,
    use_dir_icons=True,
    only_dirs=True
)

dest_subfolder = W.Text(
    value='exported_fmus',
    placeholder='Subfolder name for exported FMUs',
    description='Subfolder:',
    disabled=False,
    layout=W.Layout(width='50%')
)

dest_create = W.Checkbox(
    value=True,
    description='Create subfolder if it does not exist',
    indent=True,
    layout=W.Layout(width='400px')
)

dest_preview = W.HTML(value="<i>Note: The export directory will be created if it does not exist.</i>")

#---------------------------------------------------
# FMU Instantiation Widgets
fmu_dir = FileChooser(str(Path.cwd()), title="Select directory with FMUs", show_hidden=False, select_default=True, use_dir_icons=True)
fmu_dir.show_only_dirs = True

fmu_file = FileChooser(str(Path.cwd()), title="Select an FMU file (*.fmu)", show_hidden=False, select_default=False, use_dir_icons=True)
fmu_file.filter_pattern = "*.fmu"

# Instance metadata display
inst_name = W.Text(description="Instance Name:", disabled=True, layout=W.Layout(width='60%'), placeholder="e.g., pendulum_fmu")
inst_group = W.Text(description="Instance Group:", disabled=True, layout=W.Layout(width='60%'), placeholder="e.g., Plant / Control / Sensors")

# I/O preview (readonly)
io_out = W.Output()
def show_io_tables(comp: FMUComponent):
    with io_out:
        io_out.clear_output()
        # Inputs
        in_rows = []
        for n, spec in comp.input_specs.items():
            in_rows.append({"name": n, "type": spec.type.value, "unit": spec.unit or ""})
        df_in = pd.DataFrame(in_rows) if in_rows else pd.DataFrame(columns=["name","type","unit"])

        # Outputs
        out_rows = []
        for n, spec in comp.output_specs.items():
            out_rows.append({"name": n, "type": spec.type.value, "unit": spec.unit or ""})
        df_out = pd.DataFrame(out_rows) if out_rows else pd.DataFrame(columns=["name","type","unit"])

        display(W.HTML("<b>Inputs</b>"))
        display(df_in)
        display(W.HTML("<b>Outputs</b>"))
        display(df_out)

# Parameter editors
param_box = W.VBox()
param_out = W.Output()
def _editor_for_param(name: str, var) -> W.Widget:
    """Create a widget for a parameter based on fmpy ModelVariable._python_type."""
    tooltip = var.description or ""
    unit = getattr(var, "unit", None)
    start = var.start
    base = getattr(var, "_python_type", float)
    if base is float:
        w = W.FloatText(value=float(start) if start is not None else 0.0,
                        description=name, layout=W.Layout(width="50%"), tooltip=tooltip)
        if unit:
            return W.HBox([w, W.Label(f"[{unit}]")])
        return w
    elif base is int:
        w = W.IntText(value=int(start) if start is not None else 0,
                      description=name, layout=W.Layout(width="50%"), tooltip=tooltip)
        if unit:
            return W.HBox([w, W.Label(f"[{unit}]")])
        return w
    elif base is bool:
        return W.Checkbox(value=bool(start) if start is not None else False,
                          description=name, indent=False, tooltip=tooltip)
    elif base is str:
        return W.Text(value=str(start) if start is not None else "",
                      description=name, layout=W.Layout(width="60%"), tooltip=tooltip)
    else:
        # Fallback to text
        return W.Text(value=str(start) if start is not None else "",
                      description=name, layout=W.Layout(width="60%"), tooltip=tooltip)
    
def build_param_editors(comp: FMUComponent):
    global PARAM_WIDGETS
    PARAM_WIDGETS = {}
    rows = []
    # comp.parameters is dict[name -> fmpy.ModelVariable] (from your wrapper)
    for name, var in sorted(comp.parameters.items()):
        editor = _editor_for_param(name, var)
        PARAM_WIDGETS[name] = editor if isinstance(editor, W.Widget) else editor.children[0]  # grab main widget
        if isinstance(editor, W.HBox):
            rows.append(editor)
        else:
            rows.append(editor)
    if not rows:
        rows = [W.HTML("<i>No FMU parameters.</i>")]
    param_box.children = rows

# Buttons
btn_load = W.Button(description="Load FMU", button_style="info", icon="search")
btn_instantiate = W.Button(description="Instantiate Component", button_style="success", icon="check")
btn_clear = W.Button(description="Clear Preview", button_style="warning", icon="trash")

fmu_status = W.Textarea(
    value="No FMU loaded.",
    placeholder="",
    description="FMU Status:",
    disabled=True,
    layout=W.Layout(width='60%', height='50px')
)

#---------------------------------------------------
# Helpers
def update_listbox():
    listbox.options = sorted(str(p) for p in SELECTED)

def set_status(message: str, ok=True):
        color = "#065f46" if ok else "#92400e"
        status.value = f'<span style="color:{color}">{message}</span>'

def update_preview_dropdown():
    opts = []
    for p in sorted(SELECTED):
        try:
            label = str(p.relative_to(Path.cwd()))
        except Exception:
            label = str(p)
        opts.append((label, str(p)))
    preview_selected.options = opts
    if opts:
        current = preview_selected.value
        if current and current in [v for _, v in opts]:
            preview_selected.value = current
        else:
            preview_selected.value = opts[0][1]
    else:
        preview_selected.options = []
        preview_selected.value = None
        preview_text.value = ''
        preview_text.placeholder = 'Select a model to preview its code here.'

def read_file_text(file_path: str) -> str:
    p = Path(file_path)
    if not p.exists() or not p.is_file():
        return f"[Error] File not found: {file_path}"
    try:
        with p.open('r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"[Error] Could not read file: {e}"
    return ""

def refresh_code_preview(_=None):
    if not preview_selected.value:
        set_status("No model selected for preview.", ok=False)
        return
    text = read_file_text(preview_selected.value)
    preview_text.value = text

def add_selected_file(_=None):
    sel = chooser.selected
    if not sel:
        set_status("No file selected to add.", ok=False)
        return
    p = Path(sel)
    if not (p.is_file() and p.suffix == ".mo"):
        set_status("Please select a valid Modelica (.mo) file.", ok=False)
        return
    if p in SELECTED:
        set_status("File already in the selected list.", ok=False)
        return
    SELECTED.add(p)
    update_listbox()
    update_preview_dropdown()
    refresh_code_preview()
    set_status(f"Added: {p.name}")

def remove_selected_file(_=None):
    if not listbox.value:
        set_status("No file selected to remove.", ok=False)
        return
    for item in listbox.value:
        try:
            SELECTED.remove(Path(item))
        except KeyError:
            pass
    update_listbox()
    update_preview_dropdown()
    refresh_code_preview()
    set_status(f"Removed selected models.")

def clear_all(_=None):
    SELECTED.clear()
    update_listbox()
    update_preview_dropdown()
    refresh_code_preview()
    set_status("Cleared all selected models.")

def export_selected_models(_=None):
    if not SELECTED:
        set_status("No models selected to export.", ok=False)
        return

    export_dir = _compute_export_path()
    try:
        if export_dir.exists():
            if not export_dir.is_dir():
                set_status(f"Export path exists and is not a directory: {export_dir}", ok=False)
                return
        else:
            if dest_create.value:
                export_dir.mkdir(parents=True, exist_ok=True)
            else:
                set_status(f"Export directory does not exist: {export_dir}", ok=False)
                return
    except Exception as e:
        set_status(f"Could not create export directory: {e}", ok=False)
        return
    
    files = tuple(sorted(SELECTED))

    for f in files:
        # Placeholder for actual export logic
        dest_path = export_dir / f.name.replace('.mo', '.fmu')
        try:
            package_path = f.parent / "package.mo"  # Assuming package.mo is in the same directory
            package_name = "ControlledPendulum"     # Placeholder, should be derived from actual package
            model_name = f.stem
            composed_model_name = f"{package_name}.{model_name}"
            modelica_system = create_modelica_system(package_path, composed_model_name)
            src_path = create_fmu(modelica_system)
            move_file(src_path, dest_path)
            set_status(f"Exported {f.name} to {dest_path}", ok=True)
        except Exception as e:
            set_status(f"Failed to export {f.name}: {e}", ok=False)
            return
    return files

def _compute_export_path() -> Path:
    base = dest_chooser.selected or dest_chooser._select.value or dest_chooser.getcwd()
    base_path = Path(str(base)).expanduser().resolve()
    if dest_subfolder.value.strip():
        return (base_path / dest_subfolder.value.strip()).resolve()
    return base_path

def _refresh_dest_preview():
    p = _compute_export_path()
    dest_preview.value = f"<code>{p}</code>"

def _update_fmu_file_root():
    root = fmu_dir.selected or fmu_dir._select.value or fmu_dir.getcwd()
    fmu_file.reset(path=root)

def on_load_clicked(_):
    sel = fmu_file.selected
    if not sel:
        fmu_status.value = "No FMU file selected."
        return
    p = Path(sel)
    if not (p.is_file() and p.suffix == ".fmu"):
        fmu_status.value = "Please select a valid FMU (.fmu) file."
        return
    global CURRENT_FMU_PATH
    CURRENT_FMU_PATH = p

    try:
        # Build a temporary FMUComponent to read metadata
        temp = FMUComponent(name="__preview__", fmu_path=str(p))
        show_io_tables(temp)
        fmu_status.value = f"Loaded FMU: {p.name}"
    except Exception as e:
        fmu_status.value = f"Failed to load FMU: {e}"
        return

def on_instantiate_clicked(_):
    if CURRENT_FMU_PATH is None:
        fmu_status.value = "No FMU loaded to instantiate."
        return
    name = (inst_name.value.strip() or "")
    if not name:
        fmu_status.value = "Please provide a valid instance name."
        return
    if name in REGISTRY:
        fmu_status.value = f"An instance with the name '{name}' already exists."
        return
    try:
        comp = FMUComponent(name=name, fmu_path=str(CURRENT_FMU_PATH))
        overrides = {}
        for param_name, widget in PARAM_WIDGETS.items():
            val = getattr(widget, 'value', None)
            overrides[param_name] = val
        if overrides:
            comp.set_parameters(**overrides)
        REGISTRY[name] = comp
        SYSTEM.add_component(comp)
        fmu_status.value = f"Instantiated component '{name}' and added to system."
        refresh_registry()
    except Exception as e:
        fmu_status.value = f"Failed to instantiate component: {e}"

reg_out = W.Output()
def refresh_registry():
    with reg_out:
        reg_out.clear_output()
        rows = []
        for name, comp in REGISTRY.items():
            rows.append({
                "name": name,
                "group": comp.group or "",
                "n_inputs": len(comp.input_specs),
                "n_outputs": len(comp.output_specs),
                "kind": "FMU",
            })
        df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=["name","group","n_inputs","n_outputs","kind"])
        display(W.HTML("<b>Instantiated Components</b>"))
        display(df)



#---------------------------------------------------
# Event bindings / Wire handlings
btn_add.on_click(add_selected_file)
btn_remove.on_click(remove_selected_file)
btn_clear.on_click(clear_all)

btn_export.on_click(export_selected_models)
preview_selected.observe(lambda change: refresh_code_preview() if change['name'] == 'value' else None, names='value')
dest_chooser.register_callback(lambda _: _refresh_dest_preview())
dest_subfolder.observe(lambda change: _refresh_dest_preview() if change['name'] == 'value' else None, names='value')
fmu_dir.register_callback(_update_fmu_file_root)
_update_fmu_file_root()

btn_load.on_click(on_load_clicked)

#---------------------------------------------------
# Layout
actions = W.HBox([btn_add, btn_remove, btn_clear], layout=W.Layout(margin='10px 0px'))
preview_box = W.VBox([preview_label, preview_selected, preview_text], layout=W.Layout(margin='10px 0px'))
dest_box = W.VBox([dest_header, dest_subfolder, dest_create, dest_preview, btn_export], layout=W.Layout(margin='10px 0px'))
_refresh_dest_preview()

# FMU Instantiation layout
# Layout
left = W.VBox([
    header_2_fmu_instantiation,
    W.HTML("<b>1) Choose FMU directory</b>"),
    fmu_dir,
    W.HTML("<b>2) Pick FMU file</b>"),
    fmu_file,
    W.HBox([btn_load, btn_clear]),
    W.HTML("<hr>"),
    W.HTML("<b>3) Instance metadata</b>"),
    inst_name,
    inst_group,
    W.HBox([btn_instantiate]),
    status,
])

right = W.VBox([
    W.HTML("<b>I/O Ports</b>"),
    io_out,
    W.HTML("<b>Parameters</b>"),
    param_box,
    W.HTML("<hr>"),
    reg_out,
])

ui = W.VBox([header_main,
             chooser,
             actions,
             listbox,
             W.HBox([W.Label(""),], layout=W.Layout(height='6px')),
             preview_box,
             dest_box,
             status,],
             #W.HBox([left, W.HTML("&nbsp;&nbsp;&nbsp;"), right], layout=W.Layout(width="100%"))],
             layout=W.Layout(width='100%'))

refresh_registry()