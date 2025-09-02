import yaml
import pathlib
from typing import Any, Dict

def load_config(path: str) -> Dict[str, Any]:
    """
    Load a YAML configuration file.
        :param path: Path to the YAML file.
        :return: Configuration as a dictionary.
    """
    with open(pathlib.Path(path), 'r') as f:
        config = yaml.safe_load(f)
    return config