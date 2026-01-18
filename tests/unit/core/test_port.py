"""
Unit tests for SysSimX.core.port

Tests PortSpec, PortState, and port compatibility logic.
"""

import numpy as np
import pytest
from pint import DimensionalityError

from syssimx.core.port import PortSpec, PortState, PortType
from syssimx.utilities.units import Quantity, ureg


# ============================================================================
# Test PortSpec Creation and Validation
# ============================================================================
class TestPortSpecCreation:
    """Test PortSpec creation and basic properties."""

    def test_real_port_with_unit(self):
        """Test creating a REAL port with unit."""
        spec = PortSpec(
            name="velocity",
            type=PortType.REAL,
            direction="in",
            unit="m/s",
            description="Velocity input",
        )
        assert spec.name == "velocity"
        assert spec.type == PortType.REAL
        assert spec.direction == "in"
        assert spec.unit == "m/s"
        assert spec.description == "Velocity input"

    def test_real_port_without_unit(self):
        """Test creating a REAL port without unit."""
        spec = PortSpec(name="coefficient", type=PortType.REAL, direction="in")
        assert spec.name == "coefficient"
        assert spec.type == PortType.REAL
        assert spec.unit is None

    def test_int_port(self):
        """Test creating an INT port."""
        spec = PortSpec(name="count", type=PortType.INT, direction="out", description="Counter")
        assert spec.name == "count"
        assert spec.type == PortType.INT
        assert spec.unit is None

    def test_bool_port(self):
        """Test creating a BOOL port."""
        spec = PortSpec(name="enabled", type=PortType.BOOL, direction="in")
        assert spec.name == "enabled"
        assert spec.type == PortType.BOOL

    def test_string_port(self):
        """Test creating a STRING port."""
        spec = PortSpec(name="status", type=PortType.STRING, direction="out")
        assert spec.name == "status"
        assert spec.type == PortType.STRING

    def test_event_port(self):
        """Test creating an EVENT port."""
        spec = PortSpec(name="trigger", type=PortType.EVENT, direction="out")
        assert spec.name == "trigger"
        assert spec.type == PortType.EVENT

    def test_port_spec_is_frozen(self):
        """Test that PortSpec is immutable (frozen dataclass)."""
        spec = PortSpec(name="test", type=PortType.REAL, direction="in")
        with pytest.raises(Exception):
            spec.name = "modified"


