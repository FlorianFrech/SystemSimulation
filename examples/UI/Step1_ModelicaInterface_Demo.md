# Modelica Simulation Interface Demo

This notebook demonstrates the enhanced Modelica file management and simulation UI.

## Features

1. **📁 Package Discovery**: Automatically find all .mo files in a directory
2. **📄 File Management**: View and select multiple Modelica files
3. **👤 User Modes**: Standard and Expert modes with different capabilities
4. **🚀 Simulation Setup**: Configure and run simulations
5. **💾 Configuration**: Save and load simulation configurations
6. **📦 FMU Export**: (Expert mode) Future functionality for FMU generation

## Usage

Simply run the cell below to start the interactive interface:

```python
from SysSimX.ui.step1 import step1_ui

# Start the comprehensive Modelica UI
ui_manager = step1_ui()
```

## Workflow

1. **Select User Mode**: Choose between Standard or Expert mode
2. **Choose Package Directory**: Navigate to your Modelica files directory
3. **Refresh Files**: Click refresh to discover all .mo files
4. **Select Models**: Choose multiple files for simulation
5. **Setup Models**: Validate and prepare models
6. **Configure Simulation**: Set simulation time, step size, and solver
7. **Run Simulation**: Execute the simulation
8. **View Results**: Check simulation outcomes

## Expert Mode Features

In Expert mode, you get access to:
- FMU export functionality
- Advanced simulation parameters
- Extended model configuration options

## Configuration Management

The interface can save and load your settings, including:
- Selected package directory
- Chosen models
- Simulation parameters
- User mode preferences

This makes it easy to resume work on simulation projects.