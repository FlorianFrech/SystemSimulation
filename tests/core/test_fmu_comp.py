from SysSimX.core.fmu_comp import FMUComponent

fmu_path = "tests/test_data/FMU/Pendulum.fmu"

def test_init():
    comp = FMUComponent("Pendulum", fmu_path=fmu_path)
    assert comp.input_specs['torque'].name == "torque"

def test_build_port_specs():
    pass

def test_buil_value_reference_map():
    pass

def test_initialize():
    pass

def test_set_parameters():
    pass

def test_set_inputs():
    pass

def test_do_step():
    pass

def test_get_outputs():
    pass

def test_set_state():
    pass

def test_get_state():
    pass

def test_reset():
    pass