"""
SysSimX UI Core Module
====================

Clean, structured UI framework for system simulation workflows.
Provides organized components for model selection, FMU export, and instantiation.
"""

from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Set, Optional, Any, Callable
from ipyfilechooser import FileChooser
import ipywidgets as W
from IPython.display import display, clear_output
import pandas as pd

from ..core.port import PortType
from ..core.fmu_comp import FMUComponent
from ..system.system import System
from ..utilities.update_fmus import create_modelica_system, create_fmu, move_file


# =====================================================================
# CONFIGURATION & STYLING
# =====================================================================

@dataclass
class UITheme:
    """Centralized UI theme configuration."""
    primary_color: str = "#006699"
    secondary_color: str = "#0369A1"
    success_color: str = "#065f46"
    warning_color: str = "#92400e"
    danger_color: str = "#dc2626"
    
    background_primary: str = "#DFF2FD"
    background_secondary: str = "#E0F2FE"
    
    border_radius: str = "8px"
    padding_large: str = "20px"
    padding_medium: str = "15px"
    padding_small: str = "10px"
    
    @property
    def header_style(self) -> str:
        return f"""
            background-color: {self.background_primary}; 
            color: {self.primary_color}; 
            padding: {self.padding_large}; 
            border-radius: {self.border_radius}; 
            text-align: center; 
            margin-bottom: {self.padding_large};
        """
    
    @property
    def section_header_style(self) -> str:
        return f"""
            background-color: {self.background_secondary}; 
            color: {self.secondary_color}; 
            padding: {self.padding_medium}; 
            border-radius: {self.border_radius}; 
            text-align: center; 
            margin-bottom: {self.padding_medium};
        """

THEME = UITheme()


# =====================================================================
# APPLICATION STATE
# =====================================================================

@dataclass
class ApplicationState:
    """Centralized application state management."""
    system: System = field(default_factory=lambda: System("MySystem"))
    registry: Dict[str, FMUComponent] = field(default_factory=dict)
    selected_models: Set[Path] = field(default_factory=set)
    current_fmu_path: Optional[Path] = None
    param_widgets: Dict[str, W.Widget] = field(default_factory=dict)
    
    def add_model(self, path: Path) -> bool:
        """Add a model to selection. Returns True if added, False if already exists."""
        if path in self.selected_models:
            return False
        self.selected_models.add(path)
        return True
    
    def remove_model(self, path: Path) -> bool:
        """Remove a model from selection. Returns True if removed, False if not found."""
        try:
            self.selected_models.remove(path)
            return True
        except KeyError:
            return False
    
    def clear_models(self) -> None:
        """Clear all selected models."""
        self.selected_models.clear()
    
    def add_component(self, name: str, component: FMUComponent) -> bool:
        """Add component to registry. Returns True if added, False if name exists."""
        if name in self.registry:
            return False
        self.registry[name] = component
        self.system.add_component(component)
        return True


# =====================================================================
# UI COMPONENTS BASE CLASSES  
# =====================================================================

class UIComponent:
    """Base class for UI components with common functionality."""
    
    def __init__(self, state: ApplicationState):
        self.state = state
        self.widget = None
        self._setup_ui()
        self._bind_events()
    
    def _setup_ui(self):
        """Override to setup UI elements."""
        raise NotImplementedError
    
    def _bind_events(self):
        """Override to bind event handlers."""
        pass
    
    def display(self):
        """Display the component."""
        if self.widget:
            display(self.widget)


class StatusMixin:
    """Mixin for components that need status reporting."""
    
    def __init__(self):
        self.status_widget = W.Textarea(
            value="Ready",
            description="Status:",
            disabled=True,
            layout=W.Layout(width='60%', height='50px')
        )
    
    def set_status(self, message: str, success: bool = True):
        """Set status message with appropriate styling."""
        color = THEME.success_color if success else THEME.warning_color
        self.status_widget.value = message


# =====================================================================
# SPECIALIZED UI COMPONENTS
# =====================================================================

