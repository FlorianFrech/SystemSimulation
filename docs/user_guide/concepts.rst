Core Concepts
=============

This section explains the fundamental concepts and architecture of SysSimX.

Architecture Overview
---------------------

SysSimX follows a modular architecture with clear separation of concerns:

.. code-block:: text

   ┌─────────────────────────────────────────────────────────┐
   │                      System                              │
   │  ┌─────────────────────────────────────────────────────┐│
   │  │              Master Algorithm                        ││
   │  │   (Jacobi / Gauss-Seidel / Hybrid)                  ││
   │  └─────────────────────────────────────────────────────┘│
   │                          │                               │
   │         ┌────────────────┼────────────────┐             │
   │         ▼                ▼                ▼             │
   │  ┌───────────┐    ┌───────────┐    ┌───────────┐       │
   │  │ Component │◄──►│ Component │◄──►│ Component │       │
   │  │   (FMU)   │    │   (FEM)   │    │ (OpenSim) │       │
   │  └───────────┘    └───────────┘    └───────────┘       │
   │         │                │                │             │
   │  ┌──────┴──────┐  ┌──────┴──────┐  ┌──────┴──────┐     │
   │  │ Ports/State │  │ Ports/State │  │ Ports/State │     │
   │  └─────────────┘  └─────────────┘  └─────────────┘     │
   └─────────────────────────────────────────────────────────┘

Components
----------

A **Component** (``CoSimComponent``) is the fundamental building block representing
a simulation subsystem. Components have:

**Ports**
   Input and output interfaces for data exchange:
   
   - ``REAL`` - Continuous floating-point values
   - ``INT`` - Integer values
   - ``BOOL`` - Boolean values
   - ``EVENT`` - Discrete event signals

**State**
   Internal dynamic state that evolves over time.

**Parameters**
   Configurable values set before simulation.

**Lifecycle Methods**
   - ``initialize(t0)`` - Set up initial conditions
   - ``do_step(t, dt)`` - Advance simulation by dt
   - ``reset()`` - Return to clean state

Component Types
^^^^^^^^^^^^^^^

SysSimX provides specialized components for different simulation tools:

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - Type
     - Class
     - Description
   * - FMU
     - ``FMUComponent``
     - FMI 2.0 Co-Simulation FMUs
   * - FEM
     - ``FEMComponent``
     - NGSolve finite element models
   * - OpenSim
     - ``OpenSimComponent``
     - Musculoskeletal dynamics
   * - Custom
     - Subclass ``CoSimComponent``
     - User-defined components

Connections
-----------

A **Connection** links an output port of one component to an input port of another:

.. code-block:: python

   Connection(
       src_comp="ComponentA",  # Source component name
       src_port="y",           # Output port name
       dst_comp="ComponentB",  # Destination component name
       dst_port="u"            # Input port name
   )

**Unit Conversion**
   If ports have different but compatible units, SysSimX automatically
   converts values using Pint.

**Direct Feedthrough**
   When an output depends algebraically on an input (no dynamics),
   this creates potential algebraic loops.

Systems
-------

A **System** orchestrates components and manages simulation execution:

.. code-block:: python

   system = System(name="MySystem")
   system.add_component(comp_a)
   system.add_component(comp_b)
   system.add_connection(conn)
   system.initialize(t0=0.0)
   system.run(t0=0.0, tf=10.0, dt=0.01)

**Execution Order**
   SysSimX analyzes the connection graph to determine optimal execution order,
   grouping components into generations that can run in parallel.

**Algebraic Loops**
   Cycles of direct feedthrough connections are detected as Strongly Connected
   Components (SCCs) and solved iteratively.

Master Algorithms
-----------------

The **Algorithm** controls how components are stepped through time:

Jacobi Algorithm
^^^^^^^^^^^^^^^^

All components step in parallel with inputs from the previous time step.

- **Pros**: Maximum parallelism, decoupled execution
- **Cons**: Lower accuracy, stability limits

Gauss-Seidel Algorithm
^^^^^^^^^^^^^^^^^^^^^^

Components step sequentially, using updated values as they become available.

- **Pros**: Higher accuracy, better stability
- **Cons**: Sequential execution, no parallelism

Hybrid Algorithm
^^^^^^^^^^^^^^^^

Extends Gauss-Seidel with event detection and handling:

- Zero-crossing detection via event indicators
- Bisection-based event time localization
- Superdense time for simultaneous events
- Commutativity checking for event handlers

.. code-block:: python

   from syssimx.system.algorithms import HybridAlgorithm
   
   system.algorithm = HybridAlgorithm()
   system.algorithm.tol_time = 1e-6  # Event localization tolerance

History and Results
-------------------

Components automatically record output values over time:

.. code-block:: python

   # Get history as dictionary
   history = component.get_history()
   # Returns: {"port_name": {"time": [...], "values": [...], "unit": "..."}}
   
   # Get history as numpy arrays
   time_array, data_dict = component.get_history_arrays()
   # time_array: np.ndarray of time points
   # data_dict: {"port_name": np.ndarray of values}

Units
-----

SysSimX uses `Pint <https://pint.readthedocs.io/>`_ for physical units:

.. code-block:: python

   from syssimx.utilities.units import ureg, Quantity
   
   # Create quantities
   length = 1.5 * ureg.meter
   velocity = Quantity(10.0, "m/s")
   
   # Unit conversion happens automatically in connections
   # if ports have compatible units

Next: :doc:`components`
