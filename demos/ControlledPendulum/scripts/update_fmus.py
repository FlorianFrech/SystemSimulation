import os
from functools import lru_cache
from pathlib import Path
from shutil import move

from OMPython import ModelicaSystem

# The tracked FMUs under demos/ControlledPendulum/artifacts/fmus are built with
# this compiler, and syssimx.components.fmu carries a CVODE workaround that was
# isolated against it. Rebuilding with another OpenModelica therefore changes
# artifacts the rest of the project treats as fixed.
OMC_VERSION_PINNED = "1.26.3"


@lru_cache(maxsize=None)
def pin_openmodelica() -> str:
    """Pin and report the OpenModelica that builds every FMU in this module.

    OMPython resolves omc through OPENMODELICAHOME and PATH, so a second
    OpenModelica installation on the machine silently changes which compiler
    produces the artifacts. ``SYSSIMX_OM_HOME`` selects the installation;
    ``SYSSIMX_OM_ALLOW_ANY=1`` lifts the check for a deliberate experiment.
    """
    from OMPython import OMCSessionZMQ

    om_home = os.environ.get("SYSSIMX_OM_HOME")
    if om_home:
        os.environ["OPENMODELICAHOME"] = om_home

    session = OMCSessionZMQ()
    try:
        version = str(session.sendExpression("getVersion()")).strip()
    finally:
        del session

    if (OMC_VERSION_PINNED not in version
            and os.environ.get("SYSSIMX_OM_ALLOW_ANY") != "1"):
        raise RuntimeError(
            f"The tracked FMUs are built with OpenModelica "
            f"{OMC_VERSION_PINNED}, but omc reports {version!r}. Set "
            f"SYSSIMX_OM_HOME to the pinned installation, or "
            f"SYSSIMX_OM_ALLOW_ANY=1 to rebuild with another toolchain "
            f"deliberately."
        )
    return version


def get_models_within_package(package_path: Path) -> list[str]:
    """Get all model names within a Modelica package.

    Args:
        package_path (Path): Path to the Modelica package directory.

    Returns:
        list[str]: List of model names within the package.
    """
    model_files = package_path.glob("*.mo")
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
    pin_openmodelica()
    modelica_system = ModelicaSystem(
        fileName=str(package_file_path),
        modelName=composed_model_name,
        commandLineOptions="--fmiFlags=s:cvode",
    )
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


def get_fmu_paths(package_path: Path, fmu_output_dir: Path, force_rebuild=False) -> dict[str, Path]:
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
        existing_fmus = fmu_output_dir.glob("*.fmu")
        existing_fmus = sorted(existing_fmus)
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
        print(80 * "#")
        print(f"Processing model: {composed_model_name}")

        model = create_modelica_system(package_file_path, composed_model_name)
        fmu_path = create_fmu(model)

        dst_fmu_path = fmu_output_dir / f"{model_name}.fmu"
        move_file(fmu_path, dst_fmu_path)
        print(f"FMU for {composed_model_name} moved to:\n{dst_fmu_path}\n")
        fmu_paths[model_name] = dst_fmu_path

    return fmu_paths
