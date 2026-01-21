"""
Unit tests for syssimx.core.port

Tests for PortHistory, ComponentHistory, and SystemHistory classes.
"""

import numpy as np
import pytest

from syssimx.core.events import DenseTime
from syssimx.core.history import ComponentHistory, PortHistory, SystemHistory
from syssimx.utilities.units import Quantity, ureg


# ============================================================================
# Test PortHistory Creation and Validation
# ============================================================================
class TestPortHistory:
    """Test PortHistory class functionality."""

    def test_create_port_history(self):
        """Test creating a PortHistory instance."""
        port_history = PortHistory(port_name="PortA", unit="m")
        assert port_history.port_name == "PortA"
        assert port_history.unit == "m"
        assert port_history._timestamps == []
        assert port_history._values == []

    def test_add_entry(self):
        """Test adding entries to PortHistory."""
        port_history = PortHistory(port_name="PortB", unit="kg")
        port_history.append(t=1.0, value=100)
        assert port_history._timestamps == [1.0]
        assert port_history._values == [100]

    def test_append_quantity(self):
        """Test appending Quantity values to PortHistory."""
        port_history = PortHistory(port_name="PortC", unit="m")
        port_history.append(t=2.0, value=Quantity(5.0, ureg.m))
        assert port_history._timestamps == [2.0]
        assert port_history._values == [5.0]

    def test_clear_history(self):
        """Test clearing PortHistory entries."""
        port_history = PortHistory(port_name="PortD", unit="s")
        port_history.append(t=1.0, value=10)
        port_history.clear()
        assert port_history._timestamps == []
        assert port_history._values == []

    def test_time_property(self):
        """Test time property of PortHistory."""
        port_history = PortHistory(port_name="PortE", unit="A")
        port_history.append(t=0.0, value=1.0)
        port_history.append(t=1.0, value=2.0)
        assert np.array_equal(port_history.time, np.array([0.0, 1.0]))

    def test_values_property(self):
        """Test values property of PortHistory."""
        port_history = PortHistory(port_name="PortF", unit="V")
        port_history.append(t=0.0, value=3.0)
        port_history.append(t=1.0, value=4.0)
        assert np.array_equal(port_history.values, np.array([3.0, 4.0]))

    def test_get_values(self):
        """Test get_values method of PortHistory."""
        port_history = PortHistory(port_name="PortG", unit="W")
        port_history.append(t=0.0, value=10.0)
        port_history.append(t=1.0, value=20.0)
        values = port_history.get_values()
        assert np.array_equal(values, np.array([10.0, 20.0]))

    def test_get_values_with_unit(self):
        """Test get_values method with unit conversion."""
        port_history = PortHistory(port_name="PortH", unit="m")
        port_history.append(t=0.0, value=100.0)  # in meters
        port_history.append(t=1.0, value=200.0)  # in meters
        values_km = port_history.get_values(as_unit="km")
        expected_values = np.array([0.1, 0.2])  # in kilometers
        assert np.allclose(values_km, expected_values)

    def test_to_dict(self):
        """Test to_dict method of PortHistory."""
        port_history = PortHistory(port_name="PortI", unit="N")
        port_history.append(t=0.0, value=50.0)
        port_history.append(t=1.0, value=100.0)
        history_dict = port_history.to_dict()
        assert history_dict["unit"] == "N"
        assert np.array_equal(history_dict["time"], np.array([0.0, 1.0]))
        assert np.array_equal(history_dict["values"], np.array([50.0, 100.0]))

    def test_to_dict_with_unit(self):
        """Test to_dict method with unit conversion."""
        port_history = PortHistory(port_name="PortJ", unit="m")
        port_history.append(t=0.0, value=1000.0)  # in meters
        port_history.append(t=1.0, value=2000.0)  # in meters
        history_dict = port_history.to_dict(as_unit="km")
        expected_values = np.array([1.0, 2.0])  # in kilometers
        assert history_dict["unit"] == "km"
        assert np.array_equal(history_dict["time"], np.array([0.0, 1.0]))
        assert np.array_equal(history_dict["values"], expected_values)

    def test_to_tuple(self):
        """Test to_tuple method of PortHistory."""
        port_history = PortHistory(port_name="PortK", unit="m")
        port_history.append(t=0.0, value=5.0)
        port_history.append(t=1.0, value=10.0)
        time_array, values_array, unit = port_history.to_tuple()
        assert np.array_equal(time_array, np.array([0.0, 1.0]))
        assert np.array_equal(values_array, np.array([5.0, 10.0]))
        assert unit == "m"

    def test_to_tuple_with_unit_conversion(self):
        """Test to_tuple method with unit conversion."""
        port_history = PortHistory(port_name="PortL", unit="m")
        port_history.append(t=0.0, value=1000.0)
        port_history.append(t=1.0, value=2000.0)
        time_array, values_array, unit = port_history.to_tuple(as_unit="km")
        assert np.array_equal(time_array, np.array([0.0, 1.0]))
        assert np.allclose(values_array, np.array([1.0, 2.0]))
        assert unit == "km"

    def test_len_empty(self):
        """Test __len__ for empty PortHistory."""
        port_history = PortHistory(port_name="PortM", unit="m")
        assert len(port_history) == 0

    def test_len_with_entries(self):
        """Test __len__ for PortHistory with entries."""
        port_history = PortHistory(port_name="PortN", unit="m")
        port_history.append(t=0.0, value=1.0)
        port_history.append(t=1.0, value=2.0)
        port_history.append(t=2.0, value=3.0)
        assert len(port_history) == 3

    def test_bool_empty_is_falsy(self):
        """Test empty PortHistory is falsy."""
        port_history = PortHistory(port_name="PortO", unit="m")
        assert not port_history
        assert bool(port_history) is False

    def test_bool_with_entries_is_truthy(self):
        """Test PortHistory with entries is truthy."""
        port_history = PortHistory(port_name="PortP", unit="m")
        port_history.append(t=0.0, value=1.0)
        assert port_history
        assert bool(port_history) is True


