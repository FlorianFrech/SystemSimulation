import pytest

from SysSimX.core.fmu_comp import FMUComponent

#-----------------------------------------------------------------------------
# Test FMUComponent class
class TestFMUComponent:
    """Test suite for the FMUComponent class."""
    
    def test_construction(self):
        """Test basic construction of FMUComponent."""
        fmu_path = "tests/test_data/FMU/Pendulum.fmu"
        comp = FMUComponent(name="pendulum", fmu_path=fmu_path)
        assert comp.name == "pendulum"
        assert comp.path == fmu_path
        assert comp.inputs is not None
        assert comp.outputs is not None
        assert comp.parameters is not None
        assert comp._md is not None
        assert comp._vars is not None
        assert comp._instance is not None