class ModelSelectionComponent(UIComponent, StatusMixin):
    """Component for selecting and managing Modelica model files."""
    
    def __init__(self, state: ApplicationState):
        StatusMixin.__init__(self)
        UIComponent.__init__(self, state)
    
    def _setup_ui(self):
        # Header
        self.header = W.HTML(f"""
            <div style='{THEME.section_header_style}'>
                <h2>Step 1: Model Selection</h2>
            </div>
        """)
        
        # File chooser
        self.file_chooser = FileChooser(
            str(Path.cwd()),
            title="<b>Browse & select Modelica files (.mo)</b>",
            show_hidden=False,
            select_default=False,
            use_dir_icons=True,
        )
        self.file_chooser.pattern = "*.mo"
        
        # Action buttons
        self.btn_add = W.Button(
            description="Add Selected Model", 
            button_style='success', 
            icon='plus',
            layout=W.Layout(width='180px')
        )
        self.btn_remove = W.Button(
            description="Remove Selected", 
            button_style='warning', 
            icon='minus',
            layout=W.Layout(width='180px')
        )
        self.btn_clear = W.Button(
            description="Clear All", 
            button_style='danger', 
            icon='trash',
            layout=W.Layout(width='180px')
        )
        
        # Model list
        self.model_list = W.SelectMultiple(
            options=[],
            rows=8,
            description='Selected Models:',
            disabled=False,
            layout=W.Layout(width='70%')
        )
        
        # Code preview
        self.preview_dropdown = W.Dropdown(
            options=[], 
            description='Preview File:', 
            layout=W.Layout(width='60%')
        )
        self.preview_text = W.Textarea(
            value='',
            placeholder='Select a model to preview its code here.',
            description='',
            disabled=True,
            layout=W.Layout(width='100%', height='300px')
        )
        
        # Layout
        actions_box = W.HBox([
            self.btn_add, self.btn_remove, self.btn_clear
        ], layout=W.Layout(margin='10px 0px'))
        
        preview_box = W.VBox([
            W.HTML("<h3><b>Model Code Preview:</b></h3>"),
            self.preview_dropdown,
            self.preview_text
        ], layout=W.Layout(margin='10px 0px'))
        
        self.widget = W.VBox([
            self.header,
            self.file_chooser,
            actions_box,
            self.model_list,
            preview_box,
            self.status_widget
        ])
    
    def _bind_events(self):
        """Bind event handlers."""
        self.btn_add.on_click(self._on_add_clicked)
        self.btn_remove.on_click(self._on_remove_clicked)
        self.btn_clear.on_click(self._on_clear_clicked)
        self.preview_dropdown.observe(self._on_preview_changed, names='value')
    
    def _on_add_clicked(self, _):
        """Handle add button click."""
        selected = self.file_chooser.selected
        if not selected:
            self.set_status("No file selected to add.", False)
            return
        
        file_path = Path(selected)
        if not (file_path.is_file() and file_path.suffix == ".mo"):
            self.set_status("Please select a valid Modelica (.mo) file.", False)
            return
        
        if self.state.add_model(file_path):
            self._update_model_list()
            self._update_preview_dropdown()
            self.set_status(f"Added: {file_path.name}")
        else:
            self.set_status("File already in the selected list.", False)
    
    def _on_remove_clicked(self, _):
        """Handle remove button click."""
        selected_items = self.model_list.value
        if not selected_items:
            self.set_status("No file selected to remove.", False)
            return
        
        removed_count = 0
        for item in selected_items:
            if self.state.remove_model(Path(item)):
                removed_count += 1
        
        self._update_model_list()
        self._update_preview_dropdown()
        self.set_status(f"Removed {removed_count} model(s).")
    
    def _on_clear_clicked(self, _):
        """Handle clear button click."""
        self.state.clear_models()
        self._update_model_list()
        self._update_preview_dropdown()
        self.set_status("Cleared all selected models.")
    
    def _on_preview_changed(self, change):
        """Handle preview dropdown change."""
        if change['name'] == 'value' and change['new']:
            self._refresh_code_preview()
    
    def _update_model_list(self):
        """Update the model list widget."""
        self.model_list.options = sorted(str(p) for p in self.state.selected_models)
    
    def _update_preview_dropdown(self):
        """Update the preview dropdown options."""
        options = []
        for path in sorted(self.state.selected_models):
            try:
                label = str(path.relative_to(Path.cwd()))
            except ValueError:
                label = str(path)
            options.append((label, str(path)))
        
        self.preview_dropdown.options = options
        if options and (not self.preview_dropdown.value or 
                       self.preview_dropdown.value not in [v for _, v in options]):
            self.preview_dropdown.value = options[0][1]
            self._refresh_code_preview()
        elif not options:
            self.preview_text.value = ''
            self.preview_text.placeholder = 'Select a model to preview its code here.'
    
    def _refresh_code_preview(self):
        """Refresh the code preview."""
        if not self.preview_dropdown.value:
            return
        
        try:
            path = Path(self.preview_dropdown.value)
            if path.exists():
                with path.open('r', encoding='utf-8') as f:
                    self.preview_text.value = f.read()
            else:
                self.preview_text.value = f"[Error] File not found: {path}"
        except Exception as e:
            self.preview_text.value = f"[Error] Could not read file: {e}"


