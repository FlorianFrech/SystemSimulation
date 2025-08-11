import pytest

from SysSimX.core.unit import Unit
import pint

Q_ = pint.UnitRegistry().Quantity

def test_unit_creation():
    u = Unit.from_string("m")
    assert str(u) == "meter"
    assert u.pint_unit.dimensionality == {"[length]": 1}

def test_unit_from_pint():
    ureg = pint.UnitRegistry()
    pint_unit = ureg.meter
    u = Unit.from_pint(pint_unit)
    assert str(u) == "meter"
    assert u.pint_unit.dimensionality == {"[length]": 1}

def test_dimensionless_unit():
    u = Unit.dimensionless()
    scalar = Q_(1)
    assert str(u) == "dimensionless"
    assert u.is_dimensionless
    assert u.pint_unit.dimensionality == scalar.dimensionality

def test_original_string():
    u = Unit.from_string("kg*m^2/s^2")
    assert u.original_string == "kg*m^2/s^2"
    assert str(u) == "kilogram * meter ** 2 / second ** 2"

def test_is_dimensionless():
    u = Unit.from_string("")
    assert u.is_dimensionless
