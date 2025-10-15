from SysSimX.core.port import PortSpec, PortType, ureg
from pint import DimensionalityError

def test_spec_compatibility():
    # Compatible Real ports with same unit
    spec1 = PortSpec(name="port1", type=PortType.REAL, direction="in", unit="m/s")
    spec2 = PortSpec(name="port2", type=PortType.REAL, direction="out", unit="m/s")
    assert PortSpec.compatible(spec1, spec2)
    
    # Compatible Real ports with convertible units
    spec3 = PortSpec(name="port3", type=PortType.REAL, direction="in", unit="km/h")
    assert PortSpec.compatible(spec1, spec3)
    
    # Incompatible Real ports with different dimensions
    spec4 = PortSpec(name="port4", type=PortType.REAL, direction="in", unit="kg")
    assert not PortSpec.compatible(spec1, spec4)

    # Incompatible ports with different types
    spec5 = PortSpec(name="port5", type=PortType.INT, direction="in")
    assert not PortSpec.compatible(spec1, spec5)
    assert not PortSpec.compatible(spec5, spec1)

def test_real_port_spec():
    # Test Real port with unit
    real_port = PortSpec(name="speed",
                         type=PortType.REAL,
                         direction="in",
                         unit="m/s",
                         description="Speed in meters per second")
    assert real_port.name == "speed"
    assert real_port.type == PortType.REAL
    assert real_port.direction == "in"
    assert real_port.unit == "m/s"
    assert real_port.description == "Speed in meters per second"

    # Test validation for Real port with correct unit
    real_port.validate_value(10.0)             # Should not raise
    real_port.validate_value(5 * ureg("m/s"))  # Should not raise

    # Test validation for Real port with incorrect unit
    try:
        real_port.validate_value(5 * ureg("kg"))
        assert False, "Expected DimensionalityError for incompatible unit"
    except DimensionalityError:
        pass  # Expected

def test_int_port_spec():
    # Test Integer port without unit
    int_port = PortSpec(name="item_count",
                        type=PortType.INT,
                        direction="in",
                        description="Count of items")
    assert int_port.name == "item_count"
    assert int_port.type == PortType.INT
    assert int_port.unit is None
    assert int_port.description == "Count of items"
    
    # Test validation for Integer port with correct type
    int_port.validate_value(42)  # Should not raise
    
    # Test validation for Integer port with incorrect type
    try:
        int_port.validate_value(3.14)
        assert False, "Expected TypeError for incorrect type"
    except TypeError:
        pass  # Expected

def test_bool_port_spec():
    # Test Boolean port without unit
    bool_port = PortSpec(name="is_active",
                         type=PortType.BOOL,
                         direction="in",
                         description="Is the component active?")
    assert bool_port.name == "is_active"
    assert bool_port.type == PortType.BOOL
    assert bool_port.unit is None
    assert bool_port.description == "Is the component active?"
    
    # Test validation for Boolean port with correct type
    bool_port.validate_value(True)   # Should not raise
    bool_port.validate_value(False)  # Should not raise
    
    # Test validation for Boolean port with incorrect type
    try:
        bool_port.validate_value(1)
        assert False, "Expected TypeError for incorrect type"
    except TypeError:
        pass  # Expected

def test_string_port_spec():
    # Test String port without unit
    string_port = PortSpec(name="status",
                           type=PortType.STRING,
                           direction="out",
                           description="Status message")
    assert string_port.name == "status"
    assert string_port.type == PortType.STRING
    assert string_port.unit is None
    assert string_port.description == "Status message"
    
    # Test validation for String port with correct type
    string_port.validate_value("OK")  # Should not raise
    
    # Test validation for String port with incorrect type
    try:
        string_port.validate_value(100)
        assert False, "Expected TypeError for incorrect type"
    except TypeError:
        pass  # Expected