from SysSimX.core.fmu_comp import FMUComponent
from SysSimX.system.system import System
from SysSimX.system.connection import Connection

class TestComponents:
    REF_FMU_PATH = "tests/test_data/FMU/Reference.fmu"
    SENSOR_FMU_PATH = "tests/test_data/FMU/AngleEncoder.fmu"
    PID_FMU_PATH = "tests/test_data/FMU/PID.fmu"
    DRIVE_FMU_PATH = "tests/test_data/FMU/Drive.fmu"
    PENDULUM_FMU_PATH = "tests/test_data/FMU/Pendulum.fmu"

    def __init__(self):
        self.REF          = FMUComponent("Reference", self.REF_FMU_PATH, group="Input")
        self.SENSOR_REF   = FMUComponent("SensorRef", self.SENSOR_FMU_PATH, group="Sensors")
        self.SENSOR_STATE = FMUComponent("SensorState", self.SENSOR_FMU_PATH, group="Sensors")
        self.PID          = FMUComponent("PID", self.PID_FMU_PATH, group="Controller")
        self.DRIVE        = FMUComponent("Drive", self.DRIVE_FMU_PATH, group="Actuator")
        self.PENDULUM     = FMUComponent("Pendulum", self.PENDULUM_FMU_PATH, group="Plant")

def test_init():
    sys = System("TestSystem")
    assert sys.name == "TestSystem"
    assert sys.components == {}
    assert sys.connections == []
    assert sys.groups == {}
    assert sys.execution_order == []
    assert sys.execution_idx == {}

def test_add_component():
    sys = System("TestSystem")
    comps = TestComponents()
    sys.add_component(comps.REF)
    assert "Reference" in sys.components
    try:
        sys.add_component(comps.REF)
        assert False, "Expected ValueError for adding duplicate component"
    except ValueError as e:
        assert True, str(e)
    assert sys.groups == {"Input": [comps.REF]}

def test_add_connection():
    sys = System("TestSystem")
    comps = TestComponents()
    ref = comps.REF
    sensor = comps.SENSOR_REF
    sys.add_component(ref)
    sys.add_component(sensor)
    conn = Connection("Reference", "q_ref", "SensorRef", "q")
    sys.add_connection(conn)

    assert sys.connections == [conn]

    conn_invalid = Connection("Reference", "invalid_port", "SensorRef", "q")
    try:
        sys.add_connection(conn_invalid)
        assert False, "Expected KeyError for invalid source port"
    except KeyError as e:
        assert True, str(e)

    # TODO: add tests for comp existence, port existence, type/unit compatibility, duplicate connections

def test_compute_execution_order():
    sys = System("TestSystem")
    comps = TestComponents()
    ref = comps.REF
    sensor_ref = comps.SENSOR_REF
    sensor_state = comps.SENSOR_STATE
    pid = comps.PID
    drive = comps.DRIVE
    pendulum = comps.PENDULUM

    for comp in [ref, sensor_ref, sensor_state, pid, drive, pendulum]:
        sys.add_component(comp)

    sys.add_connection(Connection("Reference", "q_ref", "SensorRef", "q"))
    sys.add_connection(Connection("SensorRef", "U_q", "PID", "ref"))
    sys.add_connection(Connection("SensorState", "U_q", "PID", "y"))
    sys.add_connection(Connection("PID", "u", "Drive", "u_control"))
    sys.add_connection(Connection("Drive", "torque", "Pendulum", "torque"))
    sys.add_connection(Connection("Pendulum", "q_state", "SensorState", "q", delay=1))
    sys.add_connection(Connection("Pendulum", "omega_state", "Drive", "omega", delay=1))
    sys.compute_execution_order()

    expected_order = [["Reference", "SensorState"], ["SensorRef"], ["PID"], ["Drive"], ["Pendulum"]]
    assert sys.execution_order == expected_order

    # TODO: add test for cycle detection and invalid connections

def test_step():
    sys = System("TestSystem")
    comps = TestComponents()
    ref = comps.REF
    sensor_ref = comps.SENSOR_REF
    sensor_state = comps.SENSOR_STATE
    pid = comps.PID
    drive = comps.DRIVE
    pendulum = comps.PENDULUM

    for comp in [ref, sensor_ref, sensor_state, pid, drive, pendulum]:
        sys.add_component(comp)

    sys.add_connection(Connection("Reference", "q_ref", "SensorRef", "q"))
    sys.add_connection(Connection("SensorRef", "U_q", "PID", "ref"))
    sys.add_connection(Connection("SensorState", "U_q", "PID", "y"))
    sys.add_connection(Connection("PID", "u", "Drive", "u_control"))
    sys.add_connection(Connection("Drive", "torque", "Pendulum", "torque"))
    sys.add_connection(Connection("Pendulum", "q_state", "SensorState", "q", delay=1))
    sys.add_connection(Connection("Pendulum", "omega_state", "Drive", "omega", delay=1))
    sys.compute_execution_order()

    sys.initialize(0.0)
    omega_state_0 = pendulum.get_outputs()['omega_state']
    sys.step(t=0.0, dt=0.1)
    omega_state_1 = pendulum.get_outputs()['omega_state']
    assert omega_state_0 != omega_state_1  # Expect state to change after step