# ============================================================================
# Test Component History Creation and Validation
# ============================================================================
class TestComponentHistory:
    """Test ComponentHistory class functionality."""

    def test_create_component_history(self):
        """Test creating a ComponentHistory instance."""
        comp_history = ComponentHistory(component_name="CompA")
        assert comp_history.component_name == "CompA"
        assert comp_history._port_histories == {}

    def test_add_port(self):
        """Test adding PortHistory to ComponentHistory."""
        comp_history = ComponentHistory(component_name="CompB")
        comp_history.add_port("Port1", unit="m")
        assert "Port1" in comp_history._port_histories
        assert comp_history._port_histories["Port1"].port_name == "Port1"

    def test_add_existing_port(self):
        """Test adding an existing Port to ComponentHistory."""
        comp_history = ComponentHistory(component_name="CompC")
        comp_history.add_port("Port2", unit="m/s")  # 1st addition
        comp_history.add_port("Port2", unit="m/s")  # 2nd addition
        assert len(comp_history._port_histories.keys()) == 1  # Should still be 1

    def test_append_to_registered_port(self):
        """Test appending data to a registered port in ComponentHistory."""
        comp_history = ComponentHistory(component_name="CompD")
        comp_history.add_port("Port3", unit="kg")
        comp_history.append("Port3", t=0.0, value=50.0)
        port_history = comp_history._port_histories["Port3"]
        assert port_history._timestamps == [0.0]
        assert port_history._values == [50.0]

    def test_append_to_unregistered_port(self):
        """Test appending data to an unregistered port in ComponentHistory."""
        comp_history = ComponentHistory(component_name="CompE")
        with pytest.raises(KeyError):
            comp_history.append("Port4", t=0.0, value=100.0)

    def test_get_port_history(self):
        """Test retrieving a registered port history."""
        comp_history = ComponentHistory(component_name="CompF")
        comp_history.add_port("Port5", unit="m/s")
        comp_history.append("Port5", t=0.0, value=10.0)
        port_hist = comp_history.get_port_history("Port5")
        assert port_hist.port_name == "Port5"
        assert port_hist.unit == "m/s"
        assert len(port_hist) == 1

    def test_get_port_history_unregistered_raises(self):
        """Test get_port_history for non-existent port raises KeyError."""
        comp_history = ComponentHistory(component_name="CompG")
        with pytest.raises(KeyError, match="No history for port"):
            comp_history.get_port_history("nonexistent")

    def test_get_all_histories(self):
        """Test get_all_histories returns all port histories."""
        comp_history = ComponentHistory(component_name="CompH")
        comp_history.add_port("Port6", unit="m")
        comp_history.add_port("Port7", unit="s")
        all_hist = comp_history.get_all_histories()
        assert "Port6" in all_hist
        assert "Port7" in all_hist
        assert len(all_hist) == 2

    def test_to_dict(self):
        """Test to_dict method of ComponentHistory."""
        comp_history = ComponentHistory(component_name="CompI")
        comp_history.add_port("position", unit="m")
        comp_history.add_port("velocity", unit="m/s")
        comp_history.append("position", t=0.0, value=0.0)
        comp_history.append("position", t=1.0, value=5.0)
        comp_history.append("velocity", t=0.0, value=0.0)
        comp_history.append("velocity", t=1.0, value=10.0)

        result = comp_history.to_dict()
        assert "position" in result
        assert "velocity" in result
        assert np.array_equal(result["position"]["values"], np.array([0.0, 5.0]))
        assert result["position"]["unit"] == "m"

    def test_to_dict_with_port_filter(self):
        """Test to_dict with specific port names."""
        comp_history = ComponentHistory(component_name="CompJ")
        comp_history.add_port("a", unit="m")
        comp_history.add_port("b", unit="s")
        comp_history.append("a", t=0.0, value=1.0)
        comp_history.append("b", t=0.0, value=2.0)

        result = comp_history.to_dict(port_names=["a"])
        assert "a" in result
        assert "b" not in result

    def test_to_arrays(self):
        """Test to_arrays method of ComponentHistory."""
        comp_history = ComponentHistory(component_name="CompK")
        comp_history.add_port("x", unit="m")
        comp_history.add_port("y", unit="m")
        comp_history.append("x", t=0.0, value=1.0)
        comp_history.append("x", t=1.0, value=2.0)
        comp_history.append("y", t=0.0, value=10.0)
        comp_history.append("y", t=1.0, value=20.0)

        time_arr, values_dict = comp_history.to_arrays()
        assert np.array_equal(time_arr, np.array([0.0, 1.0]))
        assert np.array_equal(values_dict["x"], np.array([1.0, 2.0]))
        assert np.array_equal(values_dict["y"], np.array([10.0, 20.0]))

    def test_to_arrays_empty(self):
        """Test to_arrays with no ports returns empty arrays."""
        comp_history = ComponentHistory(component_name="CompL")
        time_arr, values_dict = comp_history.to_arrays()
        assert len(time_arr) == 0
        assert values_dict == {}

    def test_clear_all_ports(self):
        """Test clearing all port histories."""
        comp_history = ComponentHistory(component_name="CompM")
        comp_history.add_port("p1", unit="m")
        comp_history.add_port("p2", unit="s")
        comp_history.append("p1", t=0.0, value=1.0)
        comp_history.append("p2", t=0.0, value=2.0)

        comp_history.clear()
        assert len(comp_history.get_port_history("p1")) == 0
        assert len(comp_history.get_port_history("p2")) == 0

    def test_clear_specific_ports(self):
        """Test clearing specific port histories."""
        comp_history = ComponentHistory(component_name="CompN")
        comp_history.add_port("p1", unit="m")
        comp_history.add_port("p2", unit="s")
        comp_history.append("p1", t=0.0, value=1.0)
        comp_history.append("p2", t=0.0, value=2.0)

        comp_history.clear(port_names=["p1"])
        assert len(comp_history.get_port_history("p1")) == 0
        assert len(comp_history.get_port_history("p2")) == 1

    def test_len(self):
        """Test __len__ returns number of registered ports."""
        comp_history = ComponentHistory(component_name="CompO")
        assert len(comp_history) == 0
        comp_history.add_port("p1", unit="m")
        assert len(comp_history) == 1
        comp_history.add_port("p2", unit="s")
        assert len(comp_history) == 2

    def test_contains(self):
        """Test __contains__ checks for port existence."""
        comp_history = ComponentHistory(component_name="CompP")
        comp_history.add_port("present", unit="m")
        assert "present" in comp_history
        assert "absent" not in comp_history


