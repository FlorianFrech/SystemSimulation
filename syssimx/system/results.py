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

if TYPE_CHECKING:
    import pandas as pd

    from ..core.history import ModeSwitchEvent
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
        units: Unit metadata aligned with ``histories``.
        events: Recorded event occurrences, as stored by the system history.
        mode_switches: Typed committed switch records keyed by component name.
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
        units: dict[str, dict[str, str | None]] | None = None,
        events: Any = None,
        mode_switches: dict[str, tuple[ModeSwitchEvent, ...]] | None = None,
    ):
        self.system_name = system_name
        self.t0 = t0
        self.tf = tf
        self.dt = dt
        self.wall_time = wall_time
        self.algorithm = algorithm
        self._validate_histories(histories)
        self.histories = histories
        self.units = self._normalize_units(histories, units)
        self.events = events
        self.mode_switches = mode_switches or {}

    @staticmethod
    def _validate_histories(
        histories: dict[str, tuple[np.ndarray, dict[str, np.ndarray]]],
    ) -> None:
        """Reject malformed scientific data instead of silently omitting it."""
        for component, (time_values, ports) in histories.items():
            time_array = np.asarray(time_values)
            if time_array.ndim != 1:
                raise ValueError(f"{component}: time history must be one-dimensional.")
            if time_array.size and not np.all(np.isfinite(time_array.astype(float))):
                raise ValueError(f"{component}: time history must contain only finite values.")
            if time_array.size > 1 and np.any(np.diff(time_array.astype(float)) < 0.0):
                raise ValueError(f"{component}: time history must be monotonically non-decreasing.")

            for port, values in ports.items():
                value_array = np.asarray(values)
                if value_array.ndim == 0:
                    raise ValueError(f"{component}.{port}: value history must have a sample axis.")
                if len(value_array) != len(time_array):
                    raise ValueError(
                        f"{component}.{port}: history has {len(time_array)} timestamps "
                        f"but {len(value_array)} values."
                    )

    @staticmethod
    def _normalize_units(
        histories: dict[str, tuple[np.ndarray, dict[str, np.ndarray]]],
        units: dict[str, dict[str, str | None]] | None,
    ) -> dict[str, dict[str, str | None]]:
        """Return complete unit metadata aligned with the history structure."""
        supplied = units or {}
        unknown_components = set(supplied) - set(histories)
        if unknown_components:
            names = ", ".join(sorted(unknown_components))
            raise ValueError(f"Unit metadata refers to unknown components: {names}.")

        normalized: dict[str, dict[str, str | None]] = {}
        for component, (_, ports) in histories.items():
            component_units = supplied.get(component, {})
            unknown_ports = set(component_units) - set(ports)
            if unknown_ports:
                names = ", ".join(sorted(unknown_ports))
                raise ValueError(f"Unit metadata for {component} refers to unknown ports: {names}.")
            normalized[component] = {port: component_units.get(port) for port in ports}
        return normalized

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
        mode_switches = raw.pop("ModeSwitches", {})
        units = {
            component_name: {
                port_name: port_history.unit
                for port_name, port_history in component.history.get_all_histories().items()
            }
            for component_name, component in system.components.items()
        }
        return cls(
            system_name=system.name,
            t0=t0,
            tf=tf,
            dt=dt,
            wall_time=wall_time,
            algorithm=type(system.algorithm).__name__,
            histories=raw,
            units=units,
            events=events,
            mode_switches=mode_switches,
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
            The requested DataFrame. Long-format data includes a ``unit``
            column. Wide-format data stores ``{port: unit}`` in
            ``DataFrame.attrs['units']``. Values that are pint quantities are
            reduced to their magnitudes.
        """
        pd = _require_pandas()
        if component is not None:
            t_vals, ports = self.histories[component]
            t_arr = np.asarray(t_vals)
            data: dict[str, Any] = {"time": t_arr}
            for port, values in ports.items():
                data[port] = _magnitudes(values)
            frame = pd.DataFrame(data)
            frame.attrs["units"] = dict(self.units[component])
            return frame

        frames = []
        for comp, (t_vals, ports) in self.histories.items():
            t_arr = np.asarray(t_vals)
            for port, values in ports.items():
                vals = _magnitudes(values)
                frames.append(
                    pd.DataFrame(
                        {
                            "component": comp,
                            "port": port,
                            "time": t_arr,
                            "value": vals,
                            "unit": self.units[comp][port],
                        }
                    )
                )
        if not frames:
            return pd.DataFrame(columns=["component", "port", "time", "value", "unit"])
        return pd.concat(frames, ignore_index=True)

    def to_csv(self, path: str | Path, component: str | None = None) -> Path:
        """Write the result to a CSV file and return the written path.

        Args:
            path: Destination file path.
            component: Same semantics as :meth:`to_dataframe`.
        """
        path = Path(path)
        frame = self.to_dataframe(component=component)
        if component is not None:
            frame = frame.rename(
                columns={
                    port: f"{port} [{unit}]"
                    for port, unit in self.units[component].items()
                    if unit is not None
                }
            )
        frame.to_csv(path, index=False)
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


def _require_pandas() -> Any:
    """Import the optional result-table dependency at its point of use."""
    try:
        import pandas as pd
    except ImportError as exc:  # pragma: no cover - depends on installation
        raise ModuleNotFoundError(
            "DataFrame and CSV export require pandas; install 'syssimx[results]'."
        ) from exc
    return pd
