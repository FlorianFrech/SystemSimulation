from pathlib import Path
from typing import List, Dict, Any

from .model import Model

class Package:
    """Class representing a system model."""
    name: str
    path: Path
    def __init__(self, name: str, path: Path):
        self.name = name
        self.path = path
        self.create_system_directory()
        self.create_modelica_package()

    def create_system_directory(self) -> None:
        """Creates a directory for the system model."""
        self.path.mkdir(parents=True, exist_ok=True)

    def create_modelica_package(self) -> None:
        """Creates a Modelica package file."""
        package_file = self.path / "package.mo"
        with package_file.open('w') as f:
            f.write(f"package {self.name}\nend {self.name};\n")
        print(f"{package_file} created.")

