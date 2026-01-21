"""
Unit tests for SysSimX.core.port

Tests PortSpec, PortState, and port compatibility logic.
"""

import numpy as np
import pytest
from pint import DimensionalityError, UnitRegistry

from syssimx.core.port import PortSpec, PortState, PortType, _coerce_numpy_scalar
from syssimx.utilities.units import Quantity, ureg


# ============================================================================
# Test _coerce_numpy_scalar helper function
# ============================================================================
class TestCoerceNumpyScalar:
    """Test the _coerce_numpy_scalar helper function."""

    def test_coerce_np_float32(self):
        """Test coercing np.float32 to Python float."""
        result = _coerce_numpy_scalar(np.float32(3.14))
        assert isinstance(result, float)
        assert not isinstance(result, np.floating)
        assert result == pytest.approx(3.14, rel=1e-5)

    def test_coerce_np_float64(self):
        """Test coercing np.float64 to Python float."""
        result = _coerce_numpy_scalar(np.float64(2.71828))
        assert isinstance(result, float)
        assert not isinstance(result, np.floating)
        assert result == pytest.approx(2.71828)

    def test_coerce_np_int32(self):
        """Test coercing np.int32 to Python int."""
        result = _coerce_numpy_scalar(np.int32(42))
        assert isinstance(result, int)
        assert not isinstance(result, np.integer)
        assert result == 42

    def test_coerce_np_int64(self):
        """Test coercing np.int64 to Python int."""
        result = _coerce_numpy_scalar(np.int64(-100))
        assert isinstance(result, int)
        assert not isinstance(result, np.integer)
        assert result == -100

    def test_coerce_np_bool_true(self):
        """Test coercing np.bool_ True to Python bool."""
        result = _coerce_numpy_scalar(np.bool_(True))
        assert isinstance(result, bool)
        assert not isinstance(result, np.bool_)
        assert result is True

    def test_coerce_np_bool_false(self):
        """Test coercing np.bool_ False to Python bool."""
        result = _coerce_numpy_scalar(np.bool_(False))
        assert isinstance(result, bool)
        assert not isinstance(result, np.bool_)
        assert result is False

    def test_passthrough_native_float(self):
        """Test that native Python float passes through unchanged."""
        value = 3.14
        result = _coerce_numpy_scalar(value)
        assert result is value

    def test_passthrough_native_int(self):
        """Test that native Python int passes through unchanged."""
        value = 42
        result = _coerce_numpy_scalar(value)
        assert result is value

    def test_passthrough_native_bool(self):
        """Test that native Python bool passes through unchanged."""
        result_true = _coerce_numpy_scalar(True)
        result_false = _coerce_numpy_scalar(False)
        assert result_true is True
        assert result_false is False

    def test_passthrough_string(self):
        """Test that strings pass through unchanged."""
        value = "hello"
        result = _coerce_numpy_scalar(value)
        assert result is value

    def test_passthrough_none(self):
        """Test that None passes through unchanged."""
        result = _coerce_numpy_scalar(None)
        assert result is None

    def test_passthrough_quantity(self):
        """Test that Quantity values pass through unchanged."""
        value = Quantity(10.0, "m/s")
        result = _coerce_numpy_scalar(value)
        assert result is value


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

    def test_invalid_unit_string_raises_at_construction(self):
        """Test that invalid unit strings raise ValueError at construction."""
        with pytest.raises(ValueError, match="Invalid unit string"):
            PortSpec(name="x", type=PortType.REAL, direction="in", unit="invalid_unit_xyz")

    def test_valid_complex_unit_at_construction(self):
        """Test that valid complex units are accepted at construction."""
        spec = PortSpec(name="power", type=PortType.REAL, direction="in", unit="kg*m**2/s**3")
        assert spec.unit == "kg*m**2/s**3"

    def test_unit_object_at_construction(self):
        """Test that Unit objects are accepted at construction."""
        spec = PortSpec(name="length", type=PortType.REAL, direction="in", unit=ureg.meter)
        assert spec.unit == ureg.meter

    def test_unit_object_wrong_registry_raises_at_construction(self):
        """Test that Unit objects from another registry are rejected."""
        other_ureg = UnitRegistry()
        with pytest.raises(ValueError, match="Unit is not from the framework UnitRegistry"):
            PortSpec(name="length", type=PortType.REAL, direction="in", unit=other_ureg.meter)

    def test_port_spec_str_with_unit(self):
        """Test PortSpec __str__ method with unit."""
        spec = PortSpec(name="velocity", type=PortType.REAL, direction="in", unit="m/s")
        str_repr = str(spec)
        assert "velocity" in str_repr
        assert "real" in str_repr
        assert "in" in str_repr
        assert "m/s" in str_repr

    def test_port_spec_str_without_unit(self):
        """Test PortSpec __str__ method without unit."""
        spec = PortSpec(name="count", type=PortType.INT, direction="out")
        str_repr = str(spec)
        assert "count" in str_repr
        assert "int" in str_repr
        assert "out" in str_repr


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
        """Test INT port with unit raises error at construction time."""
        with pytest.raises(ValueError, match="Only REAL ports can have units"):
            PortSpec(name="count", type=PortType.INT, direction="in", unit="kg")

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
        """Test BOOL port with unit raises error at construction time."""
        with pytest.raises(ValueError, match="Only REAL ports can have units"):
            PortSpec(name="flag", type=PortType.BOOL, direction="in", unit="m")

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
        """Test STRING port with unit raises error at construction time."""
        with pytest.raises(ValueError, match="Only REAL ports can have units"):
            PortSpec(name="message", type=PortType.STRING, direction="in", unit="m")

    # --- EVENT Port Validation ---
    def test_event_port_accepts_bool(self):
        """Test EVENT port accepts bool values (events are boolean triggers)."""
        spec = PortSpec(name="trigger", type=PortType.EVENT, direction="in")
        spec.validate_value(True)  # Should not raise
        spec.validate_value(False)  # Should not raise

    def test_event_port_rejects_non_bool(self):
        """Test EVENT port rejects non-bool values."""
        spec = PortSpec(name="trigger", type=PortType.EVENT, direction="in")
        with pytest.raises(TypeError, match="EVENT expects"):
            spec.validate_value(1)
        with pytest.raises(TypeError, match="EVENT expects"):
            spec.validate_value("trigger")

    def test_event_port_cannot_have_unit(self):
        """Test EVENT port with unit raises error at construction time."""
        with pytest.raises(ValueError, match="Only REAL ports can have units"):
            PortSpec(name="trigger", type=PortType.EVENT, direction="in", unit="m")

    # --- REAL Port Edge Cases ---
    def test_real_port_accepts_zero(self):
        """Test REAL port accepts zero values."""
        spec = PortSpec(name="x", type=PortType.REAL, direction="in", unit="m")
        spec.validate_value(0.0)
        spec.validate_value(0)
        spec.validate_value(Quantity(0.0, "m"))

    def test_real_port_accepts_negative_values(self):
        """Test REAL port accepts negative values."""
        spec = PortSpec(name="x", type=PortType.REAL, direction="in", unit="m")
        spec.validate_value(-100.0)
        spec.validate_value(-1)
        spec.validate_value(Quantity(-50.0, "m"))

    def test_real_port_accepts_large_values(self):
        """Test REAL port accepts very large values."""
        spec = PortSpec(name="x", type=PortType.REAL, direction="in", unit="m")
        spec.validate_value(1e308)  # Near float max
        spec.validate_value(-1e308)

    def test_real_port_accepts_small_values(self):
        """Test REAL port accepts very small values."""
        spec = PortSpec(name="x", type=PortType.REAL, direction="in", unit="m")
        spec.validate_value(1e-308)  # Near float min positive
        spec.validate_value(-1e-308)

    def test_real_port_accepts_numpy_types(self):
        """Test REAL port accepts numpy float64 (inherits from Python float).

        Note: Only np.float64 inherits from Python float and is accepted.
        Other numpy types (np.float32, np.int64, np.int32) do NOT inherit
        from Python's native types and are rejected.
        """
        spec = PortSpec(name="x", type=PortType.REAL, direction="in", unit="m")
        spec.validate_value(np.float64(3.14))  # Accepted: inherits from float

    def test_real_port_accepts_numpy_float32(self):
        """Test REAL port accepts np.float32."""
        spec = PortSpec(name="x", type=PortType.REAL, direction="in", unit="m")
        spec.validate_value(np.float32(2.71), coerce_numpy=True)  # Coerce to float

    def test_real_port_accepts_numpy_int64(self):
        """Test REAL port accepts np.int64."""
        spec = PortSpec(name="x", type=PortType.REAL, direction="in", unit="m")
        spec.validate_value(np.int64(42), coerce_numpy=True)  # Coerce to int

    def test_real_port_rejects_none(self):
        """Test REAL port rejects None value."""
        spec = PortSpec(name="x", type=PortType.REAL, direction="in", unit="m")
        with pytest.raises(TypeError):
            spec.validate_value(None)

    def test_real_port_rejects_string(self):
        """Test REAL port rejects string values."""
        spec = PortSpec(name="x", type=PortType.REAL, direction="in", unit="m")
        with pytest.raises(TypeError, match="REAL expects"):
            spec.validate_value("3.14")

    def test_real_port_rejects_list(self):
        """Test REAL port rejects list values."""
        spec = PortSpec(name="x", type=PortType.REAL, direction="in", unit="m")
        with pytest.raises(TypeError, match="REAL expects"):
            spec.validate_value([1.0, 2.0])

    # --- INT Port Edge Cases ---
    def test_int_port_accepts_numpy_int(self):
        """Test INT port accepts numpy int types."""
        spec = PortSpec(name="count", type=PortType.INT, direction="in")
        spec.validate_value(np.int64(42), coerce_numpy=True)  # Coerce to int

    def test_int_port_rejects_none(self):
        """Test INT port rejects None value."""
        spec = PortSpec(name="count", type=PortType.INT, direction="in")
        with pytest.raises(TypeError):
            spec.validate_value(None)

    def test_int_port_accepts_large_values(self):
        """Test INT port accepts large integer values."""
        spec = PortSpec(name="count", type=PortType.INT, direction="in")
        spec.validate_value(10**18)  # Large but valid Python int
        spec.validate_value(-(10**18))


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

    def test_compatible_event_ports(self):
        """Test EVENT ports are compatible with each other."""
        spec1 = PortSpec(name="e1", type=PortType.EVENT, direction="out")
        spec2 = PortSpec(name="e2", type=PortType.EVENT, direction="in")
        assert PortSpec.compatible(spec1, spec2)

    def test_incompatible_event_with_bool(self):
        """Test EVENT and BOOL ports are incompatible (different types)."""
        spec_event = PortSpec(name="e", type=PortType.EVENT, direction="out")
        spec_bool = PortSpec(name="b", type=PortType.BOOL, direction="in")
        assert not PortSpec.compatible(spec_event, spec_bool)

    def test_compatible_real_both_no_unit(self):
        """Test REAL ports with both None units are compatible."""
        spec1 = PortSpec(name="x1", type=PortType.REAL, direction="out", unit=None)
        spec2 = PortSpec(name="x2", type=PortType.REAL, direction="in", unit=None)
        assert PortSpec.compatible(spec1, spec2)

    def test_incompatible_real_one_has_unit_other_none(self):
        """Test REAL ports where one has unit and other has None are incompatible."""
        spec_with_unit = PortSpec(name="v1", type=PortType.REAL, direction="out", unit="m/s")
        spec_no_unit = PortSpec(name="v2", type=PortType.REAL, direction="in", unit=None)
        assert not PortSpec.compatible(spec_with_unit, spec_no_unit)
        assert not PortSpec.compatible(spec_no_unit, spec_with_unit)

    def test_compatible_real_complex_units(self):
        """Test REAL ports with complex but compatible units."""
        spec1 = PortSpec(name="power1", type=PortType.REAL, direction="out", unit="W")
        spec2 = PortSpec(name="power2", type=PortType.REAL, direction="in", unit="kg*m**2/s**3")
        assert PortSpec.compatible(spec1, spec2)  # W = kg*m^2/s^3

    def test_compatible_real_angular_units(self):
        """Test REAL ports with angular velocity units."""
        spec1 = PortSpec(name="omega1", type=PortType.REAL, direction="out", unit="rad/s")
        spec2 = PortSpec(name="omega2", type=PortType.REAL, direction="in", unit="rpm")
        assert PortSpec.compatible(spec1, spec2)


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

    def test_set_updates_time(self):
        """Test that set() updates t_last correctly."""
        spec = PortSpec(name="x", type=PortType.REAL, direction="in", unit="m")
        state = PortState(spec=spec)

        state.set(1.0, t=0.0)
        assert state.t_last == 0.0

        state.set(2.0, t=1.5)
        assert state.t_last == 1.5

        state.set(3.0, t=0.5)  # Earlier time (valid, e.g., rollback)
        assert state.t_last == 0.5

    def test_set_negative_time(self):
        """Test setting value with negative time (valid in some contexts)."""
        spec = PortSpec(name="x", type=PortType.REAL, direction="in")
        state = PortState(spec=spec)

        state.set(5.0, t=-1.0)

        assert state.get() == 5.0
        assert state.t_last == -1.0

    def test_set_real_with_incompatible_quantity_raises(self):
        """Test setting REAL port with incompatible Quantity raises error."""
        spec = PortSpec(name="velocity", type=PortType.REAL, direction="in", unit="m/s")
        state = PortState(spec=spec)

        with pytest.raises(DimensionalityError):
            state.set(Quantity(10.0, "kg"), t=1.0)

    def test_set_int_with_float_raises(self):
        """Test setting INT port with float raises error."""
        spec = PortSpec(name="count", type=PortType.INT, direction="in")
        state = PortState(spec=spec)

        with pytest.raises(TypeError, match="INT expects"):
            state.set(3.14, t=1.0)

    def test_set_bool_with_int_raises(self):
        """Test setting BOOL port with int raises error."""
        spec = PortSpec(name="flag", type=PortType.BOOL, direction="in")
        state = PortState(spec=spec)

        with pytest.raises(TypeError, match="BOOL expects"):
            state.set(1, t=1.0)

    def test_set_string_with_int_raises(self):
        """Test setting STRING port with int raises error."""
        spec = PortSpec(name="msg", type=PortType.STRING, direction="in")
        state = PortState(spec=spec)

        with pytest.raises(TypeError, match="STRING expects"):
            state.set(42, t=1.0)

    def test_get_with_as_unit_on_unitless_port(self):
        """Test get() with as_unit on unitless REAL port."""
        spec = PortSpec(name="x", type=PortType.REAL, direction="in", unit=None)
        state = PortState(spec=spec)
        state.set(10.0, t=1.0)

        # When port has no unit, as_unit should return raw value
        result = state.get(as_unit="m")
        assert result == 10.0  # No conversion applied

    def test_get_with_as_unit_converts_correctly(self):
        """Test get() with as_unit performs correct unit conversion."""
        spec = PortSpec(name="length", type=PortType.REAL, direction="in", unit="m")
        state = PortState(spec=spec)
        state.set(1000.0, t=1.0)

        result = state.get(as_unit="km")
        assert abs(result.magnitude - 1.0) < 1e-9
        assert result.units == ureg("km")

    def test_set_numpy_float_to_real_port(self):
        """Test setting numpy float to REAL port."""
        spec = PortSpec(name="x", type=PortType.REAL, direction="in", unit="m")
        state = PortState(spec=spec)

        state.set(np.float64(3.14159), t=1.0)

        result = state.get()
        assert abs(result.magnitude - 3.14159) < 1e-10

    def test_event_port_state_default_value(self):
        """Test EVENT port state has correct default value."""
        spec = PortSpec(name="trigger", type=PortType.EVENT, direction="in")
        state = PortState(spec=spec)

        assert state.value is False
        assert state.get() is False

    def test_set_event_port_value(self):
        """Test setting EVENT port values."""
        spec = PortSpec(name="trigger", type=PortType.EVENT, direction="in")
        state = PortState(spec=spec)

        state.set(True, t=1.0)
        assert state.get() is True

        state.set(False, t=2.0)
        assert state.get() is False

    def test_set_numpy_float32_coerced(self):
        """Test that np.float32 is coerced to Python float."""
        spec = PortSpec(name="x", type=PortType.REAL, direction="in", unit="m")
        state = PortState(spec=spec)

        state.set(np.float32(2.71828), t=1.0)
        result = state.get()
        assert abs(result.magnitude - 2.71828) < 1e-5

    def test_set_numpy_int64_coerced(self):
        """Test that np.int64 is coerced to Python int for INT port."""
        spec = PortSpec(name="count", type=PortType.INT, direction="in")
        state = PortState(spec=spec)

        state.set(np.int64(42), t=1.0)
        assert state.get() == 42

    def test_set_numpy_bool_coerced(self):
        """Test that np.bool_ is coerced to Python bool."""
        spec = PortSpec(name="flag", type=PortType.BOOL, direction="in")
        state = PortState(spec=spec)

        state.set(np.bool_(True), t=1.0)
        assert state.get() is True

    def test_port_state_str_with_time(self):
        """Test PortState __str__ method with timestamp."""
        spec = PortSpec(name="velocity", type=PortType.REAL, direction="in", unit="m/s")
        state = PortState(spec=spec)
        state.set(10.5, t=1.5)

        str_repr = str(state)
        assert "velocity" in str_repr
        assert "t=1.5" in str_repr

    def test_port_state_str_without_time(self):
        """Test PortState __str__ method without timestamp."""
        spec = PortSpec(name="count", type=PortType.INT, direction="in")
        state = PortState(spec=spec)
        state.set(42)

        str_repr = str(state)
        assert "count" in str_repr
        assert "42" in str_repr


