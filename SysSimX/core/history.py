from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Union, List, Tuple
from pathlib import Path

import numpy as np
import csv

from .events import DenseTime
from ..utilities.units import ureg, Quantity

# -------------------------------------------------------------------
# Port History - stores time series data for a single port variable
# -------------------------------------------------------------------
@dataclass
class PortHistory:
    """
    Time series history for a single port variable.
    Stores values in the ports native unit and provides efficient array access.
    """
    port_name: str
    unit: Optional[str] = None
    _timestamps: List[float] = field(default_factory=list)
    _values: List[Union[float, int, bool, str]] = field(default_factory=list)

    def append(self, t: float, value: Union[float, int, bool, str, Quantity]) -> None:
        """Append a new time-value pair to the history."""
        self._timestamps.append(t)
        if isinstance(value, Quantity):
            self._values.append(value.magnitude)
        else:
            self._values.append(value)
    
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
    
    def get_values(self, as_unit: Optional[str] = None) -> np.ndarray:
        """Get values as a numpy array, converting to the specified unit if applicable."""
        vals = self.values
        if as_unit and self.unit and as_unit != self.unit:
            # Convert entire array at once
            converted = (vals * ureg(self.unit)).to(as_unit)
            return converted.magnitude
        return vals
    
    def to_dict(self, as_unit: Optional[str] = None) -> dict[str, Any]:
        """Get the history as a dictionary with 'time' array, 'values' array, and unit."""
        return {
            "time": self.time,
            "values": self.get_values(as_unit),
            "unit": as_unit if as_unit else self.unit
        }
    
    def to_tuple(self, as_unit: Optional[str] = None) -> Tuple[np.ndarray, np.ndarray, Optional[str]]:
        """Export history as tuple (time, values, unit)."""
        return self.time, self.get_values(as_unit), as_unit if as_unit else self.unit
    
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
    """
    Container for all port histories of a component.
    Provides convenient access patterns for retrieving trajectory data.
    """
    component_name: str
    _port_histories: Dict[str, PortHistory] = field(default_factory=dict)
    
    def add_port(self, port_name: str, unit: Optional[str] = None) -> None:
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
    
    def get_all_histories(self) -> Dict[str, PortHistory]:
        """Get all port histories as dictionary."""
        return dict(self._port_histories)
    
    def to_dict(self, port_names: Optional[List[str]] = None, 
                units: Optional[Dict[str, str]] = None) -> Dict[str, Dict[str, Any]]:
        """
        Export histories as nested dictionary.
        
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
    
    def to_arrays(self, port_names: Optional[List[str]] = None,
                  units: Optional[Dict[str, str]] = None) -> Tuple[np.ndarray, Dict[str, np.ndarray]]:
        """
        Export as common time array and dict of value arrays.
        
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
    
    def clear(self, port_names: Optional[List[str]] = None) -> None:
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
    """
    Container for all component histories in a system.
    Provides convenient access patterns and persistence methods.
    """
    system_name: str
    _component_histories: Dict[str, ComponentHistory] = field(default_factory=dict)
    _event_histories: Dict[Tuple[str, str], List[float]] = field(default_factory=dict)  # (component, event_name) -> times
    
    def add_component(self, component_name: str, component_history: ComponentHistory) -> None:
        """Register a component's history."""
        self._component_histories[component_name] = component_history
    
    def get_component_history(self, component_name: str) -> ComponentHistory:
        """Get history object for a specific component."""
        if component_name not in self._component_histories:
            raise KeyError(f"No history for component '{component_name}'")
        return self._component_histories[component_name]
    
    def get_all_histories(self) -> Dict[str, ComponentHistory]:
        """Get all component histories as dictionary."""
        return dict(self._component_histories)

    def record_event(self, component_name: str, event_name: str, t: DenseTime) -> None:
        """Record an event occurrence time."""
        key = (component_name, event_name)
        if key not in self._event_histories:
            self._event_histories[key] = []
        self._event_histories[key].append(t)
    
    def get_event_history(self, component_name: str, event_name: str) -> List[float]:
        """Get recorded times for a specific event."""
        key = (component_name, event_name)
        return self._event_histories.get(key, [])
    
    def get_all_event_histories(self) -> Dict[Tuple[str, str], List[float]]:
        """Get all recorded event histories."""
        return dict(self._event_histories)

    #----------------------------------------------------------------------------
    # Retrieval Methods
    #----------------------------------------------------------------------------
    def to_dict(self,
                component_names: Optional[List[str]] = None,
                port_names: Optional[Dict[str, List[str]]] = None,
                units: Optional[Dict[str, Dict[str, str]]] = None,
                format: str = 'nested') -> Dict[str, Any]:
        """
        Retrieve histories from components in the system.
        
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
        
        if format == 'nested':
            result = {}
            for comp_name in comps:
                if comp_name not in self._component_histories:
                    continue
                    
                comp_hist = self._component_histories[comp_name]
                ports = port_names.get(comp_name) if port_names else None
                comp_units = units.get(comp_name) if units else None
                
                result[comp_name] = comp_hist.to_dict(
                    port_names=ports,
                    units=comp_units
                )
            return result
            
        elif format == 'flat':
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
    
    def to_arrays(self,
                  component_names: Optional[List[str]] = None,
                  port_names: Optional[Dict[str, List[str]]] = None,
                  units: Optional[Dict[str, Dict[str, str]]] = None) -> Dict[str, Tuple[np.ndarray, Dict[str, np.ndarray]]]:
        """
        Get histories as numpy arrays per component.
        
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
            
            result[comp_name] = comp_hist.to_arrays(
                port_names=ports,
                units=comp_units
            )
        
        return result
    
    def get_port_trajectory(self, 
                           component: str, 
                           port: str,
                           as_unit: Optional[str] = None) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get time and value arrays for a specific port (convenience method).
        
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
    
    def clear(self,
              component_names: Optional[List[str]] = None,
              port_names: Optional[Dict[str, List[str]]] = None) -> None:
        """Clear histories for specified components and ports."""
        comps = component_names if component_names else list(self._component_histories.keys())
        
        for comp_name in comps:
            if comp_name not in self._component_histories:
                continue
            
            comp_hist = self._component_histories[comp_name]
            ports = port_names.get(comp_name) if port_names else None
            comp_hist.clear(port_names=ports)
    
    #-------------------------------------------------------------------
    # Persistence Methods
    #-------------------------------------------------------------------
    def save_csv(self,
                 filepath: Path,
                 component_names: Optional[List[str]] = None,
                 port_names: Optional[Dict[str, List[str]]] = None,
                 units: Optional[Dict[str, Dict[str, str]]] = None,
                 long_format: bool = False) -> None:
        """
        Save as single CSV file.
        
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
            component_names=component_names,
            port_names=port_names,
            units=units,
            format='flat'
        )
        
        if not histories:
            print("No data to save.")
            return
        
        # Get all time points (assuming all signals have same time base)
        first_key = next(iter(histories.keys()))
        time_array = histories[first_key]['time']
        
        # Build header rows
        signal_names = list(histories.keys())
        units_row = []
        
        for signal in signal_names:
            unit = histories[signal].get('unit', '-')
            units_row.append(unit if unit else '-')
        
        # Write CSV
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Header row 1: signal names
            writer.writerow(['time'] + signal_names)
            
            # Header row 2: units
            writer.writerow(['s'] + units_row)
            
            # Data rows
            n_points = len(time_array)
            for i in range(n_points):
                row = [time_array[i]]
                for signal in signal_names:
                    row.append(histories[signal]['values'][i])
                writer.writerow(row)

        print(f"Results saved to: {filepath}")

    @staticmethod
    def load_csv(filepath: Path) -> Dict[str, Any]:
        """
        Load CSV file (auto-detects wide or long format).
        
        Args
            filepath: Path to CSV file
        
        Returns:
            Dictionary with loaded data in nested format
        """
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        data = {}
        
        with open(filepath, 'r') as f:
            reader = csv.reader(f)
            headers = next(reader)  # signal names
            units_row = next(reader)  # units
            
            # Read all data rows
            rows = list(reader)
            time_vals = np.array([float(row[0]) for row in rows])
            
            # Parse each signal column
            for col_idx, signal_name in enumerate(headers[1:], 1):
                values = np.array([float(row[col_idx]) for row in rows])
                unit = units_row[col_idx] if units_row[col_idx] != '-' else None
                
                # Parse component.port
                parts = signal_name.split('.', 1)
                if len(parts) == 2:
                    comp_name, port_name = parts
                else:
                    comp_name = 'default'
                    port_name = signal_name
                
                # Organize into nested structure
                if comp_name not in data:
                    data[comp_name] = {}
                
                data[comp_name][port_name] = {
                    'time': time_vals,
                    'values': values,
                    'unit': unit
                }
        
        return data