import opensim as osim
from opensim import TimeSeriesTable, STOFileAdapter
import numpy as np
from typing import Dict

def create_opensim_mot_file(data: Dict[str, np.ndarray], time: np.ndarray, filename: str):
    """
    Create an OpenSim .mot file from simulation data.
        :param data: Dictionary where keys are variable names and values are numpy arrays of shape (n_time_steps,).
        :param time: Numpy array of time steps of shape (n_time_steps,).
        :param filename: Name of the output .mot file.
    """
    n_time_steps = time.shape[0]
    table = TimeSeriesTable()

    table.setColumnLabels(list(data.keys()))
    
    # Append data rows to the table
    for i in range(n_time_steps):
        n_data = len(data.keys())
        row = osim.RowVector(n_data)
        for j, key in enumerate(data.keys()):
            row[j] = data[key][i]
        table.appendRow(time[i], row)
    
    # Write to .mot file
    adapter = STOFileAdapter()
    adapter.write(table, filename)