# ============================================================================
# Test PortState Reset
# ============================================================================
class TestPortStateReset:
    """Test PortState.reset() method."""

    def test_reset_real_port_with_unit(self):
        """Test reset() on REAL port with unit."""
        spec = PortSpec(name="velocity", type=PortType.REAL, direction="in", unit="m/s")
        state = PortState(spec=spec)

        state.set(100.0, t=5.0)
        assert state.get().magnitude == 100.0
        assert state.t_last == 5.0

        state.reset()
        assert state.get().magnitude == 0.0
        assert state.t_last is None

    def test_reset_real_port_without_unit(self):
        """Test reset() on REAL port without unit."""
        spec = PortSpec(name="coefficient", type=PortType.REAL, direction="in")
        state = PortState(spec=spec)

        state.set(3.14, t=2.0)
        state.reset()

        assert state.get() == 0.0
        assert state.t_last is None

    def test_reset_int_port(self):
        """Test reset() on INT port."""
        spec = PortSpec(name="count", type=PortType.INT, direction="in")
        state = PortState(spec=spec)

        state.set(999, t=10.0)
        state.reset()

        assert state.get() == 0
        assert state.t_last is None

    def test_reset_bool_port(self):
        """Test reset() on BOOL port."""
        spec = PortSpec(name="enabled", type=PortType.BOOL, direction="in")
        state = PortState(spec=spec)

        state.set(True, t=1.0)
        state.reset()

        assert state.get() is False
        assert state.t_last is None

    def test_reset_string_port(self):
        """Test reset() on STRING port."""
        spec = PortSpec(name="status", type=PortType.STRING, direction="in")
        state = PortState(spec=spec)

        state.set("Running", t=1.0)
        state.reset()

        assert state.get() == ""
        assert state.t_last is None

    def test_reset_event_port(self):
        """Test reset() on EVENT port."""
        spec = PortSpec(name="trigger", type=PortType.EVENT, direction="in")
        state = PortState(spec=spec)

        state.set(True, t=1.0)
        state.reset()

        assert state.get() is False
        assert state.t_last is None

    def test_reset_then_set(self):
        """Test that port works correctly after reset."""
        spec = PortSpec(name="x", type=PortType.REAL, direction="in", unit="m")
        state = PortState(spec=spec)

        state.set(50.0, t=1.0)
        state.reset()
        state.set(25.0, t=2.0)

        assert state.get().magnitude == 25.0
        assert state.t_last == 2.0


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

    def test_compatible_real_both_no_unit(self):
        """Test REAL port state compatibility when both have no unit."""
        spec1 = PortSpec(name="x1", type=PortType.REAL, direction="out", unit=None)
        spec2 = PortSpec(name="x2", type=PortType.REAL, direction="in", unit=None)
        state = PortState(spec=spec1)

        assert state.compatible_with(spec2)

    def test_incompatible_real_one_no_unit(self):
        """Test REAL port state incompatibility when one has no unit."""
        spec_with_unit = PortSpec(name="v1", type=PortType.REAL, direction="out", unit="m/s")
        spec_no_unit = PortSpec(name="v2", type=PortType.REAL, direction="in", unit=None)

        state_with_unit = PortState(spec=spec_with_unit)
        state_no_unit = PortState(spec=spec_no_unit)

        # PortState.compatible_with now delegates to PortSpec.compatible
        # so behavior is consistent: asymmetric units are incompatible
        assert not state_with_unit.compatible_with(spec_no_unit)
        assert not state_no_unit.compatible_with(spec_with_unit)

    def test_compatible_event_port_state(self):
        """Test EVENT port state compatibility."""
        spec1 = PortSpec(name="e1", type=PortType.EVENT, direction="out")
        spec2 = PortSpec(name="e2", type=PortType.EVENT, direction="in")
        state = PortState(spec=spec1)

        assert state.compatible_with(spec2)


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


