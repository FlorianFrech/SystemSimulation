Quick Start
===========

This guide walks you through creating your first co-simulation with SysSimX.
Prefer a runnable version? See :doc:`notebooks/quickstart`.

Your First Simulation
---------------------

Let's create a simple system with two components connected in series.

Step 1: Import SysSimX
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from syssimx import System, Connection
   from syssimx.core.base import CoSimComponent
   from syssimx.core.port import PortSpec, PortType

Step 2: Define a Custom Component
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Components must inherit from ``CoSimComponent`` and implement required methods:

.. code-block:: python

   class Integrator(CoSimComponent):
       """Simple Euler integrator: y = y + u * dt"""
       
       def __init__(self, name: str, x0: float = 0.0):
           super().__init__(name)
           self.x0 = x0
           self.x = x0
           
           # Define ports
           self.input_specs = {
               "u": PortSpec(name="u", type=PortType.REAL, direction="in")
           }
           self.output_specs = {
               "y": PortSpec(name="y", type=PortType.REAL, direction="out")
           }
       
       def _initialize_component(self, t0: float) -> None:
           self.x = self.x0
       
       def _do_step_internal(self, t: float, dt: float) -> None:
           u = self.inputs["u"].get() or 0.0
           self.x = self.x + u * dt
       
       def _update_output_states(self, t=None, event_names=None) -> None:
           self.outputs["y"].set(self.x, t=t)
       
       def set_state(self, state, t):
           self.x = state.get("x", self.x)
       
       def get_state(self):
           return {"x": self.x}

Step 3: Build the System
^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # Create components
   source = ConstantSource("Source", value=1.0)
   integrator = Integrator("Integrator", x0=0.0)

   # Create system
   system = System(name="IntegratorDemo")
   system.add_component(source)
   system.add_component(integrator)

   # Connect: Source.y -> Integrator.u
   system.add_connection(Connection(
       src_comp="Source", src_port="y",
       dst_comp="Integrator", dst_port="u"
   ))

Step 4: Run Simulation
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # Initialize at t=0
   system.initialize(t0=0.0)

   # Run for 10 seconds with dt=0.01
   system.run(t0=0.0, tf=10.0, dt=0.01)

   # Get results
   time, data = integrator.get_history_arrays()
   print(f"Final value: {data['y'][-1]}")  # Should be ~10.0

Step 5: Visualize Results
^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   import matplotlib.pyplot as plt

   time, data = integrator.get_history_arrays()
   
   plt.figure(figsize=(10, 6))
   plt.plot(time, data["y"], label="Integrator output")
   plt.xlabel("Time (s)")
   plt.ylabel("Value")
   plt.title("Simple Integration: y = ∫1 dt")
   plt.legend()
   plt.grid(True)
   plt.show()

Using FMU Components
--------------------

If you have FMU files, use the ``FMUComponent`` wrapper:

.. code-block:: python

   from syssimx.components import FMUComponent

   # Load FMU
   pendulum = FMUComponent(
       name="Pendulum",
       fmu_path="path/to/Pendulum.fmu",
       group="Plant"
   )

   # Set parameters before initialization
   pendulum.set_parameters(L=1.0, m=0.5, q0=0.1)

   # Add to system
   system = System("PendulumSystem")
   system.add_component(pendulum)
   system.initialize(t0=0.0)
   system.run(t0=0.0, tf=5.0, dt=0.001)

Next Steps
----------

- :doc:`concepts` - Understand the architecture
- :doc:`components` - Learn about component types
- :doc:`systems` - Advanced system configuration
- :doc:`hybrid` - Event-driven hybrid simulation