# ============================================================================
# Test PortSpec Validation
# ============================================================================
class TestPortSpecValidation:
    """Test PortSpec.validate_value() method."""

    # --- REAL Port Validation ---
    def test_real_port_accepts_float(self):
        """Test REAL port accepts float values."""
        spec = PortSpec(name="x", type=PortType.REAL, direction="in", unit="m")
        spec.validate_value(5.0)  # Should not raise
        spec.validate_value(0.0)
        spec.validate_value(-3.14)

    def test_real_port_accepts_int(self):
        """Test REAL port accepts int values (converted to float)."""
        spec = PortSpec(name="x", type=PortType.REAL, direction="in", unit="m")
        spec.validate_value(5)  # Should not raise

    def test_real_port_accepts_quantity_with_compatible_unit(self):
        """Test REAL port accepts Quantity with compatible unit."""
        spec = PortSpec(name="velocity", type=PortType.REAL, direction="in", unit="m/s")
        spec.validate_value(Quantity(10.0, "m/s"))  # Should not raise
        spec.validate_value(Quantity(36.0, "km/h"))  # Convertible

    def test_real_port_rejects_quantity_with_incompatible_unit(self):
        """Test REAL port rejects Quantity with incompatible unit."""
        spec = PortSpec(name="velocity", type=PortType.REAL, direction="in", unit="m/s")
        with pytest.raises(DimensionalityError):
            spec.validate_value(Quantity(10.0, "kg"))

    # --- INT Port Validation ---
    def test_int_port_accepts_int(self):
        """Test INT port accepts int values."""
        spec = PortSpec(name="count", type=PortType.INT, direction="in")
        spec.validate_value(42)  # Should not raise
        spec.validate_value(0)
        spec.validate_value(-10)

    def test_int_port_rejects_float(self):
        """Test INT port rejects float values."""
        spec = PortSpec(name="count", type=PortType.INT, direction="in")
        with pytest.raises(TypeError, match="INT expects"):
            spec.validate_value(3.14)

    def test_int_port_rejects_wrong_type(self):
        """Test INT port rejects non-int types."""
        spec = PortSpec(name="count", type=PortType.INT, direction="in")
        with pytest.raises(TypeError):
            spec.validate_value("42")
        with pytest.raises(TypeError):
            spec.validate_value(True)  # Even though bool is subclass of int in Python

    def test_int_port_cannot_have_unit(self):
        """Test INT port with unit raises validation error."""
        spec = PortSpec(name="count", type=PortType.INT, direction="in", unit="kg")
        with pytest.raises(ValueError, match="Only REAL ports can have units"):
            spec.validate_value(5)

    # --- BOOL Port Validation ---
    def test_bool_port_accepts_bool(self):
        """Test BOOL port accepts bool values."""
        spec = PortSpec(name="flag", type=PortType.BOOL, direction="in")
        spec.validate_value(True)  # Should not raise
        spec.validate_value(False)

    def test_bool_port_rejects_int(self):
        """Test BOOL port rejects int (even 0/1)."""
        spec = PortSpec(name="flag", type=PortType.BOOL, direction="in")
        with pytest.raises(TypeError, match="BOOL expects"):
            spec.validate_value(1)
        with pytest.raises(TypeError):
            spec.validate_value(0)

    def test_bool_port_rejects_wrong_type(self):
        """Test BOOL port rejects non-bool types."""
        spec = PortSpec(name="flag", type=PortType.BOOL, direction="in")
        with pytest.raises(TypeError):
            spec.validate_value("true")

    def test_bool_port_cannot_have_unit(self):
        """Test BOOL port with unit raises validation error."""
        spec = PortSpec(name="flag", type=PortType.BOOL, direction="in", unit="m")
        with pytest.raises(ValueError, match="Only REAL ports can have units"):
            spec.validate_value(True)

    # --- STRING Port Validation ---
    def test_string_port_accepts_string(self):
        """Test STRING port accepts string values."""
        spec = PortSpec(name="message", type=PortType.STRING, direction="in")
        spec.validate_value("Hello")  # Should not raise
        spec.validate_value("")

    def test_string_port_rejects_wrong_type(self):
        """Test STRING port rejects non-string types."""
        spec = PortSpec(name="message", type=PortType.STRING, direction="in")
        with pytest.raises(TypeError, match="STRING expects"):
            spec.validate_value(42)
        with pytest.raises(TypeError):
            spec.validate_value(3.14)

    def test_string_port_cannot_have_unit(self):
        """Test STRING port with unit raises validation error."""
        spec = PortSpec(name="message", type=PortType.STRING, direction="in", unit="m")
        with pytest.raises(ValueError, match="Only REAL ports can have units"):
            spec.validate_value("test")


