"""
Unit tests for SysSimX.utilities.units

Tests the unit handling utilities using Pint.
"""

import pytest
from pint import DimensionalityError

from syssimx.utilities.units import Quantity, fix_exponent, to_pint_unit, ureg


# ============================================================================
# Test fix_exponent Function
# ============================================================================
class TestFixExponent:
    """Test the fix_exponent function for FMU unit strings."""

    def test_simple_exponent(self):
        """Test simple exponent conversion."""
        assert fix_exponent("s2") == "s^2"
        assert fix_exponent("m3") == "m^3"

    def test_negative_exponent(self):
        """Test negative exponent conversion."""
        assert fix_exponent("s-1") == "s^-1"
        assert fix_exponent("m-2") == "m^-2"

    def test_multiple_units(self):
        """Test multiple units with exponents."""
        assert fix_exponent("kg.m2.s-2") == "kg.m^2.s^-2"
        assert fix_exponent("N.m-1") == "N.m^-1"

    def test_no_exponent(self):
        """Test units without exponents."""
        assert fix_exponent("m") == "m"
        assert fix_exponent("kg") == "kg"

    def test_empty_string(self):
        """Test empty string."""
        assert fix_exponent("") == ""

    def test_mixed_separators(self):
        """Test units with different separators."""
        assert fix_exponent("kg*m2/s-2") == "kg*m^2/s^-2"
        assert fix_exponent("N*m-1") == "N*m^-1"

    @pytest.mark.parametrize(
        "input_str,expected",
        [
            ("rad2", "rad^2"),
            ("Hz-1", "Hz^-1"),
            ("A2.V-1", "A^2.V^-1"),
            ("m/s2", "m/s^2"),
            ("kg.m2.s-2", "kg.m^2.s^-2"),
        ],
    )
    def test_various_formats(self, input_str, expected):
        """Test various FMU unit string formats."""
        assert fix_exponent(input_str) == expected


# ============================================================================
# Test to_pint_unit Function
# ============================================================================
class TestToPintUnit:
    """Test the to_pint_unit conversion function."""

    def test_simple_unit(self):
        """Test simple unit conversion."""
        unit = to_pint_unit("m")
        assert unit == ureg.meter

    def test_compound_unit(self):
        """Test compound unit conversion."""
        unit = to_pint_unit("m/s")
        assert unit == ureg.meter / ureg.second

    def test_unit_with_exponent(self):
        """Test unit with exponent (FMU format)."""
        unit = to_pint_unit("m2")
        assert unit == ureg.meter**2

    def test_negative_exponent(self):
        """Test unit with negative exponent."""
        unit = to_pint_unit("s-1")
        assert unit == ureg.second**-1

    def test_empty_string(self):
        """Test empty string returns dimensionless."""
        unit = to_pint_unit("")
        assert unit == ureg.dimensionless

    def test_none_input(self):
        """Test None input returns dimensionless."""
        unit = to_pint_unit(None)
        assert unit == ureg.dimensionless

    def test_invalid_unit_raises_error(self):
        """Test invalid unit string raises ValueError."""
        with pytest.raises(ValueError, match="Invalid unit string"):
            to_pint_unit("invalid_unit_xyz123")

    @pytest.mark.parametrize(
        "unit_str,expected_unit",
        [
            ("N*m", ureg.newton * ureg.meter),
            ("kg*m/s2", ureg.kilogram * ureg.meter / ureg.second**2),
            ("rad/s", ureg.radian / ureg.second),
            ("A2", ureg.ampere**2),
            ("m/s2", ureg.meter / ureg.second**2),
        ],
    )
    def test_common_units(self, unit_str, expected_unit):
        """Test common engineering units."""
        unit = to_pint_unit(unit_str)
        assert unit == expected_unit


# ============================================================================
# Test Quantity Creation and Operations
# ============================================================================
class TestQuantity:
    """Test Pint Quantity usage in SysSimX."""

    def test_create_quantity(self):
        """Test creating a quantity."""
        q = Quantity(5.0, "m")
        assert q.magnitude == 5.0
        assert q.units == ureg.meter

    def test_quantity_conversion(self):
        """Test unit conversion."""
        q = Quantity(1.0, "m")
        q_cm = q.to("cm")
        assert q_cm.magnitude == 100.0

    def test_compatible_units(self):
        """Test checking unit compatibility."""
        q1 = Quantity(1.0, "m")
        q2 = Quantity(100.0, "cm")
        assert q1.is_compatible_with(q2)

    def test_incompatible_units(self):
        """Test incompatible units."""
        q1 = Quantity(1.0, "m")
        q2 = Quantity(1.0, "kg")
        assert not q1.is_compatible_with(q2)

    def test_quantity_addition(self):
        """Test addition with compatible units."""
        q1 = Quantity(2.0, "m")
        q2 = Quantity(3.0, "m")
        q_sum = q1 + q2
        assert q_sum.magnitude == 5.0
        assert q_sum.units == ureg.meter

    def test_quantity_multiplication(self):
        """Test multiplication."""
        q1 = Quantity(2.0, "m")
        q2 = Quantity(3.0, "s")
        q_prod = q1 * q2
        assert q_prod.magnitude == 6.0
        assert q_prod.units == ureg.meter * ureg.second

    def test_quantity_division(self):
        """Test division."""
        q1 = Quantity(10.0, "m")
        q2 = Quantity(2.0, "s")
        q_div = q1 / q2
        assert q_div.magnitude == 5.0
        assert q_div.units == ureg.meter / ureg.second

    def test_dimensionality_error(self):
        """Test that incompatible operations raise errors."""
        q1 = Quantity(1.0, "m")
        q2 = Quantity(1.0, "kg")
        with pytest.raises(DimensionalityError):
            _ = q1 + q2


