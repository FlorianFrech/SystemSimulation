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
