from SysSimX.core.config import load_config
from SysSimX.components.fmu_component import FMUComponent
from SysSimX.components.opensim_pendulum import OpenSimPendulum
from SysSimX.core.scheduler import run_controlled_pendulum

def main(cfg_path: str):
    cfg = load_config(cfg_path)

    t0, tf, h = cfg["step"]["t0"], cfg["step"]["tf"], cfg["step"]["h"]

    # Build components
    ref   = FMUComponent("ref",   cfg["fmus"]["ReferenceTrajectory"]["path"],
                         inputs=cfg["fmus"]["ReferenceTrajectory"]["inputs"],
                         outputs=cfg["fmus"]["ReferenceTrajectory"]["outputs"])
    sref  = FMUComponent("sref",  cfg["fmus"]["SensorRef"]["path"],
                         inputs=cfg["fmus"]["SensorRef"]["inputs"],
                         outputs=cfg["fmus"]["SensorRef"]["outputs"])
    sstate= FMUComponent("sstate",cfg["fmus"]["SensorState"]["path"],
                         inputs=cfg["fmus"]["SensorState"]["inputs"],
                         outputs=cfg["fmus"]["SensorState"]["outputs"])
    pid   = FMUComponent("pid",   cfg["fmus"]["PID"]["path"],
                         inputs=cfg["fmus"]["PID"]["inputs"],
                         outputs=cfg["fmus"]["PID"]["outputs"])
    drive = FMUComponent("drive", cfg["fmus"]["Drive"]["path"],
                         inputs=cfg["fmus"]["Drive"]["inputs"],
                         outputs=cfg["fmus"]["Drive"]["outputs"])
    plant = OpenSimPendulum()

    # Initialize
    for c in (ref, sref, sstate, pid, drive, plant):
        c.initialize(t0)

    # Simple logger
    rows = []
    def log(t, signals): rows.append({"t":t, **signals})

    run_controlled_pendulum(ref, sref, sstate, pid, drive, plant, t0, tf, h, logger=log)

    # Example: print last line
    print(rows[-1])

if __name__ == "__main__":
    import sys
    main(sys.argv[1] if len(sys.argv)>1 else "SysSimX/demos/configs/demo_hybrid.yaml")