class FMUExportComponent(UIComponent, StatusMixin):
    """Component for exporting models to FMU format."""
    
    def __init__(self, state: ApplicationState):
        StatusMixin.__init__(self)
        UIComponent.__init__(self, state)
    
    def _setup_ui(self):
        # Header
        self.header = W.HTML(f"""
            <div style='{THEME.section_header_style}'>
                <h2>Step 2: FMU Export</h2>
            </div>
        """)
        
        # Destination chooser
        self.dest_chooser = FileChooser(
            str(Path.cwd()),
            title="Select Export Directory",
            show_hidden=False,
            select_default=True,
            use_dir_icons=True,
            only_dirs=True
        )
        
        # Export options
        self.subfolder_input = W.Text(
            value='exported_fmus',
            placeholder='Subfolder name for exported FMUs',
            description='Subfolder:',
            layout=W.Layout(width='50%')
        )
        
        self.create_dirs_checkbox = W.Checkbox(
            value=True,
            description='Create directories if they do not exist',
            indent=True,
            layout=W.Layout(width='400px')
        )
        
        # Export preview and button
        self.export_preview = W.HTML(value="<i>Export path will be shown here</i>")
        self.btn_export = W.Button(
            description="Export Selected Models to FMU", 
            button_style='info', 
            icon='download',
            layout=W.Layout(width='300px')
        )
        
        # Layout
        options_box = W.VBox([
            W.HTML("<b>Export Configuration:</b>"),
            self.subfolder_input,
            self.create_dirs_checkbox,
            W.HTML("<b>Export Path Preview:</b>"),
            self.export_preview,
            self.btn_export
        ], layout=W.Layout(margin='10px 0px'))
        
        self.widget = W.VBox([
            self.header,
            self.dest_chooser,
            options_box,
            self.status_widget
        ])
        
        # Initialize preview
        self._update_export_preview()
    
    def _bind_events(self):
        """Bind event handlers."""
        self.btn_export.on_click(self._on_export_clicked)
        self.dest_chooser.register_callback(lambda _: self._update_export_preview())
        self.subfolder_input.observe(
            lambda change: self._update_export_preview() if change['name'] == 'value' else None, 
            names='value'
        )
    
    def _on_export_clicked(self, _):
        """Handle export button click."""
        if not self.state.selected_models:
            self.set_status("No models selected to export.", False)
            return
        
        export_path = self._compute_export_path()
        
        # Validate/create export directory
        try:
            if export_path.exists():
                if not export_path.is_dir():
                    self.set_status(f"Export path exists and is not a directory: {export_path}", False)
                    return
            else:
                if self.create_dirs_checkbox.value:
                    export_path.mkdir(parents=True, exist_ok=True)
                else:
                    self.set_status(f"Export directory does not exist: {export_path}", False)
                    return
        except Exception as e:
            self.set_status(f"Could not create export directory: {e}", False)
            return
        
        # Export each model
        exported_count = 0
        for model_path in sorted(self.state.selected_models):
            if self._export_single_model(model_path, export_path):
                exported_count += 1
            else:
                return  # Error already reported
        
        self.set_status(f"Successfully exported {exported_count} model(s) to {export_path}")
    
    def _export_single_model(self, model_path: Path, export_dir: Path) -> bool:
        """Export a single model to FMU. Returns True on success."""
        dest_path = export_dir / model_path.name.replace('.mo', '.fmu')
        
        try:
            # This is a placeholder - adjust based on your actual export logic
            package_path = model_path.parent / "package.mo"
            package_name = "ControlledPendulum"  # Should be derived from actual package
            model_name = model_path.stem
            composed_model_name = f"{package_name}.{model_name}"
            
            modelica_system = create_modelica_system(package_path, composed_model_name)
            src_path = create_fmu(modelica_system)
            move_file(src_path, dest_path)
            
            return True
        except Exception as e:
            self.set_status(f"Failed to export {model_path.name}: {e}", False)
            return False
    
    def _compute_export_path(self) -> Path:
        """Compute the full export path."""
        base = self.dest_chooser.selected or self.dest_chooser.getcwd()
        base_path = Path(str(base)).expanduser().resolve()
        
        if self.subfolder_input.value.strip():
            return (base_path / self.subfolder_input.value.strip()).resolve()
        return base_path
    
    def _update_export_preview(self):
        """Update the export path preview."""
        path = self._compute_export_path()
        self.export_preview.value = f"<code>{path}</code>"

