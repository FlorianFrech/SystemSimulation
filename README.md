# SysSimX

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)"
            srcset="./logo/dist/svg/syssimx_horizontal_dark.svg">
    <source media="(prefers-color-scheme: light)"
            srcset="./logo/dist/svg/syssimx_horizontal_light.svg">
    <img src="./logo/dist/svg/syssimx_horizontal_light.svg"
         alt="SysSimX"
         width="480">
  </picture>
</p>

**SysSimX** is a free and open-source Python library for system simulation.
It allows you to build hybrid and heterogeneous system models by connecting system component models from different environments, including:
- **FMU Components** - [Functional Mock-up Units (FMI 2.0 Co-Simulation)](https://fmi-standard.org/)
- **OpenSim Components** - Musculoskeletal biomechanics models using [OpenSim](https://opensim.stanford.edu/)
- **Structural-Dynamics FEM Components** - Transient structural-mechanics models using [NGSolve](https://ngsolve.org/) and Newmark time integration
- **Custom Python Components** - User-defined models implemented directly in Python

The library comes with a [user documentation site](https://syssimx.readthedocs.io/en/latest/) that includes installation instructions, core concepts, API references, and tutorials covering fundamental techniques, tool integrations, and a case study.

The public [brand assets](logo/dist/) include the light/dark wordmarks, application icons, favicons, and the GitHub social-preview image.

## Key Features

- **Graph-Based Execution:** Automatic dependency analysis with direct feedthrough and algebraic loop detection. Components are executed in topologically sorted order.

- **Algebraic Loop Handling:** Detection and iterative solving using the Interface Jacobian-based Co-Simulation Algorithm (IJCSA).

- **Hybrid Co-Simulation:** Event detection via zero-crossing indicators with bisection-based time localization and superdense time semantics.

- **Multiple Master Algorithms:** Choose from Jacobi (lagged inputs), Gauss-Seidel (sequential current-step propagation), or Hybrid (event-driven) algorithms. The current engine steps components serially.

- **Multi-Tool Integration:** Connect FMUs, OpenSim models, and NGSolve transient structural-dynamics models in a single system.

- **Multi-Model Switching:** Dynamically switch between multiple models of the same component during simulation.

- **Unit-Aware Connections:** Automatic unit conversion between ports using Pint.

- **Extensible Component API:** Base class for custom components with lifecycle methods for initialization, stepping, and output updates.

## Installation

The `syssimx` package is available on [PyPI](https://pypi.org/project/syssimx/). You can install it using `pip`. Optional extras are available for FMI, OpenSim, and NGSolve structural-dynamics support.

### Basic install

```bash
pip install syssimx
```

### Optional extras

```bash
pip install "syssimx[fmu]"
pip install "syssimx[fem]"
pip install "syssimx[opensim]"
pip install "syssimx[dev]"
pip install "syssimx[all]"
pip install "syssimx[full]"
```

### OpenSim note (important)

OpenSim 4.6 provides PyPI wheels for current CPython versions, including Python 3.13. For the non-conda path, install the OpenSim extra in a virtual environment:

```bash
pip install "syssimx[opensim]"
```

See the full installation guide:
- `docs/01_getting_started/01_installation.ipynb`

### Development with uv

For repository development, `uv` is the recommended package manager. It reads `pyproject.toml`, creates the project environment, installs SysSimX editable, and uses `uv.lock` for reproducible dependency resolution.

```powershell
uv sync --python 3.13 --extra all
uv run pytest tests
```

On Windows, use a short environment path if JupyterLab hits long path limits:

```powershell
$env:UV_PROJECT_ENVIRONMENT = "$env:USERPROFILE\.venvs\syssimx-313"
uv sync --python 3.13 --extra all
```

Build and publish releases with uv:

```powershell
uv build --no-sources
uv publish --index testpypi
uv publish
```

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
result = system.run(t0=0.0, tf=5.0, dt=0.1)

t_vals, data = result["Integrator"]
y_vals = data["y"]

plt.plot(t_vals, y_vals)
plt.xlabel("Time (s)")
plt.ylabel("Integrator output")
plt.title("SysSimX Quickstart")
plt.grid(True)
plt.show()
```

For the complete walkthrough, see:
- [Quickstart notebook](docs/01_getting_started/02_quickstart.ipynb)

The installable `syssimx_examples` namespace contains the controlled-pendulum
case-study implementation used by the documentation and framework-paper
experiments. Generated models and large result artifacts stay under
[`demos/ControlledPendulum`](demos/ControlledPendulum/); they are not bundled in
the Python wheel.

## Documentation

- [Documentation entry](docs/index.rst)
- [Installation guide](docs/01_getting_started/01_installation.ipynb)
- [Core concepts](docs/01_getting_started/03_concepts.ipynb)
- [Quickstart tutorial](docs/01_getting_started/02_quickstart.ipynb)
- [API docs](docs/02_api/)
- Tutorials and case studies:
  - [Core tutorials](docs/03_core_tutorials/)
  - [Tool integration](docs/04_tool_integration/)
  - [Case study](docs/05_case_study/)

## Project Status

SysSimX is under active development. APIs and behavior may evolve as algorithms and component integrations are extended.

## License

- Project license: MIT (`LICENSE`)
- Third-party dependencies and attributions: `THIRD_PARTY_LICENSES.MD`
