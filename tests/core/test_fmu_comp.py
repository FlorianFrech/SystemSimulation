from pathlib import Path
from SysSimX.core.fmu_comp import FMUComponent
from SysSimX.utilities.units import ureg, Quantity

fmu_path_pendulum = "tests/test_data/FMU/Pendulum.fmu"
fmu_path_reference = "tests/test_data/FMU/Reference.fmu"

def test_init():
    comp = FMUComponent("Pendulum", fmu_path=fmu_path_pendulum, group="Plant")
    assert comp.name == "Pendulum"
    assert comp.group == "Plant"
    assert comp._path == str(Path(fmu_path_pendulum).resolve())
    assert comp.input_specs != {}
    assert comp.output_specs != {}
    assert comp._vrs_in_real != {}
    assert comp._vrs_out_real != {}
    assert comp.parameters != {}
    assert comp.input_specs['torque'].name == "torque"
    assert (1 * ureg(comp.input_specs['torque'].unit)).is_compatible_with(ureg("N*m"))

def test_initialize():
    comp = FMUComponent("Pendulum", fmu_path=fmu_path_pendulum, group="Plant")
    comp.initialize(t0=0.0)
    assert comp.inputs['torque'].spec.name == "torque"
    assert comp.outputs['q_state'].spec.name == "q_state"
    assert comp.outputs['omega_state'].spec.name == "omega_state"
    assert comp._instance is not None
    assert comp.outputs['q_state'].t_last == 0.0

def test_set_parameters():
    comp = FMUComponent("Pendulum", fmu_path=fmu_path_pendulum, group="Plant")
    comp.set_parameters(L=42)
    comp.initialize(t0=0.0)
    assert comp._instance.getReal([comp.parameters['L'].valueReference])[0] == 42

def test_set_inputs():
    comp = FMUComponent("Pendulum", fmu_path=fmu_path_pendulum, group="Plant")
    comp.initialize(t0=0.0)
    
    comp.set_inputs({"torque": 5}, t=0.0)
    torque_port = comp.inputs['torque']
    assert torque_port.value == Quantity(5, ureg(torque_port.spec.unit))
    assert torque_port.t_last == 0.0
    assert comp._instance.getReal([comp._vrs_in_real['torque']])[0] == 5

    comp.set_inputs({"torque": Quantity(10, ureg("N*m"))}, t=0.5)
    assert torque_port.value == Quantity(10, ureg(torque_port.spec.unit))
    assert torque_port.t_last == 0.5
    assert comp._instance.getReal([comp._vrs_in_real['torque']])[0] == 10

def test_update_output_states():
    comp = FMUComponent("Reference", fmu_path=fmu_path_reference, group="Input")
    comp.initialize(t0=0.0)
    q_ref_0 = comp._instance.getReal([comp._vrs_out_real['q_ref']])[0]
    comp._instance.doStep(currentCommunicationPoint=0.0, communicationStepSize=0.25)
    comp._update_output_states(t=0.25)
    q_ref_1 = comp._instance.getReal([comp._vrs_out_real['q_ref']])[0]
    assert q_ref_0 != q_ref_1

def test_do_step():
    comp = FMUComponent("Pendulum", fmu_path=fmu_path_pendulum, group="Plant")
    comp.set_parameters(L=0.5, q0=0, m=1)
    comp.initialize(t0=0.0)
    omega_0 = comp.outputs['omega_state'].value
    comp.set_inputs({"torque": 5}, t=0.0)
    torque_in = comp._instance.getReal([comp._vrs_in_real['torque']])[0]
    assert torque_in == 5
    comp.do_step(t=0.0, dt=1)
    omega_1 = comp._instance.getReal([comp._vrs_out_real['omega_state']])[0]
    assert omega_0 != omega_1

def test_get_outputs():
    comp = FMUComponent("Pendulum", fmu_path=fmu_path_pendulum, group="Plant")
    comp.initialize(t0=0.0)
    comp.set_inputs({"torque": 5}, t=0.0)
    comp.do_step(t=0.0, dt=1)
    outputs = comp.get_outputs()
    assert isinstance(outputs, dict)
    assert 'q_state' in outputs
    assert 'omega_state' in outputs
    assert isinstance(outputs['q_state'], Quantity)
    assert isinstance(outputs['omega_state'], Quantity)

def test_set_state():
    # TODO: Implement test
    pass

def test_get_state():
    # TODO: Implement test
    pass

def test_reset():
    comp = FMUComponent("Pendulum", fmu_path=fmu_path_pendulum, group="Plant")
    comp.initialize(t0=0.0)
    comp.set_inputs({"torque": 5}, t=0.0)
    comp.do_step(t=0.0, dt=1)
    comp.reset()
    assert comp._instance is None
    