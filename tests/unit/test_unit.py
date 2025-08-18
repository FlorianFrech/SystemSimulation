import pytest

import numpy as np
from typing import Union, Iterable

from SysSimX.core.units import Q, qty, parse_unit, have_same_dimensions, assert_compatible


class TestQtyFunction:
    """Test suite for the qty function."""
    
    @pytest.mark.parametrize("value, unit", [
        (1.0, "m"),
        (2, "kg"),
        ([1.0, 2.0], "m/s"),
        (np.array([1.0, 2.0]), "kg*m/s^2"),
    ])
    def test_qty_basic(self, value, unit):
        """Test basic functionality of qty function."""
        quantity = qty(value, unit)
        assert isinstance(quantity, Q)
        assert quantity.units == parse_unit(unit)
        np.testing.assert_array_equal(quantity.magnitude, np.asarray(value))
    
    def test_qty_float_input(self):
        """Test qty with float input."""
        result = qty(5.5, "m/s")
        assert isinstance(result, Q)
        assert result.magnitude == 5.5
        assert str(result.units) == "m/s"
    
    def test_qty_int_input(self):
        """Test qty with integer input."""
        result = qty(42, "kg")
        assert isinstance(result, Q)
        assert result.magnitude == 42.0  # numpy converts to float
        assert str(result.units) == "kg"
    
    def test_qty_numpy_array_input(self):
        """Test qty with numpy array input."""
        arr = np.array([1.0, 2.0, 3.0])
        result = qty(arr, "N")
        assert isinstance(result, Q)
        np.testing.assert_array_equal(result.magnitude, arr)
        assert str(result.units) == "N"
    
    def test_qty_list_input(self):
        """Test qty with list input."""
        values = [1.0, 2.0, 3.0, 4.0]
        result = qty(values, "W")
        assert isinstance(result, Q)
        np.testing.assert_array_equal(result.magnitude, np.array(values))
        assert str(result.units) == "W"
    
    def test_qty_tuple_input(self):
        """Test qty with tuple input."""
        values = (10.0, 20.0)
        result = qty(values, "J")
        assert isinstance(result, Q)
        np.testing.assert_array_equal(result.magnitude, np.array(values))
        assert str(result.units) == "J"
    
    def test_qty_complex_units(self):
        """Test qty with complex unit expressions."""
        result = qty(9.81, "m/s^2")
        assert isinstance(result, Q)
        assert result.magnitude == 9.81
        assert str(result.units) == "m/s²"
    
    def test_qty_dimensionless_units(self):
        """Test qty with dimensionless units."""
        result = qty(1.0, "")
        assert isinstance(result, Q)
        assert result.magnitude == 1.0
        assert result.dimensionless
    
    def test_qty_abbreviated_units(self):
        """Test qty with abbreviated SI units."""
        test_cases = [
            ("m", "m"),
            ("kg", "kg"),
            ("s", "s"),
            ("A", "A"),
            ("K", "K"),
            ("mol", "mol"),
            ("cd", "cd"),
            ("Hz", "Hz"),
            ("N", "N"),
            ("Pa", "Pa"),
            ("J", "J"),
            ("W", "W"),
            ("V", "V"),
            ("ohm", "Ω"),  # Note: ohm shows as Ω in abbreviated format
        ]
        
        for abbrev, expected in test_cases:
            result = qty(1.0, abbrev)
            assert str(result.units) == expected
    
    def test_qty_compound_abbreviated_units(self):
        """Test qty with compound abbreviated units."""
        result = qty(1.0, "m/s")
        assert str(result.units) == "m/s"
        
        result = qty(1.0, "kg*m/s^2")
        assert str(result.units) == "kg·m/s²"
        
        result = qty(1.0, "J/kg/K")
        assert str(result.units) == "J/K/kg"  # Pint orders units differently
    
    def test_qty_zero_value(self):
        """Test qty with zero value."""
        result = qty(0.0, "m")
        assert result.magnitude == 0.0
        assert str(result.units) == "m"
    
    def test_qty_negative_value(self):
        """Test qty with negative value."""
        result = qty(-5.0, "m/s")
        assert result.magnitude == -5.0
        assert str(result.units) == "m/s"
    
    def test_qty_large_array(self):
        """Test qty with large numpy array."""
        large_array = np.linspace(0, 100, 1000)
        result = qty(large_array, "m")
        np.testing.assert_array_equal(result.magnitude, large_array)
        assert str(result.units) == "m"
    
    def test_qty_mixed_numeric_types(self):
        """Test qty with mixed numeric types in iterable."""
        values = [1, 2.0, 3]  # mix of int and float
        result = qty(values, "kg")
        expected = np.array([1.0, 2.0, 3.0])
        np.testing.assert_array_equal(result.magnitude, expected)
    
    def test_qty_scientific_notation(self):
        """Test qty with scientific notation values."""
        result = qty(1e-6, "m")
        assert result.magnitude == 1e-6
        
        result = qty([1e3, 2e-3], "kg")
        np.testing.assert_array_equal(result.magnitude, np.array([1000.0, 0.002]))
    
    def test_qty_invalid_unit_raises_error(self):
        """Test that qty raises error for invalid units."""
        with pytest.raises(Exception):  # Pint raises UndefinedUnitError
            qty(1.0, "invalid_unit_xyz")
    
    def test_qty_empty_array(self):
        """Test qty with empty array."""
        result = qty([], "m")
        assert len(result.magnitude) == 0
        assert str(result.units) == "m"
    
    def test_qty_single_element_array(self):
        """Test qty with single element array."""
        result = qty([42.0], "kg")
        np.testing.assert_array_equal(result.magnitude, np.array([42.0]))
        assert str(result.units) == "kg"
    
    def test_qty_return_type_consistency(self):
        """Test that qty always returns numpy arrays for magnitude."""
        # Float input
        result = qty(5.0, "m")
        assert isinstance(result.magnitude, (float, np.floating))
        
        # List input 
        result = qty([1.0, 2.0], "m")
        assert isinstance(result.magnitude, np.ndarray)
        
        # Numpy array input
        result = qty(np.array([1.0, 2.0]), "m")
        assert isinstance(result.magnitude, np.ndarray)
    
    def test_qty_unit_parsing_edge_cases(self):
        """Test qty with various unit parsing edge cases."""
        # Dimensionless units
        result = qty(1.0, "dimensionless")
        assert result.dimensionless
        
        # Case sensitivity
        result1 = qty(1.0, "m")
        result2 = qty(1.0, "M")  # This might be different (mega) or same
        # Just test that both work without error
        assert isinstance(result1, Q)
        assert isinstance(result2, Q)
        
        # Unicode units
        result = qty(1.0, "°C")
        assert isinstance(result, Q)
    
    def test_qty_preserves_input_precision(self):
        """Test that qty preserves numerical precision."""
        high_precision = 1.23456789012345
        result = qty(high_precision, "m")
        assert result.magnitude == high_precision
        
        # Test with arrays
        precise_array = np.array([1.23456789012345, 9.87654321098765])
        result = qty(precise_array, "kg")
        np.testing.assert_array_equal(result.magnitude, precise_array)