class FMUInstantiationComponent(UIComponent, StatusMixin):
    """Component for loading and instantiating FMU files."""
    
    def __init__(self, state: ApplicationState):
        StatusMixin.__init__(self)
        UIComponent.__init__(self, state)
    
    def _setup_ui(self):
        # Header
        self.header = W.HTML(f"""
            <div style='{THEME.section_header_style}'>
                <h2>Step 3: FMU Instantiation</h2>
            </div>
        """)
        
        # FMU file selection
        self.fmu_dir_chooser = FileChooser(
            str(Path.cwd()), 
            title="Select directory with FMUs", 
            show_hidden=False, 
            select_default=True, 
            use_dir_icons=True,
            only_dirs=True
        )
        
        self.fmu_file_chooser = FileChooser(
            str(Path.cwd()), 
            title="Select an FMU file (*.fmu)", 
            show_hidden=False, 
            select_default=False, 
            use_dir_icons=True
        )
        self.fmu_file_chooser.filter_pattern = "*.fmu"
        
        # Instance metadata
        self.instance_name = W.Text(
            description="Instance Name:", 
            layout=W.Layout(width='60%'), 
            placeholder="e.g., pendulum_fmu"
        )
        self.instance_group = W.Text(
            description="Instance Group:", 
            layout=W.Layout(width='60%'), 
            placeholder="e.g., Plant / Control / Sensors"
        )
        
        # Control buttons
        self.btn_load = W.Button(
            description="Load FMU", 
            button_style="info", 
            icon="search"
        )
        self.btn_instantiate = W.Button(
            description="Instantiate Component", 
            button_style="success", 
            icon="check"
        )
        self.btn_clear_preview = W.Button(
            description="Clear Preview", 
            button_style="warning", 
            icon="trash"
        )
        
        # Display areas
        self.io_output = W.Output()
        self.param_box = W.VBox()
        self.registry_output = W.Output()
        
        # Layout
        left_panel = W.VBox([
            W.HTML("<b>1) Choose FMU directory</b>"),
            self.fmu_dir_chooser,
            W.HTML("<b>2) Pick FMU file</b>"),
            self.fmu_file_chooser,
            W.HBox([self.btn_load, self.btn_clear_preview]),
            W.HTML("<hr>"),
            W.HTML("<b>3) Instance metadata</b>"),
            self.instance_name,
            self.instance_group,
            self.btn_instantiate,
            self.status_widget,
        ])
        
        right_panel = W.VBox([
            W.HTML("<b>I/O Ports</b>"),
            self.io_output,
            W.HTML("<b>Parameters</b>"),
            self.param_box,
            W.HTML("<hr>"),
            W.HTML("<b>Instantiated Components</b>"),
            self.registry_output,
        ])
        
        self.widget = W.VBox([
            self.header,
            W.HBox([left_panel, right_panel], layout=W.Layout(justify_content='space-between'))
        ])
        
        # Initialize registry display
        self._refresh_registry()
    
    def _bind_events(self):
        """Bind event handlers."""
        self.btn_load.on_click(self._on_load_clicked)
        self.btn_instantiate.on_click(self._on_instantiate_clicked)
        self.btn_clear_preview.on_click(self._on_clear_clicked)
        self.fmu_dir_chooser.register_callback(self._update_fmu_file_root)
        self._update_fmu_file_root()
    
    def _on_load_clicked(self, _):
        """Handle load FMU button click."""
        selected = self.fmu_file_chooser.selected
        if not selected:
            self.set_status("No FMU file selected.", False)
            return
        
        fmu_path = Path(selected)
        if not (fmu_path.is_file() and fmu_path.suffix == ".fmu"):
            self.set_status("Please select a valid FMU (.fmu) file.", False)
            return
        
        try:
            # Store the loaded FMU path
            self.state.current_fmu_path = fmu_path
            
            # Create temporary component to read metadata
            temp_component = FMUComponent(name="__preview__", fmu_path=str(fmu_path))
            
            # Display I/O information
            self._show_io_tables(temp_component)
            
            # Build parameter editors
            self._build_parameter_editors(temp_component)
            
            self.set_status(f"Loaded FMU: {fmu_path.name}")
            
        except Exception as e:
            self.set_status(f"Failed to load FMU: {e}", False)
    
    def _on_instantiate_clicked(self, _):
        """Handle instantiate component button click."""
        if self.state.current_fmu_path is None:
            self.set_status("No FMU loaded to instantiate.", False)
            return
        
        name = self.instance_name.value.strip()
        if not name:
            self.set_status("Please provide a valid instance name.", False)
            return
        
        try:
            # Create component
            component = FMUComponent(name=name, fmu_path=str(self.state.current_fmu_path))
            
            # Apply parameter overrides
            overrides = {}
            for param_name, widget in self.state.param_widgets.items():
                value = getattr(widget, 'value', None)
                if value is not None:
                    overrides[param_name] = value
            
            if overrides:
                component.set_parameters(**overrides)
            
            # Set group if provided
            if self.instance_group.value.strip():
                component.group = self.instance_group.value.strip()
            
            # Add to system
            if self.state.add_component(name, component):
                self.set_status(f"Instantiated component '{name}' and added to system.")
                self._refresh_registry()
            else:
                self.set_status(f"A component with name '{name}' already exists.", False)
                
        except Exception as e:
            self.set_status(f"Failed to instantiate component: {e}", False)
    
    def _on_clear_clicked(self, _):
        """Handle clear preview button click."""
        self.state.current_fmu_path = None
        self.state.param_widgets.clear()
        
        # Clear displays
        with self.io_output:
            self.io_output.clear_output()
        
        self.param_box.children = []
        self.set_status("Preview cleared.")
    
    def _update_fmu_file_root(self, *args):
        """Update FMU file chooser root directory."""
        root = self.fmu_dir_chooser.selected or self.fmu_dir_chooser.getcwd()
        self.fmu_file_chooser.reset(path=root)
    
    def _show_io_tables(self, component: FMUComponent):
        """Display I/O port information."""
        with self.io_output:
            self.io_output.clear_output()
            
            # Prepare input data
            input_rows = [
                {"name": name, "type": spec.type.value, "unit": spec.unit or ""}
                for name, spec in component.input_specs.items()
            ]
            df_inputs = pd.DataFrame(input_rows) if input_rows else pd.DataFrame(columns=["name", "type", "unit"])
            
            # Prepare output data  
            output_rows = [
                {"name": name, "type": spec.type.value, "unit": spec.unit or ""}
                for name, spec in component.output_specs.items()
            ]
            df_outputs = pd.DataFrame(output_rows) if output_rows else pd.DataFrame(columns=["name", "type", "unit"])
            
            # Display tables
            display(W.HTML("<b>Inputs</b>"))
            display(df_inputs)
            display(W.HTML("<b>Outputs</b>"))
            display(df_outputs)
    
    def _build_parameter_editors(self, component: FMUComponent):
        """Build parameter editor widgets."""
        self.state.param_widgets.clear()
        editors = []
        
        for name, var in sorted(component.parameters.items()):
            editor = self._create_parameter_editor(name, var)
            if editor:
                self.state.param_widgets[name] = editor if isinstance(editor, W.Widget) else editor.children[0]
                editors.append(editor)
        
        if not editors:
            editors = [W.HTML("<i>No FMU parameters found.</i>")]
        
        self.param_box.children = editors
    
    def _create_parameter_editor(self, name: str, var) -> Optional[W.Widget]:
        """Create appropriate widget for a parameter based on its type."""
        tooltip = getattr(var, 'description', '') or ""
        unit = getattr(var, 'unit', None)
        start = getattr(var, 'start', None)
        python_type = getattr(var, '_python_type', float)
        
        # Create base widget based on type
        if python_type is float:
            widget = W.FloatText(
                value=float(start) if start is not None else 0.0,
                description=name, 
                layout=W.Layout(width="50%"), 
                tooltip=tooltip
            )
        elif python_type is int:
            widget = W.IntText(
                value=int(start) if start is not None else 0,
                description=name, 
                layout=W.Layout(width="50%"), 
                tooltip=tooltip
            )
        elif python_type is bool:
            widget = W.Checkbox(
                value=bool(start) if start is not None else False,
                description=name, 
                indent=False, 
                tooltip=tooltip
            )
        elif python_type is str:
            widget = W.Text(
                value=str(start) if start is not None else "",
                description=name, 
                layout=W.Layout(width="60%"), 
                tooltip=tooltip
            )
        else:
            # Fallback to text widget
            widget = W.Text(
                value=str(start) if start is not None else "",
                description=name, 
                layout=W.Layout(width="60%"), 
                tooltip=tooltip
            )
        
        # Add unit label if present
        if unit and python_type in (float, int):
            return W.HBox([widget, W.Label(f"[{unit}]")])
        
        return widget
    
    def _refresh_registry(self):
        """Refresh the component registry display."""
        with self.registry_output:
            self.registry_output.clear_output()
            
            rows = [
                {
                    "name": name,
                    "group": comp.group or "",
                    "n_inputs": len(comp.input_specs),
                    "n_outputs": len(comp.output_specs),
                    "kind": "FMU",
                }
                for name, comp in self.state.registry.items()
            ]
            
            df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=["name", "group", "n_inputs", "n_outputs", "kind"])
            display(df)


