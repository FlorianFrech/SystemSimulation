SysSimX Documentation
=====================

.. image:: https://img.shields.io/badge/python-3.11+-blue.svg
   :alt: Python 3.11+

.. image:: https://img.shields.io/badge/license-MIT-green.svg
   :alt: MIT License

**SysSimX** is a free and open-source Python library for system simulation.
It lets you build hybrid and heterogenous system models by connecting models from different environments, including:

- **FMU Components** - `Functional Mock-up Units (FMI 2.0 Co-Simulation) <https://fmi-standard.org/>`_
- **FEM Components** - `Finite Element Method solvers (NGSolve) <https://ngsolve.org/>`_
- **OpenSim Components** - Musculoskeletal biomechanics models using `OpenSim <https://opensim.stanford.edu/>`_
- **Custom Python Components** - User-defined models implemented directly in Python

.. note::

   SysSimX targets researchers and engineers who need to couple multi-physics
   models across simulation environments, especially in mechanical, electrical,
   and biomechanical systems.

Start Here
----------

- Want to install ``syssimx``? See :doc:`01_getting_started/01_installation`.
- New to ``syssimx``? Read the :doc:`01_getting_started/02_quickstart` and
  :doc:`01_getting_started/03_concepts`.
- Looking for APIs? Jump to the :doc:`02_api/syssimx`.
- Want hands-on learning? Go to :doc:`03_core_tutorials/01_fundamentals/index`.


Quick Example
-------------

.. code-block:: python

   from syssimx import System, Connection
   from syssimx.components import FMUComponent

   # Create and configure components
   pendulum = FMUComponent("Pendulum", fmu_path="Pendulum.fmu")
   controller = FMUComponent("PID", fmu_path="Controller.fmu")

   # Build system with connections
   system = System(name="ControlledPendulum")
   system.add_component(pendulum)
   system.add_component(controller)
   system.add_connection(Connection(
       src_comp="Pendulum", src_port="angle",
       dst_comp="PID", dst_port="measurement"
   ))

   # Run simulation
   system.initialize(t0=0.0)
   system.run(t0=0.0, tf=10.0, dt=0.001)

Key Features
------------

**Graph-Based Execution**
   Automatic dependency analysis with direct feedthrough and algebraic loop detection.
   Components are executed in topologically sorted order.

**Algebraic Loop Handling**
   Detection and iterative solving using the Interface-Jacobian 
   Co-Simulation Algorithm (IJCSA).

**Hybrid Co-Simulation**
   Event detection via zero-crossing indicators with bisection-based
   time localization and superdense time semantics.

**Multiple Master Algorithms**
   Choose from Jacobi (parallel), Gauss-Seidel (sequential), or
   Hybrid (event-driven) algorithms.

**Unit-Aware Connections**
   Automatic unit conversion between ports using Pint.

**Extensible Components**
   Implement custom components in Python or wrap external tools and FMUs.

Contents
--------

.. toctree::
   :maxdepth: 1
   :caption: Getting Started
   :numbered:

   01_getting_started/01_installation
   01_getting_started/02_quickstart
   01_getting_started/03_concepts

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   02_api/syssimx
   02_api/core
   02_api/components
   02_api/system
   02_api/algorithms
   02_api/utilities
   02_api/viz

.. toctree::
   :maxdepth: 2
   :caption: Core Tutorials

   03_core_tutorials/01_fundamentals/index
   03_core_tutorials/02_intermediate/index
   03_core_tutorials/03_advanced/index

.. toctree::
   :maxdepth: 2
   :caption: Tool Integration

   04_tool_integration/01_modelica/index
   04_tool_integration/02_opensim/index
   04_tool_integration/03_fem/index
   04_tool_integration/04_master_pendulum/index

.. toctree::
   :maxdepth: 1
   :caption: Case Study
   :numbered:

   05_case_study/00_overview
   05_case_study/01_baseline
   05_case_study/02_quantization
   05_case_study/03_algebraic_loop
   05_case_study/04_rigid_contact
   05_case_study/05_multi_model_switching

.. toctree::
   :caption: Other Links
   
   FMI Standard <https://fmi-standard.org/>
   Modelica Documentation <https://modelica.org>
   OpenModelica Documentation <https://openmodelica.org>
   OpenModelica Connection Editor <https://openmodelica.org/free-and-open-source-software/omconnectioneditoromedit/>
   NGSolve Documentation <https://ngsolve.org>
   OpenSim Documentation <https://simtk-confluence.stanford.edu/display/OpenSim/Documentation>
   OpenSim Creator <https://www.opensimcreator.com/>

.. .. toctree:: 
..    :maxdepth: 2
..    :caption: Theory and Background
..    :numbered:
   
..    theory_background/01_introduction
..    theory_background/02_systems_and_models
..    theory_background/03_time_stepping_and_integration
..    theory_background/04_dependency_graphs_and_ordering
..    theory_background/05_algebraic_loops
..    theory_background/06_co_simulation_algorithms
..    theory_background/07_hybrid_and_events
..    theory_background/08_units_and_interfaces

Indices and Tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
