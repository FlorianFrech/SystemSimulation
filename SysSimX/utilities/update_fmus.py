from path import Path
from OMPython import ModelicaSystem
from shutil import move
from typing import Dict

def get_models_within_package(package_path: Path) -> list[str]:
    """Get all model names within a Modelica package.

    Args:
        package_path (Path): Path to the Modelica package directory.

    Returns:
        list[str]: List of model names within the package.
    """
    model_files = package_path.files("*.mo")
    model_names = [file.stem for file in model_files if file.stem != "package"]
    return model_names

def create_modelica_system(package_file_path: Path, composed_model_name: str) -> ModelicaSystem:
    """Create a ModelicaSystem instance for a given package and model.
    Args:
        package_file_path (Path): Path to the Modelica package file (package.mo).
        composed_model_name (str): Name of the model to be instantiated (e.g., "PackageName.ModelName").
    Returns:
        ModelicaSystem: An instance of ModelicaSystem for the specified model.
    """
    modelica_system = ModelicaSystem(fileName=str(package_file_path),
                                     modelName=composed_model_name)
    return modelica_system

def create_fmu(model: ModelicaSystem, fmuType="cs"):
    """Create an FMU from a ModelicaSystem instance.
    Args:
        model (ModelicaSystem): An instance of ModelicaSystem.
        fmuType (str, optional): Type of FMU to create. Defaults to co-simulation "cs".
    Returns:
        str: Path to the created FMU file.
    """
    model.buildModel()
    fmu_path = model.convertMo2Fmu(fmuType=fmuType)
    return fmu_path

def move_file(src_path, dst_path):
    """Move a file from source to destination.
    Args:
        src_path (str or Path): Source file path.
        dst_path (str or Path): Destination file path.
    """
    move(src_path, dst_path)

def get_fmu_paths(package_path: Path, fmu_output_dir: Path, force_rebuild=False) -> Dict[str, Path]:
    """
    Get paths to FMU files for all models within a Modelica package.
    If FMUs do not exist or force_rebuild is True, generate them.
    Args:
        package_path (Path): Path to the Modelica package directory (e.g., "/path/to/PackageName").
        fmu_output_dir (Path): Directory where the generated FMUs will be stored (e.g., "/path/to/fmus").
        force_rebuild (bool, optional): If True, force the regeneration of FMUs. Defaults to False.
    """
    fmu_paths = {}
    
    package_name = package_path.name
    
    found_model_names = get_models_within_package(package_path)
    found_model_names.sort()

    if not force_rebuild:
        existing_fmus = fmu_output_dir.files("*.fmu")
        existing_fmus.sort()
        existing_model_names = {fmu.stem for fmu in existing_fmus}
        found_model_names = [name for name in found_model_names if name not in existing_model_names]
        found_model_names.sort()
        for fmu in existing_fmus:
            fmu_paths[fmu.stem] = fmu
        if not found_model_names:
            print(f"All FMUs for package '{package_name}' already exist. Skipping generation.")
            return fmu_paths
    
    if not fmu_output_dir.exists():
        fmu_output_dir.mkdir(parents=True)

    package_file_path = package_path / "package.mo"    

    for model_name in found_model_names:
        composed_model_name = f"{package_name}.{model_name}"
        print(f"Processing model: {composed_model_name}")

        model = create_modelica_system(package_file_path, composed_model_name)
        fmu_path = create_fmu(model)

        dst_fmu_path = fmu_output_dir / f"{model_name}.fmu"
        move_file(fmu_path, dst_fmu_path)
        print(f"FMU for {composed_model_name} moved to {dst_fmu_path}")
        fmu_paths[model_name] = dst_fmu_path

    return fmu_paths