from __future__ import annotations
from pathlib import Path
from typing import Iterable, Tuple

from ..state import AppState
from ...utilities.update_fmus import create_modelica_system, create_fmu, move_file

def ensure_export_dir(state: AppState) -> Path:
    d = state.export_dir()
    if not d.exists():
        if state.create_missing_dirs:
            d.mkdir(parents=True, exist_ok=True)
        else:
            raise FileNotFoundError(f"Export directory {d} does not exist.")
    if not d.is_dir():
        raise NotADirectoryError(f"Export path {d} is not a directory.")
    return d

def export_models_to_fmus(state: AppState, package_name: str = "ControlledPendulum") -> Tuple[Path, list[Path]]:
    """
    Exports the currently selected .mo models to FMUs in state's directory.
    """
    export_dir = ensure_export_dir(state)
    outputs: list[Path] = []
    for model_path in state.selected_models:
        model_name = model_path.stem
        dest_path = export_dir / f"{model_name}.fmu"
        package_path = model_path.parent / "package.mo"
        composed = f"{package_name}.{model_name}"

        # 1) Create Modelica system
        modelica_system = create_modelica_system(package_path, composed)
        
        # 2) Create FMU
        src_fmu = create_fmu(modelica_system, composed)

        # 3) Move FMU to destination
        move_file(src_fmu, dest_path)
        outputs.append(dest_path)

    return export_dir, outputs
