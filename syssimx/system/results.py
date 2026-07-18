"""Simulation result container for SysSimX runs.

``SimulationResult`` wraps the per-component output histories recorded during
a run together with run metadata (time span, macro step, wall time, algorithm)
and provides convenient post-processing accessors: pandas ``DataFrame``
conversion (tidy long format or per-component wide format), CSV export, and
the recorded event log.

A result is returned by :meth:`syssimx.system.system.System.run` and can also
be built from an already-run system via :meth:`SimulationResult.from_system`.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from .system import System


class SimulationResult:
    """Container for the outputs and metadata of one simulation run.

    Attributes:
        system_name: Name of the simulated system.
        t0: Start time of the run in seconds.
        tf: End time of the run in seconds.
        dt: Macro communication step size in seconds.
        wall_time: Wall-clock duration of the run in seconds.
        algorithm: Name of the master algorithm used.
        histories: Mapping ``component name -> (time_array, {port: values})``
            exactly as returned by ``CoSimComponent.get_history_arrays()``.
        events: Recorded event occurrences, as stored by the system history.
    """

    def __init__(
        self,
        system_name: str,
        t0: float,
        tf: float,
        dt: float,
        wall_time: float,
        algorithm: str,
        histories: dict[str, tuple[np.ndarray, dict[str, np.ndarray]]],
        events: Any = None,
    ):
        self.system_name = system_name
        self.t0 = t0
        self.tf = tf
        self.dt = dt
        self.wall_time = wall_time
        self.algorithm = algorithm
        self.histories = histories
        self.events = events

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------
    @classmethod
    def from_system(
        cls,
        system: System,
        t0: float,
        tf: float,
        dt: float,
        wall_time: float = float("nan"),
    ) -> SimulationResult:
        """Build a result from an already-run system.

        Args:
            system: The system whose component histories to capture.
            t0: Start time of the run.
            tf: End time of the run.
            dt: Macro step size used.
            wall_time: Optional wall-clock duration in seconds.
        """
        raw = system.get_history()
        events = raw.pop("Events", None)
        return cls(
            system_name=system.name,
            t0=t0,
            tf=tf,
            dt=dt,
            wall_time=wall_time,
            algorithm=type(system.algorithm).__name__,
            histories=raw,
            events=events,
        )

    # ------------------------------------------------------------------
    # Access
    # ------------------------------------------------------------------
    @property
    def component_names(self) -> list[str]:
        """Names of all components with recorded history."""
        return list(self.histories.keys())

    def __getitem__(self, component: str) -> tuple[np.ndarray, dict[str, np.ndarray]]:
        """Return ``(time_array, {port: values})`` for one component."""
        return self.histories[component]

    def __contains__(self, component: str) -> bool:
        return component in self.histories

    def __repr__(self) -> str:
        return (
            f"<SimulationResult '{self.system_name}' t=[{self.t0}, {self.tf}] "
            f"dt={self.dt} components={len(self.histories)} "
            f"algorithm={self.algorithm}>"
        )

    # ------------------------------------------------------------------
    # DataFrame conversion and export
    # ------------------------------------------------------------------
    def to_dataframe(self, component: str | None = None) -> pd.DataFrame:
        """Convert recorded histories to a pandas DataFrame.

        Args:
            component: When given, return a wide DataFrame for that single
                component: one ``time`` column plus one column per output
                port. Without it, return a tidy long-format DataFrame with
                columns ``component``, ``port``, ``time``, ``value`` covering
                every component (components may have different time grids,
                which the long format represents without padding).

        Returns:
            The requested DataFrame. Values that are pint quantities are
            reduced to their magnitudes.
        """
        if component is not None:
            t_vals, ports = self.histories[component]
            t_arr = np.asarray(t_vals)
            data: dict[str, Any] = {"time": t_arr}
            for port, values in ports.items():
                vals = _magnitudes(values)
                if len(vals) != len(t_arr):
                    # Defensive: skip ports whose sampling does not align with
                    # the component time grid (mirrors the long-format path).
                    continue
                data[port] = vals
            return pd.DataFrame(data)

        frames = []
        for comp, (t_vals, ports) in self.histories.items():
            t_arr = np.asarray(t_vals)
            for port, values in ports.items():
                vals = _magnitudes(values)
                if len(vals) != len(t_arr):
                    # Defensive: skip ports whose sampling does not align
                    # with the component time grid (e.g. never-set ports).
                    continue
                frames.append(
                    pd.DataFrame(
                        {
                            "component": comp,
                            "port": port,
                            "time": t_arr,
                            "value": vals,
                        }
                    )
                )
        if not frames:
            return pd.DataFrame(columns=["component", "port", "time", "value"])
        return pd.concat(frames, ignore_index=True)

    def to_csv(self, path: str | Path, component: str | None = None) -> Path:
        """Write the result to a CSV file and return the written path.

        Args:
            path: Destination file path.
            component: Same semantics as :meth:`to_dataframe`.
        """
        path = Path(path)
        self.to_dataframe(component=component).to_csv(path, index=False)
        return path


def _magnitudes(values: Any) -> np.ndarray:
    """Reduce an array (possibly of pint quantities) to plain magnitudes."""
    arr = np.asarray(values)
    if arr.dtype == object:
        return np.asarray(
            [v.magnitude if hasattr(v, "magnitude") else v for v in arr.ravel()]
        ).reshape(arr.shape)
    if hasattr(values, "magnitude"):
        return np.asarray(values.magnitude)
    return arr
