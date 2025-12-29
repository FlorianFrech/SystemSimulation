from typing import Any, Dict

from SysSimX.components.fmu_comp import FMUComponent
from SysSimX.core.base import CoSimComponent
from SysSimX.core.events import Event
from SysSimX.core.port import PortSpec, PortType
from SysSimX.system.system import System, EventConnection
from SysSimX.system.connection import Connection

class TestComponents:
    REF_FMU_PATH = "tests/test_data/FMUs/Reference.fmu"
    SENSOR_FMU_PATH = "tests/test_data/FMUs/AngleEncoder.fmu"
    PID_FMU_PATH = "tests/test_data/FMUs/PID.fmu"
    DRIVE_FMU_PATH = "tests/test_data/FMUs/Drive.fmu"
    PENDULUM_FMU_PATH = "tests/test_data/FMUs/Pendulum.fmu"
    def __init__(self):
        self.REF          = FMUComponent("Reference", self.REF_FMU_PATH, group="Input")
        self.SENSOR_REF   = FMUComponent("SensorRef", self.SENSOR_FMU_PATH, group="Sensors")
        self.SENSOR_STATE = FMUComponent("SensorState", self.SENSOR_FMU_PATH, group="Sensors")
        self.PID          = FMUComponent("PID", self.PID_FMU_PATH, group="Controller")
        self.DRIVE        = FMUComponent("Drive", self.DRIVE_FMU_PATH, group="Actuator")
        self.PENDULUM     = FMUComponent("Pendulum", self.PENDULUM_FMU_PATH, group="Plant")

class SimpleEventSource(CoSimComponent):
    def __init__(self, name: str):
        super().__init__(name)

    def _initialize_component(self, t0: float) -> None:
        self.output_specs.update({
            "x": PortSpec(name="x", type=PortType.REAL, direction="out")
        })
        self._initialize_ports_from_specs()

    def _do_step_internal(self, t: float, dt: float) -> None:
        pass

    def _update_output_states(self, t: float) -> None:
        self.outputs["x"].set(0.0, t=t)

    def set_state(self, state: Dict[str, Any], t: float) -> None:
        pass

    def get_state(self) -> Dict[str, Any]:
        return {}

    def snapshot_state(self):
        return {"t": self.t}

    def restore_state(self, snapshot, t):
        self.t = t

    def reset(self) -> None:
        super().reset()

class SimpleEventListener(CoSimComponent):
    def __init__(self, name: str):
        super().__init__(name)

    def _initialize_component(self, t0: float) -> None:
        self.input_specs.update({
            "u": PortSpec(name="u", type=PortType.REAL, direction="in"),
            "event_a": PortSpec(name="event_a", type=PortType.EVENT, direction="in"),
        })
        self._initialize_ports_from_specs()

    def _do_step_internal(self, t: float, dt: float) -> None:
        pass

    def _update_output_states(self, t: float) -> None:
        pass

    def set_state(self, state: Dict[str, Any], t: float) -> None:
        pass

    def get_state(self) -> Dict[str, Any]:
        return {}

    def reset(self) -> None:
        super().reset()

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
    sys.add_connection(Connection("Pendulum", "q", "SensorState", "q"))
    sys.add_connection(Connection("Pendulum", "omega", "Drive", "omega"))
    sys.compute_execution_order()

    expected_order = [["Pendulum", "Reference"], ["SensorRef", "SensorState"], ["PID"], ["Drive"]]
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
    sys.add_connection(Connection("Pendulum", "q", "SensorState", "q"))
    sys.add_connection(Connection("Pendulum", "omega", "Drive", "omega"))
    sys.compute_execution_order()

    sys.initialize(0.0)
    omega_state_0 = pendulum.get_outputs()['omega']
    sys.run(t0=0.0, tf=1.0, dt=0.1)
    omega_state_1 = pendulum.get_outputs()['omega']
    assert omega_state_0 != omega_state_1  # Expect state to change after step

def test_add_event_connection():
    sys = System("EventSystem")
    source = SimpleEventSource("Source")
    listener = SimpleEventListener("Listener")
    sys.add_component(source)
    sys.add_component(listener)

    source.initialize(t0=0.0)
    listener.initialize(t0=0.0)

    source.add_event_indicator(
        name="event_a",
        func=lambda comp: 1.0,
        direction=0,
    )
    listener.subscribe_event(Event(name="event_a", source="Source"))

    conn = EventConnection(src_comp="Source", src_port="event_a", 
                           dst_comp="Listener", dst_port="event_a")
    sys.add_event_connection(conn)

    assert sys.get_event_targets("Source", "event_a") == ["Listener"]