# ============================================================================
# Test System History Creation and Validation
# ============================================================================
class TestSystemHistory:
    """Test SystemHistory class functionality."""

    def test_create_system_history(self):
        """Test creating a SystemHistory instance."""
        sys_history = SystemHistory("System")
        assert sys_history._component_histories == {}
        assert sys_history._event_histories == {}

    def test_add_component(self):
        """Test adding ComponentHistory to SystemHistory."""
        sys_history = SystemHistory("System")
        comp_history = ComponentHistory(component_name="CompA")
        sys_history.add_component(comp_history.component_name, comp_history)
        assert "CompA" in sys_history._component_histories
        assert sys_history._component_histories["CompA"] == comp_history

    def test_get_component_history(self):
        """Test retrieving ComponentHistory from SystemHistory."""
        sys_history = SystemHistory("System")
        comp_history = ComponentHistory(component_name="CompB")
        comp_history.add_port("Port1", unit="m")
        comp_history.append("Port1", t=0.0, value=10.0)
        comp_history.append("Port1", t=1.0, value=20.0)
        sys_history.add_component(comp_history.component_name, comp_history)
        retrieved_comp_history = sys_history.get_component_history("CompB")
        assert retrieved_comp_history == comp_history
        port_history = retrieved_comp_history._port_histories["Port1"]
        assert port_history._timestamps == [0.0, 1.0]
        assert port_history._values == [10.0, 20.0]

    def test_record_event(self):
        """Test recording events in SystemHistory."""
        sys_history = SystemHistory("System")
        comp_name = "event_comp"
        event_name = "test_event"
        event_time_1 = DenseTime(0.42)
        event_time_2 = DenseTime(1.23)
        event_time_3 = DenseTime(2.34, 5)
        sys_history.record_event(comp_name, event_name, event_time_1)
        sys_history.record_event(comp_name, event_name, event_time_2)
        sys_history.record_event(comp_name, event_name, event_time_3)
        event_history = sys_history.get_event_history(comp_name, event_name)
        assert event_history == [event_time_1, event_time_2, event_time_3]

    def test_get_component_history_nonexistent_raises(self):
        """Test get_component_history for non-existent component raises KeyError."""
        sys_history = SystemHistory("System")
        with pytest.raises(KeyError, match="No history for component"):
            sys_history.get_component_history("nonexistent")

    def test_get_all_histories(self):
        """Test get_all_histories returns all component histories."""
        sys_history = SystemHistory("System")
        comp_a = ComponentHistory(component_name="CompA")
        comp_b = ComponentHistory(component_name="CompB")
        sys_history.add_component("CompA", comp_a)
        sys_history.add_component("CompB", comp_b)

        all_hist = sys_history.get_all_histories()
        assert "CompA" in all_hist
        assert "CompB" in all_hist
        assert len(all_hist) == 2

    def test_get_event_history_nonexistent_returns_empty(self):
        """Test get_event_history for non-recorded event returns empty list."""
        sys_history = SystemHistory("System")
        result = sys_history.get_event_history("comp", "event")
        assert result == []

    def test_get_all_event_histories(self):
        """Test get_all_event_histories returns all event histories."""
        sys_history = SystemHistory("System")
        sys_history.record_event("comp1", "evt1", DenseTime(1.0))
        sys_history.record_event("comp2", "evt2", DenseTime(2.0))

        all_events = sys_history.get_all_event_histories()
        assert ("comp1", "evt1") in all_events
        assert ("comp2", "evt2") in all_events

    def test_to_dict_nested_format(self):
        """Test to_dict with nested format."""
        sys_history = SystemHistory("System")
        comp = ComponentHistory(component_name="motor")
        comp.add_port("speed", unit="rad/s")
        comp.append("speed", t=0.0, value=0.0)
        comp.append("speed", t=1.0, value=10.0)
        sys_history.add_component("motor", comp)

        result = sys_history.to_dict(format="nested")
        assert "motor" in result
        assert "speed" in result["motor"]
        assert np.array_equal(result["motor"]["speed"]["values"], np.array([0.0, 10.0]))

    def test_to_dict_flat_format(self):
        """Test to_dict with flat format."""
        sys_history = SystemHistory("System")
        comp = ComponentHistory(component_name="motor")
        comp.add_port("speed", unit="rad/s")
        comp.append("speed", t=0.0, value=0.0)
        comp.append("speed", t=1.0, value=10.0)
        sys_history.add_component("motor", comp)

        result = sys_history.to_dict(format="flat")
        assert "motor.speed" in result
        assert np.array_equal(result["motor.speed"]["values"], np.array([0.0, 10.0]))

    def test_to_dict_invalid_format_raises(self):
        """Test to_dict with invalid format raises ValueError."""
        sys_history = SystemHistory("System")
        with pytest.raises(ValueError, match="Unknown format"):
            sys_history.to_dict(format="invalid")

    def test_get_port_trajectory(self):
        """Test get_port_trajectory convenience method."""
        sys_history = SystemHistory("System")
        comp = ComponentHistory(component_name="pendulum")
        comp.add_port("angle", unit="rad")
        comp.append("angle", t=0.0, value=0.0)
        comp.append("angle", t=0.5, value=0.5)
        comp.append("angle", t=1.0, value=1.0)
        sys_history.add_component("pendulum", comp)

        time_arr, values_arr = sys_history.get_port_trajectory("pendulum", "angle")
        assert np.array_equal(time_arr, np.array([0.0, 0.5, 1.0]))
        assert np.array_equal(values_arr, np.array([0.0, 0.5, 1.0]))

    def test_get_port_trajectory_with_unit_conversion(self):
        """Test get_port_trajectory with unit conversion."""
        sys_history = SystemHistory("System")
        comp = ComponentHistory(component_name="sensor")
        comp.add_port("distance", unit="m")
        comp.append("distance", t=0.0, value=1000.0)
        comp.append("distance", t=1.0, value=2000.0)
        sys_history.add_component("sensor", comp)

        time_arr, values_arr = sys_history.get_port_trajectory("sensor", "distance", as_unit="km")
        assert np.allclose(values_arr, np.array([1.0, 2.0]))

    def test_get_port_trajectory_nonexistent_component_raises(self):
        """Test get_port_trajectory for non-existent component raises KeyError."""
        sys_history = SystemHistory("System")
        with pytest.raises(KeyError, match="Component .* not found"):
            sys_history.get_port_trajectory("nonexistent", "port")

    def test_clear_all_components(self):
        """Test clearing all component histories."""
        sys_history = SystemHistory("System")
        comp1 = ComponentHistory(component_name="c1")
        comp1.add_port("p", unit="m")
        comp1.append("p", t=0.0, value=1.0)
        comp2 = ComponentHistory(component_name="c2")
        comp2.add_port("q", unit="s")
        comp2.append("q", t=0.0, value=2.0)
        sys_history.add_component("c1", comp1)
        sys_history.add_component("c2", comp2)

        sys_history.clear()
        assert len(comp1.get_port_history("p")) == 0
        assert len(comp2.get_port_history("q")) == 0

    def test_to_arrays(self):
        """Test to_arrays method of SystemHistory."""
        sys_history = SystemHistory("System")
        comp = ComponentHistory(component_name="motor")
        comp.add_port("speed", unit="rad/s")
        comp.add_port("torque", unit="N*m")
        comp.append("speed", t=0.0, value=0.0)
        comp.append("speed", t=1.0, value=10.0)
        comp.append("torque", t=0.0, value=5.0)
        comp.append("torque", t=1.0, value=15.0)
        sys_history.add_component("motor", comp)

        result = sys_history.to_arrays()
        assert "motor" in result
        time_arr, values_dict = result["motor"]
        assert np.array_equal(time_arr, np.array([0.0, 1.0]))
        assert np.array_equal(values_dict["speed"], np.array([0.0, 10.0]))
        assert np.array_equal(values_dict["torque"], np.array([5.0, 15.0]))


