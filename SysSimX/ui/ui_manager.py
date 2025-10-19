"""
File Management and Simulation UI

This module provides a user interface for:
1. Discovering and managing Modelica (.mo) files
2. Viewing and selecting FMU models for simulation
3. Setting up and running simulations
4. Configuring FMU export (future enhancement)
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import List, Dict, Optional, Any
from IPython.display import display, clear_output
import ipywidgets as W
import ipyfilechooser as FC


class UIManager:
    """Main class for managing file UI and simulation workflow"""
    
    def __init__(self):
        self.config_path = Path("sim_config_step1.json")
        self.selected_models: Dict[str, Path] = {}
        self.simulation_results: Dict[str, Any] = {}
        
        # UI Components
        self.mode_toggle = None
        self.pkg_location = None
        self.mo_files_select = None
        self.mo_file_viewer = None
        self.model_config_area = None
        self.simulation_controls = None
        self.results_area = None
        
        # Initialize UI
        self._setup_ui()
    
    def _setup_ui(self):
        """Initialize all UI components"""
        self._create_header()
        self._create_mode_selector()
        self._create_package_selector()
        self._create_file_management_section()
        self._create_simulation_section()
        
    def _create_header(self):
        """Create the main header section"""
        header = W.HTML("""
        <div style='background-color: #DFF2FD; color: #006699; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px;'>
            <h1>SysSimX: System Simulation Framework Interface</h1>
            <h2>Demo User Interface</h2>
        </div>
        """)
        display(header)
    
    def _create_mode_selector(self):
        """Create user mode selector"""
        self.mode_toggle = W.ToggleButtons(
            options=[("Standard", "standard"), ("Expert", "expert")],
            value="standard",
            description="User Mode:",
            style={'description_width': 'initial', 'button_width': '150px'},
            layout=W.Layout(width='400px')
        )
        self.mode_toggle.observe(self._on_mode_change, names='value')
        
        mode_section = W.VBox([
            W.HTML("<h3>User Experience Level</h3>"),
            self.mode_toggle
        ], layout=W.Layout(margin='10px', padding='10px', border='1px solid #ddd'))
        
        display(mode_section)
    
    def _create_package_selector(self):
        """Create package location selector"""
        self.pkg_location = FC.FileChooser(
            title="📁 Select Modelica Package Directory",
            show_hidden=False,
            select_default=True,
            use_dir_icons=True,
            width="100%"
        )
        
        self.pkg_location.register_callback(self._on_package_selected)
        
        # Auto-set to examples directory if it exists
        examples_dir = Path("examples/Modelica")
        if examples_dir.exists():
            self.pkg_location.default_path = str(examples_dir.absolute())
        
        pkg_section = W.VBox([
            W.HTML("<h3>📂 Package Location</h3>"),
            self.pkg_location
        ], layout=W.Layout(margin='10px', padding='10px', border='1px solid #ddd'))
        
        display(pkg_section)
    
    def _create_file_management_section(self):
        """Create file discovery and management section"""
        # File discovery area
        self.discovery_output = W.Output()
        self.refresh_button = W.Button(
            description="🔄 Refresh Files",
            button_style='info',
            layout=W.Layout(width='150px')
        )
        self.refresh_button.on_click(self._refresh_files)
        
        # File selection area
        self.mo_files_select = W.SelectMultiple(
            options=[],
            description="Modelica Files:",
            layout=W.Layout(width='100%', height='200px'),
            style={'description_width': 'initial'}
        )
        self.mo_files_select.observe(self._on_files_selected, names='value')
        
        # File viewer
        self.mo_file_viewer = W.Textarea(
            value="Select a file to view its content...",
            description="File Content:",
            layout=W.Layout(width='100%', height='300px'),
            disabled=True,
            style={'description_width': 'initial'}
        )
        
        # Single file dropdown for viewing
        self.single_file_dropdown = W.Dropdown(
            options=[],
            description="View File:",
            style={'description_width': 'initial'},
            layout=W.Layout(width='300px')
        )
        self.single_file_dropdown.observe(self._on_single_file_selected, names='value')
        
        file_section = W.VBox([
            W.HTML("<h3>📄 Modelica File Management</h3>"),
            W.HBox([self.refresh_button]),
            self.discovery_output,
            W.HTML("<b>Select Multiple Files for Simulation:</b>"),
            self.mo_files_select,
            W.HTML("<b>File Viewer:</b>"),
            W.HBox([self.single_file_dropdown]),
            self.mo_file_viewer
        ], layout=W.Layout(margin='10px', padding='10px', border='1px solid #ddd'))
        
        display(file_section)
    
    def _create_simulation_section(self):
        """Create simulation setup and control section"""
        # Model configuration
        self.model_config_area = W.VBox([
            W.HTML("<p><em>Select Modelica files first to configure models...</em></p>")
        ])
        
        # Simulation parameters
        self.sim_time = W.FloatText(value=10.0, description='Sim Time (s):', style={'description_width': 'initial'})
        self.time_step = W.FloatText(value=0.01, description='Time Step (s):', style={'description_width': 'initial'})
        self.solver = W.Dropdown(
            options=['euler', 'runge-kutta', 'dassl'],
            value='euler',
            description='Solver:',
            style={'description_width': 'initial'}
        )
        
        # Control buttons
        self.setup_button = W.Button(description="⚙️ Setup Models", button_style='warning', disabled=True)
        self.run_button = W.Button(description="▶️ Run Simulation", button_style='success', disabled=True)
        self.export_fmu_button = W.Button(description="📦 Export as FMU", button_style='info', disabled=True)
        
        self.setup_button.on_click(self._setup_models)
        self.run_button.on_click(self._run_simulation)
        self.export_fmu_button.on_click(self._export_fmu)
        
        # Results area
        self.results_area = W.Output()
        
        sim_section = W.VBox([
            W.HTML("<h3>🚀 Simulation Configuration</h3>"),
            W.HTML("<b>Selected Models Configuration:</b>"),
            self.model_config_area,
            W.HTML("<b>Simulation Parameters:</b>"),
            W.HBox([self.sim_time, self.time_step, self.solver]),
            W.HTML("<b>Actions:</b>"),
            W.HBox([self.setup_button, self.run_button, self.export_fmu_button]),
            W.HTML("<b>Results:</b>"),
            self.results_area
        ], layout=W.Layout(margin='10px', padding='10px', border='1px solid #ddd'))
        
        display(sim_section)
    
    def _on_mode_change(self, change):
        """Handle mode change"""
        mode = change['new']
        if mode == 'expert':
            self.export_fmu_button.disabled = False
            # Show additional expert options
        else:
            self.export_fmu_button.disabled = True
    
    def _on_package_selected(self, chooser):
        """Handle package directory selection"""
        self._refresh_files(None)
    
    def _refresh_files(self, button):
        """Refresh and discover Modelica files"""
        with self.discovery_output:
            clear_output(wait=True)
            
            if not self.pkg_location.selected_path:
                print("❌ Please select a package directory first!")
                return
            
            pkg_path = Path(self.pkg_location.selected_path)
            
            # Discover .mo files recursively
            mo_files = []
            for pattern in ['*.mo', '**/*.mo']:
                mo_files.extend(list(pkg_path.glob(pattern)))
            
            # Remove duplicates and sort
            mo_files = sorted(list(set(mo_files)))
            
            print(f"🔍 Discovered {len(mo_files)} Modelica files in {pkg_path}")
            
            # Update file selectors
            file_options = [(f.name, f) for f in mo_files]
            self.mo_files_select.options = file_options
            self.single_file_dropdown.options = [('Select a file...', None)] + file_options
            
            if mo_files:
                print("✅ Files loaded successfully!")
                for f in mo_files[:5]:  # Show first 5 files
                    print(f"  📄 {f.relative_to(pkg_path)}")
                if len(mo_files) > 5:
                    print(f"  ... and {len(mo_files) - 5} more files")
            else:
                print("⚠️ No .mo files found in the selected directory")
    
    def _on_files_selected(self, change):
        """Handle multiple file selection for simulation"""
        selected_files = change['new']
        self.selected_models = {f.stem: f for f in selected_files}
        
        if selected_files:
            self.setup_button.disabled = False
            self._update_model_config_display()
        else:
            self.setup_button.disabled = True
            self._clear_model_config_display()
    
    def _on_single_file_selected(self, change):
        """Handle single file selection for viewing"""
        selected_file = change['new']
        if selected_file and selected_file.exists():
            try:
                with open(selected_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.mo_file_viewer.value = content
            except Exception as e:
                self.mo_file_viewer.value = f"Error reading file: {str(e)}"
        else:
            self.mo_file_viewer.value = "Select a file to view its content..."
    
    def _update_model_config_display(self):
        """Update the model configuration display"""
        config_widgets = [W.HTML("<p>📋 <b>Selected Models for Simulation:</b></p>")]
        
        for model_name, file_path in self.selected_models.items():
            model_info = W.HTML(f"""
            <div style='background: #f8f9fa; padding: 10px; margin: 5px 0; border-radius: 5px;'>
                <b>Model:</b> {model_name}<br>
                <b>File:</b> {file_path.name}<br>
                <b>Path:</b> {file_path.parent}
            </div>
            """)
            config_widgets.append(model_info)
        
        self.model_config_area.children = config_widgets
    
    def _clear_model_config_display(self):
        """Clear the model configuration display"""
        self.model_config_area.children = [
            W.HTML("<p><em>Select Modelica files first to configure models...</em></p>")
        ]
    
    def _setup_models(self, button):
        """Setup and validate selected models"""
        with self.results_area:
            clear_output(wait=True)
            print("⚙️ Setting up models...")
            
            # Basic validation
            for model_name, file_path in self.selected_models.items():
                print(f"📝 Validating {model_name}...")
                if not self._validate_modelica_file(file_path):
                    print(f"❌ Validation failed for {model_name}")
                    return
                print(f"✅ {model_name} validated successfully")
            
            print("🎯 All models setup completed!")
            self.run_button.disabled = False
    
    def _validate_modelica_file(self, file_path: Path) -> bool:
        """Basic validation of Modelica file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Basic checks
            if 'model ' in content or 'package ' in content:
                return True
            return False
        except Exception:
            return False
    
    def _run_simulation(self, button):
        """Run simulation with selected models"""
        with self.results_area:
            clear_output(wait=True)
            print("🚀 Starting simulation...")
            print(f"⏱️ Simulation time: {self.sim_time.value} seconds")
            print(f"🔢 Time step: {self.time_step.value} seconds")
            print(f"🔧 Solver: {self.solver.value}")
            
            # Mock simulation for demonstration
            import time
            for i, (model_name, _) in enumerate(self.selected_models.items()):
                print(f"📊 Simulating {model_name}... ", end='')
                time.sleep(0.5)  # Simulate computation time
                print("✅ Complete")
            
            print("\n🎉 Simulation completed successfully!")
            
            # Generate mock results
            self._display_results()
    
    def _display_results(self):
        """Display simulation results"""
        results_html = """
        <div style='background: #e8f5e8; padding: 15px; border-radius: 8px; margin-top: 10px;'>
            <h4>📈 Simulation Results</h4>
            <p><b>Status:</b> ✅ Successful</p>
            <p><b>Models Simulated:</b> """ + str(len(self.selected_models)) + """</p>
            <p><b>Total Simulation Time:</b> """ + f"{self.sim_time.value}" + """ seconds</p>
            <p><em>Note: This is a demo interface. Actual simulation results would be displayed here.</em></p>
        </div>
        """
        
        with self.results_area:
            display(W.HTML(results_html))
    
    def _export_fmu(self, button):
        """Export models as FMU (Expert mode)"""
        with self.results_area:
            clear_output(wait=True)
            print("📦 Exporting models as FMU...")
            print("⚠️ FMU export functionality will be implemented in future versions")
            
            # Future implementation:
            # - Use OMCompiler to compile models
            # - Generate FMU files
            # - Save to specified directory
    
    def save_config(self):
        """Save current configuration"""
        config = {
            'mode': self.mode_toggle.value if self.mode_toggle else 'standard',
            'package_path': self.pkg_location.selected_path if self.pkg_location else '',
            'selected_models': {name: str(path) for name, path in self.selected_models.items()},
            'sim_params': {
                'time': self.sim_time.value if self.sim_time else 10.0,
                'step': self.time_step.value if self.time_step else 0.01,
                'solver': self.solver.value if self.solver else 'euler'
            }
        }
        
        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"💾 Configuration saved to {self.config_path}")
    
    def load_config(self):
        """Load previously saved configuration"""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            
            # Apply loaded configuration
            if self.mode_toggle and 'mode' in config:
                self.mode_toggle.value = config['mode']
            
            # Note: Other widgets would be restored here
            print(f"📂 Configuration loaded from {self.config_path}")
        else:
            print("ℹ️ No saved configuration found")


def step1_ui():
    """
    Main entry point for the Modelica UI interface.
    
    Creates and displays a comprehensive interface for:
    - Discovering Modelica files in a package directory
    - Viewing and selecting multiple files
    - Configuring simulation parameters
    - Running simulations (demo)
    - Future: FMU export functionality
    
    Returns:
        ModelicaUIManager: The UI manager instance for further interaction
    """
    manager = UIManager()
    
    # Add save/load controls at the bottom
    save_button = W.Button(description="💾 Save Config", button_style='primary')
    load_button = W.Button(description="📂 Load Config", button_style='info')
    
    def save_config(b):
        manager.save_config()
    
    def load_config(b):
        manager.load_config()
    
    save_button.on_click(save_config)
    load_button.on_click(load_config)
    
    config_section = W.VBox([
        W.HTML("<h3>💾 Configuration Management</h3>"),
        W.HBox([save_button, load_button])
    ], layout=W.Layout(margin='10px', padding='10px', border='1px solid #ddd'))
    
    display(config_section)
    
    return manager


# Convenience function for quick testing
def demo_ui():
    """Quick demo of the UI with example data"""
    print("🎬 Starting Modelica UI Demo...")
    return step1_ui()

