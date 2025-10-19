from __future__ import annotations
from pathlib import Path
import pandas as pd

from ...core.fmu_comp import FMUComponent

def preview_fmu(path: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    Returns (inputs_df, outputs_df, parameters_dict) without presisting the FMUComponent.
    """
    tmp = FMUComponent(name="__preview__", fmu_path=path)
    in_rows = [{'name': name, 'type': spec['type']} for name, spec in tmp.inputs.items()]
    out_rows = [{'name': name, 'type': spec['type']} for name, spec in tmp.outputs.items()]
    return (pd.DataFrame(in_rows), pd.DataFrame(out_rows), tmp.parameters)