# ============================================================================
# Test SystemHistory CSV Persistence
# ============================================================================
class TestSystemHistoryCSV:
    """Test SystemHistory save/load CSV functionality."""

    def test_save_and_load_csv(self, tmp_path):
        """Test round-trip save and load of CSV file."""
        # Create and populate history
        sys_history = SystemHistory("TestSystem")
        comp = ComponentHistory(component_name="sensor")
        comp.add_port("temperature", unit="K")
        comp.add_port("pressure", unit="Pa")
        comp.append("temperature", t=0.0, value=300.0)
        comp.append("temperature", t=1.0, value=310.0)
        comp.append("pressure", t=0.0, value=101325.0)
        comp.append("pressure", t=1.0, value=102000.0)
        sys_history.add_component("sensor", comp)

        # Save to CSV
        csv_path = tmp_path / "test_history.csv"
        sys_history.save_csv(csv_path)

        # Verify file exists
        assert csv_path.exists()

        # Load and verify
        loaded = SystemHistory.load_csv(csv_path)
        assert "sensor" in loaded
        assert "temperature" in loaded["sensor"]
        assert "pressure" in loaded["sensor"]
        assert np.allclose(loaded["sensor"]["temperature"]["values"], np.array([300.0, 310.0]))
        assert loaded["sensor"]["temperature"]["unit"] == "K"

    def test_load_csv_file_not_found_raises(self, tmp_path):
        """Test load_csv raises FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            SystemHistory.load_csv(tmp_path / "nonexistent.csv")

    def test_save_csv_creates_parent_directories(self, tmp_path):
        """Test save_csv creates parent directories if needed."""
        sys_history = SystemHistory("TestSystem")
        comp = ComponentHistory(component_name="comp")
        comp.add_port("x", unit="m")
        comp.append("x", t=0.0, value=1.0)
        sys_history.add_component("comp", comp)

        nested_path = tmp_path / "subdir1" / "subdir2" / "output.csv"
        sys_history.save_csv(nested_path)
        assert nested_path.exists()
