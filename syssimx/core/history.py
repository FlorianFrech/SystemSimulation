"""History management for ports, components, and systems.

This module provides classes to store, retrieve, and manage
history data for port variables, components, and entire systems
during co-simulation runs.

Overview of Classes:
- PortHistory: Stores time series data for a single port variable.
- ComponentHistory: Manages PortHistory instances for all ports of a component.
- SystemHistory: Manages ComponentHistory instances for all components in a system,
  along with event recording.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import numpy as np

from ..utilities.units import QuantityClass, QuantityType, ureg
from .events import DenseTime


# -------------------------------------------------------------------
# Port History - stores time series data for a single port variable
# -------------------------------------------------------------------
@dataclass
class PortHistory:
    """Stores and manages time-series history of a port's values.

    This class maintains a chronological record of values associated with timestamps,
    with optional unit support and conversion capabilities. It provides efficient
    storage using lists internally while exposing numpy arrays for analysis.

    Attributes:
        port_name: The name of the port this history belongs to.
        unit: The unit of measurement for the values stored in this history.

    Example:
        >>> history = PortHistory(port_name="temperature", unit="celsius")
        >>> history.append(0.0, 25.0)
        >>> history.append(1.0, 26.5)
        >>> print(history.time)
        [0. 1.]
        >>> print(history.values)
        [25.  26.5]
    """

    port_name: str
    unit: str | None = None
    _timestamps: list[float] = field(default_factory=list)
    _values: list[float | int | bool | str] = field(default_factory=list)

    def append(self, t: float, value: float | int | bool | str | QuantityType) -> None:
        """Append a new time-value pair to the history."""
        self._timestamps.append(t)
        if isinstance(value, QuantityClass):
            self._values.append(value.magnitude)
        else:
            self._values.append(cast(float | int | bool | str, value))

    def clear(self) -> None:
        """Clear the history."""
        self._timestamps.clear()
        self._values.clear()

    @property
    def time(self) -> np.ndarray:
        """Get timestamps as a numpy array."""
        return np.array(self._timestamps)

    @property
    def values(self) -> np.ndarray:
        """Get values as a numpy array."""
        return np.array(self._values)

    def get_values(self, as_unit: str | None = None) -> np.ndarray:
        """Get values as a numpy array, converting to the specified unit if applicable."""
        vals = self.values
        if as_unit and self.unit and as_unit != self.unit:
            # Convert entire array at once
            converted = ureg.Quantity(vals, self.unit).to(as_unit)
            return cast(np.ndarray, np.asarray(converted.magnitude))
        return vals

    def to_dict(self, as_unit: str | None = None) -> dict[str, Any]:
        """Get the history as a dictionary with 'time' array, 'values' array, and unit."""
        return {
            "time": self.time,
            "values": self.get_values(as_unit),
            "unit": as_unit if as_unit else self.unit,
        }

    def to_tuple(self, as_unit: str | None = None) -> tuple[np.ndarray, np.ndarray, str | None]:
        """Export history as tuple (time, values, unit)."""
        if as_unit:
            return self.time, self.get_values(as_unit), as_unit
        return self.time, self.get_values(as_unit), self.unit

    def __len__(self) -> int:
        """Get the number of entries in the history."""
        return len(self._timestamps)

    def __bool__(self) -> bool:
        """Check if the history has any entries."""
        return len(self) > 0


# -------------------------------------------------------------------
# Component History - stores time series data for all ports of a component
# -------------------------------------------------------------------
@dataclass
class ComponentHistory:
    """Manages the collection of port histories for a single component.

    This class provides convenient access patterns for retrieving and
    manipulating trajectory data across all ports of a component.

    Attributes:
        component_name: Name of the component whose ports are tracked.

    Example:
        >>> history = ComponentHistory(component_name="Tank1")
        >>> history.add_port("temperature", unit="K")
        >>> history.append("temperature", t=0.0, value=300.0)
        >>> history.append("temperature", t=1.0, value=305.0)
        >>> port_hist = history.get_port_history("temperature")
    """

    component_name: str
    _port_histories: dict[str, PortHistory] = field(default_factory=dict)

    def add_port(self, port_name: str, unit: str | None = None) -> None:
        """Register a port for history tracking."""
        if port_name not in self._port_histories:
            self._port_histories[port_name] = PortHistory(port_name=port_name, unit=unit)

    def append(self, port_name: str, t: float, value: Any) -> None:
        """Append value to port history."""
        if port_name not in self._port_histories:
            raise KeyError(f"Port '{port_name}' not registered for history tracking")
        self._port_histories[port_name].append(t, value)

    def get_port_history(self, port_name: str) -> PortHistory:
        """Get history object for a specific port."""
        if port_name not in self._port_histories:
            raise KeyError(f"No history for port '{port_name}'")
        return self._port_histories[port_name]

    def get_all_histories(self) -> dict[str, PortHistory]:
        """Get all port histories as dictionary."""
        return dict(self._port_histories)

    def to_dict(
        self, port_names: list[str] | None = None, units: dict[str, str] | None = None
    ) -> dict[str, dict[str, Any]]:
        """Export histories as nested dictionary.

        Args:
            port_names: List of ports to export. If None, exports all.
            units: Dict mapping port names to desired units for conversion.

        Returns:
            Dict mapping port names to their history dicts.
        """
        ports = port_names if port_names else list(self._port_histories.keys())
        result = {}

        for port in ports:
            if port not in self._port_histories:
                continue
            target_unit = units.get(port) if units else None
            result[port] = self._port_histories[port].to_dict(as_unit=target_unit)

        return result

    def to_arrays(
        self, port_names: list[str] | None = None, units: dict[str, str] | None = None
    ) -> tuple[np.ndarray, dict[str, np.ndarray]]:
        """Export as common time array and dict of value arrays.

        Args:
            port_names: List of ports to export. If None, exports all.
            units: Dict mapping port names to desired units.

        Returns:
            Tuple of (time_array, {port_name: values_array})
        """
        ports = port_names if port_names else list(self._port_histories.keys())

        if not ports:
            return np.array([]), {}

        # Get common time array from first port
        time = self._port_histories[ports[0]].time

        values_dict = {}
        for port in ports:
            if port not in self._port_histories:
                continue
            target_unit = units.get(port) if units else None
            values_dict[port] = self._port_histories[port].get_values(as_unit=target_unit)

        return time, values_dict

    def clear(self, port_names: list[str] | None = None) -> None:
        """Clear history for specified ports or all ports."""
        ports = port_names if port_names else list(self._port_histories.keys())
        for port in ports:
            if port in self._port_histories:
                self._port_histories[port].clear()

    def __len__(self) -> int:
        """Number of ports with history."""
        return len(self._port_histories)

    def __contains__(self, port_name: str) -> bool:
        """Check if port has history."""
        return port_name in self._port_histories


# -------------------------------------------------------------------
# System History - stores time series data for components in a system
# -------------------------------------------------------------------
@dataclass
class SystemHistory:
    """Manages simulation history data for an entire system.

    This class serves as a container for component-level histories and event recordings
    in a system simulation. It provides methods for storing, retrieving, and persisting
    simulation results across multiple components and their ports.

    Attributes:
        system_name: Name identifier for the system.

    Key Features:

    - Component history management: Register and retrieve histories for individual components
    - Event recording: Track discrete event occurrences with timestamps
    - Flexible data retrieval: Export histories in nested or flat dictionary formats
    - Unit conversion: Support for automatic unit conversion during data retrieval
    - Persistence: Save/load simulation results to/from CSV files

    Example:
        >>> history = SystemHistory(system_name="my_system")
        >>> history.add_component("motor", motor_history)
        >>> history.record_event("motor", "start", 0.5)
        >>> trajectory = history.get_port_trajectory("motor", "speed")
        >>> history.save_csv(Path("results.csv"))
    """

    system_name: str
    _component_histories: dict[str, ComponentHistory] = field(default_factory=dict)
    _event_histories: dict[tuple[str, str], list[DenseTime]] = field(
        default_factory=dict
    )  # (component, event_name) -> times

    def add_component(self, component_name: str, component_history: ComponentHistory) -> None:
        """Register a component's history."""
        self._component_histories[component_name] = component_history

    def get_component_history(self, component_name: str) -> ComponentHistory:
        """Get history object for a specific component."""
        if component_name not in self._component_histories:
            raise KeyError(f"No history for component '{component_name}'")
        return self._component_histories[component_name]

    def get_all_histories(self) -> dict[str, ComponentHistory]:
        """Get all component histories as dictionary."""
        return dict(self._component_histories)

    def record_event(self, component_name: str, event_name: str, t: DenseTime) -> None:
        """Record an event occurrence time."""
        key = (component_name, event_name)
        if key not in self._event_histories:
            self._event_histories[key] = []
        self._event_histories[key].append(t)

    def get_event_history(self, component_name: str, event_name: str) -> list[DenseTime]:
        """Get recorded times for a specific event."""
        key = (component_name, event_name)
        return self._event_histories.get(key, [])

    def get_all_event_histories(self) -> dict[tuple[str, str], list[DenseTime]]:
        """Get all recorded event histories."""
        return dict(self._event_histories)

    # ----------------------------------------------------------------------------
    # Retrieval Methods
    # ----------------------------------------------------------------------------
    def to_dict(
        self,
        component_names: list[str] | None = None,
        port_names: dict[str, list[str]] | None = None,
        units: dict[str, dict[str, str]] | None = None,
        format: str = "nested",
    ) -> dict[str, Any]:
        """Retrieve histories from components in the system.

        Args:
            component_names: List of components to retrieve. If None, retrieves all.
            port_names: Dict mapping component names to lists of port names to retrieve.
                       If None, retrieves all ports for each component.
            units: Nested dict {comp_name: {port_name: target_unit}} for unit conversion.
            format: 'nested' or 'flat'
                   - 'nested': {'comp1': {'port1': {...}, 'port2': {...}}, 'comp2': {...}}
                   - 'flat': {'comp1.port1': {...}, 'comp2.port2': {...}}

        Returns:
            Dictionary with component/port histories based on format.
        """
        comps = component_names if component_names else list(self._component_histories.keys())

        if format == "nested":
            result = {}
            for comp_name in comps:
                if comp_name not in self._component_histories:
                    continue

                comp_hist = self._component_histories[comp_name]
                ports = port_names.get(comp_name) if port_names else None
                comp_units = units.get(comp_name) if units else None

                result[comp_name] = comp_hist.to_dict(port_names=ports, units=comp_units)
            return result

        elif format == "flat":
            result = {}
            for comp_name in comps:
                if comp_name not in self._component_histories:
                    continue

                comp_hist = self._component_histories[comp_name]
                ports = port_names.get(comp_name) if port_names else None
                comp_units = units.get(comp_name) if units else None

                comp_data = comp_hist.to_dict(port_names=ports, units=comp_units)

                # Flatten: comp.port as key
                for port_name, port_data in comp_data.items():
                    flat_key = f"{comp_name}.{port_name}"
                    result[flat_key] = port_data
            return result
        else:
            raise ValueError(f"Unknown format '{format}'. Use 'nested' or 'flat'.")

    def to_arrays(
        self,
        component_names: list[str] | None = None,
        port_names: dict[str, list[str]] | None = None,
        units: dict[str, dict[str, str]] | None = None,
    ) -> dict[str, tuple[np.ndarray, dict[str, np.ndarray]]]:
        """Get histories as numpy arrays per component.

        Args:
            component_names: List of components to retrieve. If None, retrieves all.
            port_names: Dict mapping component names to lists of port names.
            units: Nested dict for unit conversion.

        Returns:
            Dict mapping component names to (time_array, values_dict) tuples.
        """
        comps = component_names if component_names else list(self._component_histories.keys())
        result = {}

        for comp_name in comps:
            if comp_name not in self._component_histories:
                continue

            comp_hist = self._component_histories[comp_name]
            ports = port_names.get(comp_name) if port_names else None
            comp_units = units.get(comp_name) if units else None

            result[comp_name] = comp_hist.to_arrays(port_names=ports, units=comp_units)

        return result

    def get_port_trajectory(
        self, component: str, port: str, as_unit: str | None = None
    ) -> tuple[np.ndarray, np.ndarray]:
        """Get time and value arrays for a specific port (convenience method).

        Args:
            component: Component name
            port: Port name
            as_unit: Target unit for conversion

        Returns:
            Tuple of (time_array, values_array)
        """
        if component not in self._component_histories:
            raise KeyError(f"Component '{component}' not found in history")

        comp_hist = self._component_histories[component]
        port_hist = comp_hist.get_port_history(port)

        return port_hist.time, port_hist.get_values(as_unit=as_unit)

    def clear(
        self,
        component_names: list[str] | None = None,
        port_names: dict[str, list[str]] | None = None,
    ) -> None:
        """Clear histories for specified components and ports."""
        comps = component_names if component_names else list(self._component_histories.keys())

        for comp_name in comps:
            if comp_name not in self._component_histories:
                continue

            comp_hist = self._component_histories[comp_name]
            ports = port_names.get(comp_name) if port_names else None
            comp_hist.clear(port_names=ports)

    # -------------------------------------------------------------------
    # Persistence Methods
    # -------------------------------------------------------------------
    def save_csv(
        self,
        filepath: Path,
        component_names: list[str] | None = None,
        port_names: dict[str, list[str]] | None = None,
        units: dict[str, dict[str, str]] | None = None,
        long_format: bool = False,
    ) -> None:
        """Save as single CSV file.

        Args:
            filepath: Output CSV file path
            component_names: Components to save. If None, saves all.
            port_names: Specific ports to save per component.
            units: Unit conversion specifications.
            long_format: If True, uses long/tidy format (time, component, port, value).
                        If False, uses wide format (time, comp1.port1, comp1.port2, ...).

        Format:
            time, ref.q_ref, pendulum.q, pendulum.omega, ...
            0.0,  1.57,      0.0,         0.0,            ...
            0.01, 1.55,      0.015,       0.3,            ...
        """
        filepath.parent.mkdir(parents=True, exist_ok=True)

        # Get histories in flat format
        histories = self.to_dict(
            component_names=component_names, port_names=port_names, units=units, format="flat"
        )

        if not histories:
            print("No data to save.")
            return

        # Get all time points (assuming all signals have same time base)
        first_key = next(iter(histories.keys()))
        time_array = histories[first_key]["time"]

        # Build header rows
        signal_names = list(histories.keys())
        units_row = []

        for signal in signal_names:
            unit = histories[signal].get("unit", "-")
            units_row.append(unit if unit else "-")

        # Write CSV
        with open(filepath, "w", newline="") as f:
            writer = csv.writer(f)

            # Header row 1: signal names
            writer.writerow(["time"] + signal_names)

            # Header row 2: units
            writer.writerow(["s"] + units_row)

            # Data rows
            n_points = len(time_array)
            for i in range(n_points):
                row = [time_array[i]]
                for signal in signal_names:
                    row.append(histories[signal]["values"][i])
                writer.writerow(row)

        print(f"Results saved to: {filepath}")

    @staticmethod
    def load_csv(filepath: Path) -> dict[str, Any]:
        """Load CSV file (auto-detects wide or long format).

        Args
            filepath: Path to CSV file

        Returns:
            Dictionary with loaded data in nested format
        """
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        data: dict[str, dict[str, dict[str, Any]]] = {}

        with open(filepath) as f:
            reader = csv.reader(f)
            headers = next(reader)  # signal names
            units_row = next(reader)  # units

            # Read all data rows
            rows = list(reader)
            time_vals = np.array([float(row[0]) for row in rows])

            # Parse each signal column
            for col_idx, signal_name in enumerate(headers[1:], 1):
                values = np.array([float(row[col_idx]) for row in rows])
                unit = units_row[col_idx] if units_row[col_idx] != "-" else None

                # Parse component.port
                parts = signal_name.split(".", 1)
                if len(parts) == 2:
                    comp_name, port_name = parts
                else:
                    comp_name = "default"
                    port_name = signal_name

                # Organize into nested structure
                if comp_name not in data:
                    data[comp_name] = {}

                data[comp_name][port_name] = {"time": time_vals, "values": values, "unit": unit}

        return data