# ============================================================================
# Test Unit Registry Configuration
# ============================================================================
class TestUnitRegistry:
    """Test ureg configuration."""

    def test_ureg_exists(self):
        """Test that ureg is properly initialized."""
        assert ureg is not None

    def test_default_format(self):
        """Test default formatting."""
        q = Quantity(1.0, "meter")
        formatted = f"{q:~P}"
        assert "m" in formatted

    def test_autoconvert_offset(self):
        """Test temperature conversion with offset."""
        q_c = Quantity(0, "degC")
        q_k = q_c.to("kelvin")
        assert abs(q_k.magnitude - 273.15) < 1e-6

    def test_base_units(self):
        """Test basic SI units are available."""
        assert ureg.meter is not None
        assert ureg.kilogram is not None
        assert ureg.second is not None
        assert ureg.ampere is not None
        assert ureg.kelvin is not None
        assert ureg.mole is not None
        assert ureg.candela is not None


# ============================================================================
# Integration Tests (Realistic Usage Scenarios)
# ============================================================================
class TestUnitsIntegration:
    """Test units in realistic simulation scenarios."""

    def test_torque_units(self):
        """Test torque unit conversions."""
        torque_nm = Quantity(10.0, "N*m")
        torque_lbft = torque_nm.to("lbf*ft")
        assert torque_lbft.magnitude > 0
        # Verify conversion: 1 N*m ≈ 0.737562 lbf*ft
        expected = 10.0 * 0.737562
        assert abs(torque_lbft.magnitude - expected) < 0.01

    def test_angular_velocity_units(self):
        """Test angular velocity conversions."""
        omega = Quantity(1.0, "rad/s")
        omega_rpm = omega.to("revolution/minute")
        expected_rpm = 60 / (2 * 3.14159265358979)  # 1 rad/s in RPM
        assert abs(omega_rpm.magnitude - expected_rpm) < 0.01

    def test_angular_acceleration_units(self):
        """Test angular acceleration conversions."""
        alpha = Quantity(1.0, "rad/s^2")
        alpha_deg = alpha.to("degree/s^2")
        expected_deg = 180 / 3.14159265358979  # 1 rad/s^2 in deg/s^2
        assert abs(alpha_deg.magnitude - expected_deg) < 0.01

    def test_fmu_unit_parsing(self):
        """Test parsing typical FMU unit strings."""
        units_to_test = [
            ("rad", ureg.radian),
            ("rad/s", ureg.radian / ureg.second),
            ("rad/s2", ureg.radian / ureg.second**2),
            ("N.m", ureg.newton * ureg.meter),
            ("kg.m2", ureg.kilogram * ureg.meter**2),
        ]

        for unit_str, expected in units_to_test:
            parsed = to_pint_unit(unit_str)
            assert parsed == expected

    def test_moment_of_inertia(self):
        """Test moment of inertia units."""
        inertia = Quantity(1.0, "kg*m^2")
        assert inertia.dimensionality == (ureg.kilogram * ureg.meter**2).dimensionality

        # Convert to different units
        inertia_lbft2 = inertia.to("lb*ft^2")
        assert inertia_lbft2.magnitude > 0

    def test_power_units(self):
        """Test power unit conversions."""
        power_w = Quantity(1000.0, "W")
        power_hp = power_w.to("hp")
        expected_hp = 1000.0 / 745.7  # 1 W ≈ 0.001341 hp
        assert abs(power_hp.magnitude - expected_hp) < 0.01

    def test_energy_units(self):
        """Test energy unit conversions."""
        energy_j = Quantity(1000.0, "J")
        energy_kwh = energy_j.to("kW*hour")
        expected_kwh = 1000.0 / 3600000  # 1 J = 1/3600000 kWh
        assert abs(energy_kwh.magnitude - expected_kwh) < 1e-6


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================
class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_zero_quantity(self):
        """Test quantity with zero magnitude."""
        q = Quantity(0.0, "m")
        assert q.magnitude == 0.0

    def test_negative_quantity(self):
        """Test quantity with negative magnitude."""
        q = Quantity(-5.0, "m/s")
        assert q.magnitude == -5.0

    def test_very_large_number(self):
        """Test very large numbers."""
        q = Quantity(1e20, "m")
        assert q.magnitude == 1e20

    def test_very_small_number(self):
        """Test very small numbers."""
        q = Quantity(1e-20, "m")
        assert q.magnitude == 1e-20

    def test_dimensionless_quantity(self):
        """Test dimensionless quantities."""
        q = Quantity(5.0, "dimensionless")
        assert q.dimensionality == ureg.dimensionless.dimensionality

    def test_percentage_units(self):
        """Test percentage units."""
        q = Quantity(50, "percent")
        q_frac = q.to("dimensionless")
        assert abs(q_frac.magnitude - 0.5) < 1e-6