@pytest.mark.parametrize(
    "port_type,valid_value,invalid_value",
    [
        (PortType.REAL, 3.14, "string"),
        (PortType.INT, 42, 3.14),
        (PortType.BOOL, True, 1),
        (PortType.STRING, "hello", 42),
    ],
)
def test_port_type_validation_parametrized(port_type, valid_value, invalid_value):
    """Parametrized test for port type validation."""
    spec = PortSpec(name="test", type=port_type, direction="in")

    # Valid value should not raise
    spec.validate_value(valid_value)

    # Invalid value should raise TypeError
    with pytest.raises(TypeError):
        spec.validate_value(invalid_value)


@pytest.mark.parametrize(
    "src_unit,dst_unit,is_compatible",
    [
        ("m/s", "km/h", True),
        ("m/s", "kg", False),
        ("N*m", "J", True),  # Newton-meter equals Joule
        ("rad/s", "deg/s", True),
        ("W", "J/s", True),  # Watt equals Joule per second
        ("m", "ft", True),  # Meters to feet
        ("kg", "lb", True),  # Kilograms to pounds
        ("Pa", "bar", True),  # Pascal to bar
        ("Pa", "m", False),  # Pressure vs length
    ],
)
def test_unit_compatibility_parametrized(src_unit, dst_unit, is_compatible):
    """Parametrized test for unit compatibility checking."""
    spec1 = PortSpec(name="out", type=PortType.REAL, direction="out", unit=src_unit)
    spec2 = PortSpec(name="in", type=PortType.REAL, direction="in", unit=dst_unit)

    assert PortSpec.compatible(spec1, spec2) == is_compatible


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================
class TestPortEdgeCases:
    """Test edge cases and error conditions."""

    def test_port_spec_equality(self):
        """Test PortSpec equality comparison."""
        spec1 = PortSpec(name="x", type=PortType.REAL, direction="in", unit="m")
        spec2 = PortSpec(name="x", type=PortType.REAL, direction="in", unit="m")
        spec3 = PortSpec(name="y", type=PortType.REAL, direction="in", unit="m")

        assert spec1 == spec2
        assert spec1 != spec3

    def test_port_spec_hash(self):
        """Test PortSpec can be used in sets/dicts (frozen dataclass)."""
        spec1 = PortSpec(name="x", type=PortType.REAL, direction="in", unit="m")
        spec2 = PortSpec(name="x", type=PortType.REAL, direction="in", unit="m")

        port_set = {spec1}
        assert spec2 in port_set

        port_dict = {spec1: "value"}
        assert port_dict[spec2] == "value"

    def test_port_state_multiple_updates(self):
        """Test PortState handles multiple sequential updates correctly."""
        spec = PortSpec(name="x", type=PortType.REAL, direction="in", unit="m")
        state = PortState(spec=spec)

        for i in range(100):
            state.set(float(i), t=float(i) * 0.01)

        assert state.get().magnitude == 99.0
        assert abs(state.t_last - 0.99) < 1e-10

    def test_port_state_set_same_value_twice(self):
        """Test setting same value twice doesn't cause issues."""
        spec = PortSpec(name="x", type=PortType.REAL, direction="in", unit="m")
        state = PortState(spec=spec)

        state.set(5.0, t=1.0)
        state.set(5.0, t=2.0)

        assert state.get().magnitude == 5.0
        assert state.t_last == 2.0

    def test_quantity_with_zero_value(self):
        """Test Quantity with zero value is handled correctly."""
        spec = PortSpec(name="x", type=PortType.REAL, direction="in", unit="m")
        state = PortState(spec=spec)

        state.set(Quantity(0.0, "m"), t=1.0)

        result = state.get()
        assert result.magnitude == 0.0
        assert result.units == ureg("m")

    def test_quantity_unit_conversion_precision(self):
        """Test unit conversion maintains numerical precision."""
        spec = PortSpec(name="length", type=PortType.REAL, direction="in", unit="m")
        state = PortState(spec=spec)

        # Set 1 km, should convert to 1000 m
        state.set(Quantity(1.0, "km"), t=1.0)

        result = state.get()
        assert abs(result.magnitude - 1000.0) < 1e-10
        assert result.units == ureg("m")

    def test_dimensionless_quantity(self):
        """Test handling of dimensionless quantities."""
        spec = PortSpec(name="ratio", type=PortType.REAL, direction="in", unit="dimensionless")
        state = PortState(spec=spec)

        state.set(0.5, t=1.0)
        result = state.get()

        assert abs(result.magnitude - 0.5) < 1e-10

    def test_port_type_enum_values(self):
        """Test PortType enum has expected string values."""
        assert PortType.REAL.value == "real"
        assert PortType.INT.value == "int"
        assert PortType.BOOL.value == "bool"
        assert PortType.STRING.value == "string"
        assert PortType.EVENT.value == "event"

    def test_port_spec_repr(self):
        """Test PortSpec has meaningful string representation."""
        spec = PortSpec(name="velocity", type=PortType.REAL, direction="in", unit="m/s")
        repr_str = repr(spec)

        assert "velocity" in repr_str
        assert "REAL" in repr_str or "real" in repr_str

    def test_direction_literal_values(self):
        """Test direction accepts only 'in' or 'out'."""
        # Valid directions
        PortSpec(name="x", type=PortType.REAL, direction="in")
        PortSpec(name="y", type=PortType.REAL, direction="out")

        # Note: Invalid directions may not raise at construction time
        # due to Python's type hint system not enforcing at runtime
