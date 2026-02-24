# SysSimX

SysSimX is an open-source Python library for heterogeneous co-simulation.
It lets you build coupled systems from components with different model representations and simulation backends, then execute them with consistent orchestration logic.

## What SysSimX Provides

- Graph-based system orchestration with dependency analysis and execution ordering
- Algebraic loop detection and iterative handling (IJCSA-style workflow)
- Multiple master algorithms:
  - Jacobi (parallel-style updates)
  - Gauss-Seidel (sequential updates with fresh values)
  - Hybrid (event-aware stepping with zero-crossing support)
- Unit-aware port interfaces and conversion via Pint
- Reusable component abstractions for:
  - FMI 2.0 Co-Simulation FMUs
  - NGSolve-based FEM models
  - OpenSim models
  - Custom Python components

## Installation

### Basic install

```bash
pip install syssimx
```

### Optional extras

```bash
pip install "syssimx[fmu]"
pip install "syssimx[fem]"
pip install "syssimx[viz]"
pip install "syssimx[dev]"
pip install "syssimx[all]"
pip install "syssimx[full]"
```

### OpenSim note (important)

OpenSim is conda-only and ABI-coupled to specific NumPy/SciPy builds. Recommended order:

1. Install `syssimx` with `pip`.
2. Install OpenSim with `conda` using ABI-compatible NumPy/SciPy pins.

See the full installation guide:
- `docs/01_getting_started/01_installation.ipynb`

## Quickstart Example

The example below creates a simple linear source feeding an integrator.

```python
import matplotlib.pyplot as plt

from syssimx import CoSimComponent, Connection, System
from syssimx.core import PortSpec, PortType


class LinearSource(CoSimComponent):
    def __init__(self, name: str, a: float = 1.0, b: float = 0.0):
        super().__init__(name, group="Source")
        self.a = a
        self.b = b
        self.output_specs.update({
            "y": PortSpec(name="y", type=PortType.REAL, direction="out")
        })

    def _initialize_component(self, t0: float) -> None:
        pass

    def _do_step_internal(self, t: float, dt: float) -> None:
        pass

    def _update_output_states(self, t: float | None = None, event_names=None):
        t_now = 0.0 if t is None else t
        self.outputs["y"].set(self.a * t_now + self.b, t)


class Integrator(CoSimComponent):
    def __init__(self, name: str, x0: float = 0.0):
        super().__init__(name, group="Integrator")
        self.x0 = x0
        self.input_specs.update({
            "u": PortSpec(name="u", type=PortType.REAL, direction="in")
        })
        self.output_specs.update({
            "y": PortSpec(name="y", type=PortType.REAL, direction="out")
        })

    def _initialize_component(self, t0: float) -> None:
        self.x = self.x0
        self.outputs["y"].set(self.x, t0)

    def _do_step_internal(self, t: float, dt: float) -> None:
        u = self.inputs["u"].get()
        self.x = self.x + dt * float(u)

    def _update_output_states(self, t: float | None = None, event_names=None):
        self.outputs["y"].set(self.x, t)


source = LinearSource(name="LinearSource", a=1.0, b=0.0)
integrator = Integrator(name="Integrator", x0=0.0)

system = System(name="QuickstartSystem")
system.add_component(source)
system.add_component(integrator)
system.add_connection(Connection(
    src_comp="LinearSource", src_port="y",
    dst_comp="Integrator", dst_port="u",
))

system.initialize(t0=0.0)
system.run(t0=0.0, tf=5.0, dt=0.1)

history = system.get_history()
t_vals, data = history["Integrator"]
y_vals = data["y"]

plt.plot(t_vals, y_vals)
plt.xlabel("Time (s)")
plt.ylabel("Integrator output")
plt.title("SysSimX Quickstart")
plt.grid(True)
plt.show()
```

For the complete walkthrough, see:
- `docs/01_getting_started/02_quickstart.ipynb`

## Documentation

- Documentation entry: `docs/index.rst`
- Installation guide: `docs/01_getting_started/01_installation.ipynb`
- Core concepts: `docs/01_getting_started/03_concepts.ipynb`
- Quickstart tutorial: `docs/01_getting_started/02_quickstart.ipynb`
- API docs: `docs/02_api/`
- Tutorials and case studies:
  - `docs/03_core_tutorials/`
  - `docs/04_tool_integration/`
  - `docs/05_case_study/`

## Project Status

SysSimX is under active development. APIs and behavior may evolve as algorithms and component integrations are extended.

## License

- Project license: MIT (`LICENSE`)
- Third-party dependencies and attributions: `THIRD_PARTY_LICENSES.MD`