# =====================================================================
# MAIN APPLICATION INTERFACE
# =====================================================================

class SysSimXUI:
    """Main application interface combining all components."""
    
    def __init__(self):
        self.state = ApplicationState()
        self._setup_components()
        self._setup_layout()
    
    def _setup_components(self):
        """Initialize all UI components."""
        self.model_selection = ModelSelectionComponent(self.state)
        self.fmu_export = FMUExportComponent(self.state)
        self.fmu_instantiation = FMUInstantiationComponent(self.state)
    
    def _setup_layout(self):
        """Setup the main application layout."""
        # Main header
        main_header = W.HTML(f"""
            <div style='{THEME.header_style}'>
                <h1>SysSimX: System Simulation Framework</h1>
                <h2>Demo Interface</h2>
            </div>
        """)
        
        # Create main layout
        self.widget = W.VBox([
            main_header,
            self.model_selection.widget,
            self.fmu_export.widget,
            self.fmu_instantiation.widget
        ], layout=W.Layout(width='100%'))
    
    def display(self):
        """Display the complete application."""
        display(self.widget)


# =====================================================================
# LEGACY COMPATIBILITY & QUICK ACCESS
# =====================================================================

# Lazy initialization for backward compatibility
_default_app = None

def get_default_ui():
    """Get the default UI widget for backward compatibility."""
    global _default_app
    if _default_app is None:
        _default_app = SysSimXUI()
    return _default_app.widget

# For immediate backward compatibility, create the UI when first accessed
ui = None

# Expose individual components for advanced usage
def get_model_selection_component() -> ModelSelectionComponent:
    """Get the model selection component."""
    global _default_app
    if _default_app is None:
        _default_app = SysSimXUI()
    return _default_app.model_selection

def get_fmu_export_component() -> FMUExportComponent:
    """Get the FMU export component."""
    global _default_app
    if _default_app is None:
        _default_app = SysSimXUI()
    return _default_app.fmu_export

def get_fmu_instantiation_component() -> FMUInstantiationComponent:
    """Get the FMU instantiation component."""
    global _default_app
    if _default_app is None:
        _default_app = SysSimXUI()
    return _default_app.fmu_instantiation

def get_application_state() -> ApplicationState:
    """Get the current application state."""
    global _default_app
    if _default_app is None:
        _default_app = SysSimXUI()
    return _default_app.state

def create_new_ui() -> SysSimXUI:
    """Create a new UI instance with fresh state."""
    return SysSimXUI()


# =====================================================================
# MODULE INITIALIZATION
# =====================================================================

# Initialize the default application
def initialize():
    """Initialize the UI components (called automatically on import)."""
    pass

# Auto-initialize
initialize()