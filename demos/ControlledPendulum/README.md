# Controlled Pendulum

Hybrid co-simulation benchmark for a torque-driven pendulum with interchangeable plant fidelity:
- `FEM` for high-fidelity structural dynamics.
- `OpenSim` for biomechanical multibody dynamics.
- `FMU` for fast Modelica-based co-simulation.

The `MasterPendulum` orchestrator composes these models behind one interface and can switch modes during runtime.

<img src="./artifacts/graphs/master_pendulum_system.svg" width="60%">

<img src="./artifacts/figures/master_pendulum/master_pendulum_contact.png" width="60%">


## Architecture

- **Orchestrator**: `src/master_pendulum/orchestration/master_pendulum.py`
- **Components**:
  - `src/master_pendulum/components/fem/`
  - `src/master_pendulum/components/opensim/`
  - `src/master_pendulum/components/fmu/`
- **Modelica source models**: `src/modelica/ControlledPendulum/`
- **Generated artifacts**: `artifacts/fmus/linux/`, `artifacts/figures/`, `artifacts/results/`

Core public API:

```python
from demos.ControlledPendulum.src import MasterPendulum, FEMPendulum, OpenSimPendulum, FMUPendulum
```

## Notebook Entry Points

- `notebooks/master_pendulum/`: mode-specific and combined pendulum experiments.
- `notebooks/system/no_contact/`: closed-loop baseline and algorithm verification.
- `notebooks/system/contact/`: hybrid/contact dynamics and event-driven switching.
- `notebooks/system/verification_algorithms/`: co-simulation algorithm comparison.

## FMU Workflow

Modelica FMUs can be generated/updated via:

```bash
python demos/ControlledPendulum/scripts/modelica_to_fmu.py
```

## Notes

- This demo is intended for comparative studies: fidelity vs. runtime, contact handling, and mode-switch consistency.
- Some notebooks/components require optional dependencies (e.g., OpenSim, FEM tooling, FMU tooling) available in your active environment.