# ============================================================================
# Test PortSpec Compatibility
# ============================================================================
class TestPortSpecCompatibility:
    """Test PortSpec.compatible() static method."""

    def test_compatible_real_ports_same_unit(self):
        """Test REAL ports with same unit are compatible."""
        spec1 = PortSpec(name="v1", type=PortType.REAL, direction="out", unit="m/s")
        spec2 = PortSpec(name="v2", type=PortType.REAL, direction="in", unit="m/s")
        assert PortSpec.compatible(spec1, spec2)

    def test_compatible_real_ports_convertible_units(self):
        """Test REAL ports with convertible units are compatible."""
        spec1 = PortSpec(name="v1", type=PortType.REAL, direction="out", unit="m/s")
        spec2 = PortSpec(name="v2", type=PortType.REAL, direction="in", unit="km/h")
        assert PortSpec.compatible(spec1, spec2)

    def test_incompatible_real_ports_different_dimensions(self):
        """Test REAL ports with different dimensions are incompatible."""
        spec1 = PortSpec(name="v", type=PortType.REAL, direction="out", unit="m/s")
        spec2 = PortSpec(name="m", type=PortType.REAL, direction="in", unit="kg")
        assert not PortSpec.compatible(spec1, spec2)

    def test_compatible_real_ports_no_units(self):
        """Test REAL ports without units are compatible."""
        spec1 = PortSpec(name="x1", type=PortType.REAL, direction="out")
        spec2 = PortSpec(name="x2", type=PortType.REAL, direction="in")
        assert PortSpec.compatible(spec1, spec2)

    def test_not_compatible_real_port_one_has_unit(self):
        """Test REAL port with unit and without unit are compatible."""
        spec1 = PortSpec(name="x1", type=PortType.REAL, direction="out", unit="m")
        spec2 = PortSpec(name="x2", type=PortType.REAL, direction="in")
        assert not PortSpec.compatible(spec1, spec2)

    def test_compatible_int_ports(self):
        """Test INT ports are compatible."""
        spec1 = PortSpec(name="n1", type=PortType.INT, direction="out")
        spec2 = PortSpec(name="n2", type=PortType.INT, direction="in")
        assert PortSpec.compatible(spec1, spec2)

    def test_compatible_bool_ports(self):
        """Test BOOL ports are compatible."""
        spec1 = PortSpec(name="b1", type=PortType.BOOL, direction="out")
        spec2 = PortSpec(name="b2", type=PortType.BOOL, direction="in")
        assert PortSpec.compatible(spec1, spec2)

    def test_compatible_string_ports(self):
        """Test STRING ports are compatible."""
        spec1 = PortSpec(name="s1", type=PortType.STRING, direction="out")
        spec2 = PortSpec(name="s2", type=PortType.STRING, direction="in")
        assert PortSpec.compatible(spec1, spec2)

    def test_incompatible_different_types(self):
        """Test ports with different types are incompatible."""
        spec_real = PortSpec(name="x", type=PortType.REAL, direction="out")
        spec_int = PortSpec(name="n", type=PortType.INT, direction="in")
        spec_bool = PortSpec(name="b", type=PortType.BOOL, direction="in")
        spec_string = PortSpec(name="s", type=PortType.STRING, direction="in")

        assert not PortSpec.compatible(spec_real, spec_int)
        assert not PortSpec.compatible(spec_real, spec_bool)
        assert not PortSpec.compatible(spec_real, spec_string)
        assert not PortSpec.compatible(spec_int, spec_bool)
        assert not PortSpec.compatible(spec_int, spec_string)
        assert not PortSpec.compatible(spec_bool, spec_string)


# ============================================================================
# Test PortState Creation and Basic Operations
# ============================================================================
class TestPortStateCreation:
    """Test PortState creation and initialization."""

    def test_create_port_state(self):
        """Test creating a PortState."""
        spec = PortSpec(name="x", type=PortType.REAL, direction="in", unit="m")
        state = PortState(spec=spec)

        assert state.spec == spec
        assert state.value == 0.0 * ureg("m")
        assert state.t_last is None

    def test_default_value(self):
        """Test post init default value assignment."""
        spec_real_with_unit = PortSpec(name="v", type=PortType.REAL, direction="in", unit="m/s")
        state1 = PortState(spec=spec_real_with_unit)
        assert state1.value == 0.0 * ureg("m/s")

        spec_real_no_unit = PortSpec(name="a", type=PortType.REAL, direction="in")
        state2 = PortState(spec=spec_real_no_unit)
        assert state2.value == 0.0

        spec_int = PortSpec(name="n", type=PortType.INT, direction="in")
        state3 = PortState(spec=spec_int)
        assert state3.value == 0

        spec_bool = PortSpec(name="b", type=PortType.BOOL, direction="in")
        state4 = PortState(spec=spec_bool)
        assert state4.value is False

        spec_string = PortSpec(name="s", type=PortType.STRING, direction="in")
        state5 = PortState(spec=spec_string)
        assert state5.value == ""

        spec_event = PortSpec(name="e", type=PortType.EVENT, direction="in")
        state6 = PortState(spec=spec_event)
        assert not state6.value

    def test_create_port_state_with_initial_value(self):
        """Test creating PortState with initial value."""
        spec = PortSpec(name="x", type=PortType.REAL, direction="in", unit="m")
        state = PortState(spec=spec, value=5.0, t_last=0.0)

        assert state.value is not None
        assert np.isclose(state.t_last, 0.0)


