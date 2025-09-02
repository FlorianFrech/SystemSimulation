from typing import List, Dict
from .interfaces import CoSimComponent

def run_controlled_pendulum(ref: CoSimComponent,
                            sensor_ref: CoSimComponent,
                            sensor_state: CoSimComponent,
                            pid: CoSimComponent,
                            drive: CoSimComponent,
                            plant: CoSimComponent,
                            t0: float, tf: float, h: float,
                            logger = None):
    """
    Run a controlled pendulum simulation.
    """
    t = t0

    while t < tf - 1e-12:
        # 1) Get reference signal
        ref.step(t, h)
        q_ref = ref.get_outputs()['q_ref']

        # 2) Get plant outputs at current time
        plant_out = plant.get_outputs()
        q_state, omega_state = plant_out['q'], plant_out['omega']

        # 3) Feed reference and state to sensor models
        sensor_ref.set_inputs(q=q_ref); 
        sensor_state.set_inputs(q=q_state)
        
        sensor_ref.step(t, h)
        sensor_state.step(t, h)

        U_q_ref = sensor_ref.get_outputs()['U_q']
        U_q_state = sensor_state.get_outputs()['U_q']

        # 4) Feed sensor outputs to PID controller
        pid.set_inputs(ref=U_q_ref, y=U_q_state)
        pid.step(t, h)
        u_pid = pid.get_outputs()['u']

        # 5) Drive
        drive.set_inputs(u_control=u_pid, omega=omega_state)
        drive.step(t, h)
        torque = drive.get_outputs()['torque']

        # 6) Apply torque to plant and step
        plant.set_inputs(torque=torque)
        plant.step(t, h)

        if logger:
            logger(t, dict(
                q_ref=q_ref, q_state=q_state, omega_state=omega_state,
                U_q_ref=U_q_ref, U_q_state=U_q_state,
                u_pid=u_pid, torque=torque
            ))
        
        t += h