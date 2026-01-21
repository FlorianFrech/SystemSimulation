System Configuration
====================

This section covers advanced system configuration and execution.

Building Systems
----------------

Basic System Setup
^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from syssimx import System, Connection

   # Create system
   system = System(name="MySystem")

   # Add components
   system.add_component(component_a)
   system.add_component(component_b)
   system.add_component(component_c)

   # Add connections
   system.add_connection(Connection(
       src_comp="A", src_port="y",
       dst_comp="B", dst_port="u"
   ))

Connection Types
^^^^^^^^^^^^^^^^

**Signal Connections** - Continuous data flow:

.. code-block:: python

   Connection(
       src_comp="Sensor",
       src_port="measurement",
       dst_comp="Controller", 
       dst_port="feedback"
   )

**Event Connections** - Discrete event triggering:

.. code-block:: python

   from syssimx.system.connection import EventConnection

   EventConnection(
       src_comp="Detector",
       src_port="contact_event",
       dst_comp="Controller",
       dst_port="reset_trigger",
       direction=1  # Rising edge only
   )

Graph Analysis
--------------

After adding components and connections, SysSimX analyzes the system graph:

.. code-block:: python

   system.initialize(t0=0.0)

   # View execution order (generations)
   print(system.execution_order)
   # [['Source'], ['Filter', 'Gain'], ['Output']]

   # View detected algebraic loops
   print(system.algebraic_loops)
   # [['GainA', 'GainB']]  # Components in feedback loop

Execution Order
^^^^^^^^^^^^^^^

Components are grouped into **generations** based on dependencies:

- Generation 0: Components with no upstream dependencies
- Generation N: Components depending only on generations 0 to N-1

Components within the same generation can execute in parallel.

Algebraic Loops
^^^^^^^^^^^^^^^

When direct feedthrough connections form a cycle, an algebraic loop exists.
SysSimX detects these as Strongly Connected Components (SCCs) and solves
them iteratively using the IJCSA algorithm:

.. code-block:: python

   # Adjust solver settings
   from syssimx.system.algorithms.ijcsa import solve_algebraic_scc_ijcsa

   # Default tolerance and max iterations are used
   # tol=1e-6, max_iter=50

Master Algorithms
-----------------

Selecting an Algorithm
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from syssimx.system.algorithms import (
       JacobiAlgorithm,
       GaussSeidelAlgorithm,
       HybridAlgorithm
   )

   # Jacobi (parallel)
   system.algorithm = JacobiAlgorithm()

   # Gauss-Seidel (sequential, higher accuracy)
   system.algorithm = GaussSeidelAlgorithm()

   # Hybrid (event-driven)
   system.algorithm = HybridAlgorithm()
   system.algorithm.verbose = True  # Enable logging

Algorithm Comparison
^^^^^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 20 25 25 30

   * - Algorithm
     - Execution
     - Accuracy
     - Use Case
   * - Jacobi
     - Parallel
     - Lower (explicit)
     - Large systems, loose coupling
   * - Gauss-Seidel
     - Sequential
     - Higher (implicit)
     - Stiff systems, tight coupling
   * - Hybrid
     - Sequential + Events
     - Highest
     - Discontinuities, mode switches

Running Simulations
-------------------

Basic Run
^^^^^^^^^

.. code-block:: python

   # Initialize
   system.initialize(t0=0.0)

   # Run simulation
   system.run(t0=0.0, tf=10.0, dt=0.001)

Custom Step Loop
^^^^^^^^^^^^^^^^

For finer control, use the step method directly:

.. code-block:: python

   system.initialize(t0=0.0)
   
   t = 0.0
   tf = 10.0
   dt = 0.001
   
   while t < tf:
       # Custom logic before step
       if t > 5.0:
           component.set_parameters(gain=2.0)
       
       # Execute one step
       system.algorithm.step(system, t, dt)
       t += dt
       
       # Custom logic after step
       if component.outputs["y"].get() > threshold:
           break

Retrieving Results
------------------

Component History
^^^^^^^^^^^^^^^^^

.. code-block:: python

   # Dictionary format
   history = component.get_history()
   # {"port_name": {"time": [...], "values": [...], "unit": "m"}}

   # NumPy arrays
   time, data = component.get_history_arrays()
   # time: np.ndarray, data: {"port_name": np.ndarray}

   # Specific ports with unit conversion
   history = component.get_history(
       port_names=["position", "velocity"],
       units={"position": "mm", "velocity": "mm/s"}
   )

System History
^^^^^^^^^^^^^^

.. code-block:: python

   # All component histories
   all_history = system.get_history()

   # Event history (for hybrid simulations)
   events = system.history.get_all_event_histories()
   # {("CompA", "event_name"): [DenseTime(t=0.5, micro=0), ...]}

Visualization
^^^^^^^^^^^^^

.. code-block:: python

   import matplotlib.pyplot as plt

   time, data = pendulum.get_history_arrays()

   fig, axes = plt.subplots(2, 1, figsize=(10, 8))
   
   axes[0].plot(time, data["q"], label="Angle")
   axes[0].set_ylabel("Angle (rad)")
   axes[0].legend()
   axes[0].grid(True)
   
   axes[1].plot(time, data["omega"], label="Angular velocity")
   axes[1].set_ylabel("Angular velocity (rad/s)")
   axes[1].set_xlabel("Time (s)")
   axes[1].legend()
   axes[1].grid(True)
   
   plt.tight_layout()
   plt.show()

System Graph Visualization
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from syssimx.viz import SystemGraphVisualizer

   visualizer = SystemGraphVisualizer(system)
   visualizer.visualize()  # Opens interactive graph

Advanced Configuration
----------------------

Component Groups
^^^^^^^^^^^^^^^^

Organize components logically:

.. code-block:: python

   plant = FMUComponent("Plant", fmu_path="...", group="Physical")
   controller = FMUComponent("PID", fmu_path="...", group="Control")
   sensor = FMUComponent("Encoder", fmu_path="...", group="Sensors")

Resetting Systems
^^^^^^^^^^^^^^^^^

.. code-block:: python

   # Reset all components
   for comp in system.components.values():
       comp.reset()

   # Re-initialize with different parameters
   plant.set_parameters(L=2.0)  # Changed parameter
   system.initialize(t0=0.0)

Next: :doc:`hybrid`