# ============================================================================
# Test PortState Set/Get Operations
# ============================================================================
class TestPortStateSetGet:
    """Test PortState.set() and get() methods."""

    # --- REAL Port State ---
    def test_set_get_real_value_with_unit(self):
        """Test setting and getting REAL value with unit."""
        spec = PortSpec(name="velocity", type=PortType.REAL, direction="in", unit="m/s")
        state = PortState(spec=spec)

        state.set(10.0, t=1.0)

        value = state.get()
        assert isinstance(value, Quantity)
        assert value.magnitude == 10.0
        assert value.units == ureg("m/s")
        assert state.t_last == 1.0

    def test_set_get_real_value_without_unit(self):
        """Test setting and getting REAL value without unit."""
        spec = PortSpec(name="coefficient", type=PortType.REAL, direction="in")
        state = PortState(spec=spec)

        state.set(3.14, t=2.0)

        value = state.get()
        assert value == 3.14
        assert state.t_last == 2.0

    def test_set_real_with_quantity(self):
        """Test setting REAL value with Quantity."""
        spec = PortSpec(name="velocity", type=PortType.REAL, direction="in", unit="m/s")
        state = PortState(spec=spec)

        state.set(Quantity(10.0, "m/s"), t=1.0)

        value = state.get()
        assert value.magnitude == 10.0
        assert value.units == ureg("m/s")

    def test_set_real_with_convertible_quantity(self):
        """Test setting REAL value with convertible Quantity."""
        spec = PortSpec(name="velocity", type=PortType.REAL, direction="in", unit="m/s")
        state = PortState(spec=spec)

        state.set(Quantity(36.0, "km/h"), t=1.0)

        value = state.get()
        assert abs(value.magnitude - 10.0) < 1e-6  # 36 km/h = 10 m/s
        assert value.units == ureg("m/s")

    def test_get_real_as_different_unit(self):
        """Test getting REAL value in different unit."""
        spec = PortSpec(name="velocity", type=PortType.REAL, direction="in", unit="m/s")
        state = PortState(spec=spec)

        state.set(10.0, t=1.0)
        value_kmh = state.get(as_unit="km/h")

        assert abs(value_kmh.magnitude - 36.0) < 1e-6
        assert value_kmh.units == ureg("km/h")

    def test_get_none_value(self):
        """Test getting None from unset port."""
        spec = PortSpec(name="x", type=PortType.REAL, direction="in")
        state = PortState(spec=spec)

        assert state.get() == 0.0  # Default value

    # --- INT Port State ---
    def test_set_get_int_value(self):
        """Test setting and getting INT value."""
        spec = PortSpec(name="count", type=PortType.INT, direction="in")
        state = PortState(spec=spec)

        state.set(42, t=1.0)

        assert state.get() == 42
        assert state.t_last == 1.0

    # --- BOOL Port State ---
    def test_set_get_bool_value(self):
        """Test setting and getting BOOL value."""
        spec = PortSpec(name="enabled", type=PortType.BOOL, direction="in")
        state = PortState(spec=spec)

        state.set(True, t=1.0)

        assert state.get() is True
        assert state.t_last == 1.0

    # --- STRING Port State ---
    def test_set_get_string_value(self):
        """Test setting and getting STRING value."""
        spec = PortSpec(name="status", type=PortType.STRING, direction="in")
        state = PortState(spec=spec)

        state.set("Running", t=1.0)

        assert state.get() == "Running"
        assert state.t_last == 1.0

    def test_set_without_time(self):
        """Test setting value without timestamp."""
        spec = PortSpec(name="x", type=PortType.REAL, direction="in")
        state = PortState(spec=spec)

        state.set(5.0)

        assert state.get() == 5.0
        assert state.t_last is None


# ============================================================================
# Test PortState Compatibility
# ============================================================================
class TestPortStateCompatibility:
    """Test PortState.compatible_with() method."""

    def test_compatible_real_ports_same_unit(self):
        """Test REAL port states with same unit are compatible."""
        spec1 = PortSpec(name="v1", type=PortType.REAL, direction="out", unit="m/s")
        spec2 = PortSpec(name="v2", type=PortType.REAL, direction="in", unit="m/s")
        state = PortState(spec=spec1)

        assert state.compatible_with(spec2)

    def test_compatible_real_ports_convertible_units(self):
        """Test REAL port states with convertible units are compatible."""
        spec1 = PortSpec(name="v1", type=PortType.REAL, direction="out", unit="m/s")
        spec2 = PortSpec(name="v2", type=PortType.REAL, direction="in", unit="km/h")
        state = PortState(spec=spec1)

        assert state.compatible_with(spec2)

    def test_incompatible_real_ports_different_dimensions(self):
        """Test REAL port states with different dimensions are incompatible."""
        spec1 = PortSpec(name="v", type=PortType.REAL, direction="out", unit="m/s")
        spec2 = PortSpec(name="m", type=PortType.REAL, direction="in", unit="kg")
        state = PortState(spec=spec1)

        assert not state.compatible_with(spec2)

    def test_incompatible_different_types(self):
        """Test port states with different types are incompatible."""
        spec_real = PortSpec(name="x", type=PortType.REAL, direction="out")
        spec_int = PortSpec(name="n", type=PortType.INT, direction="in")
        state = PortState(spec=spec_real)

        assert not state.compatible_with(spec_int)


# ============================================================================
# Integration Tests (Realistic Scenarios)
# ============================================================================
class TestPortIntegration:
    """Test ports in realistic co-simulation scenarios."""

    def test_torque_port_workflow(self):
        """Test typical torque port usage."""
        # Output port from controller
        out_spec = PortSpec(name="torque_cmd", type=PortType.REAL, direction="out", unit="N*m")
        out_state = PortState(spec=out_spec)

        # Input port to actuator
        in_spec = PortSpec(name="torque_in", type=PortType.REAL, direction="in", unit="N*m")
        in_state = PortState(spec=in_spec)

        # Check compatibility
        assert PortSpec.compatible(out_spec, in_spec)

        # Set output
        out_state.set(Quantity(5.0, "N*m"), t=0.1)

        # Transfer value
        torque = out_state.get()
        in_state.set(torque, t=0.1)

        # Verify
        assert in_state.get().magnitude == 5.0

    def test_angular_velocity_unit_conversion(self):
        """Test angular velocity with different units."""
        # RPM output
        out_spec = PortSpec(name="rpm", type=PortType.REAL, direction="out", unit="rpm")
        out_state = PortState(spec=out_spec)

        # rad/s input
        in_spec = PortSpec(name="omega", type=PortType.REAL, direction="in", unit="rad/s")

        # Check compatibility
        assert PortSpec.compatible(out_spec, in_spec)

        # Set RPM value
        out_state.set(60.0, t=0.0)  # 60 RPM

        # Get in rad/s
        omega = out_state.get(as_unit="rad/s")
        expected = 60.0 * 2 * 3.14159 / 60  # ≈ 6.28 rad/s
        assert abs(omega.magnitude - expected) < 0.01

    def test_mixed_type_ports(self):
        """Test system with multiple port types."""
        # Create various port types
        velocity_spec = PortSpec(name="v", type=PortType.REAL, direction="out", unit="m/s")
        count_spec = PortSpec(name="n", type=PortType.INT, direction="out")
        enabled_spec = PortSpec(name="en", type=PortType.BOOL, direction="out")
        status_spec = PortSpec(name="st", type=PortType.STRING, direction="out")

        # Create states
        velocity_state = PortState(spec=velocity_spec)
        count_state = PortState(spec=count_spec)
        enabled_state = PortState(spec=enabled_spec)
        status_state = PortState(spec=status_spec)

        # Set values
        velocity_state.set(10.5, t=1.0)
        count_state.set(42, t=1.0)
        enabled_state.set(True, t=1.0)
        status_state.set("OK", t=1.0)

        # Verify
        assert velocity_state.get().magnitude == 10.5
        assert count_state.get() == 42
        assert enabled_state.get() is True
        assert status_state.get() == "OK"


# ============================================================================
# Parametrized Tests
# ============================================================================
@pytest.mark.parametrize(
    "unit_str,value,expected_unit",
    [
        ("m/s", 10.0, "meter / second"),
        ("km/h", 36.0, "kilometer / hour"),
        ("rad/s", 1.0, "radian / second"),
        ("N*m", 5.0, "meter * newton"),
        ("kg*m**2", 2.5, "kilogram * meter ** 2"),
    ],
)
def test_real_port_various_units(unit_str, value, expected_unit):
    """Test REAL ports with various engineering units."""
    spec = PortSpec(name="test", type=PortType.REAL, direction="in", unit=unit_str)
    state = PortState(spec=spec)

    state.set(value, t=0.0)
    result = state.get()

    assert isinstance(result, Quantity)
    assert result.magnitude == value
