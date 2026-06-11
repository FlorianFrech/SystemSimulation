SysSimX Documentation
=====================

.. image:: https://img.shields.io/badge/python-3.11+-blue.svg
   :alt: Python 3.11+

.. image:: https://img.shields.io/badge/license-MIT-green.svg
   :alt: MIT License

**SysSimX** is a free and open-source Python library for system simulation.
It allows you to build hybrid and heterogenous system models by connecting system component models from different environments, including:

- **FMU Components** - `Functional Mock-up Units (FMI 2.0 Co-Simulation) <https://fmi-standard.org/>`_
- **OpenSim Components** - Musculoskeletal biomechanics models using `OpenSim <https://opensim.stanford.edu/>`_
- **FEM Components** - Finite Element Models using `NGSolve <https://ngsolve.org/>`_
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
- Interested in tool integration? Check out :doc:`04_tool_integration/01_modelica/index`, :doc:`04_tool_integration/02_opensim/index`, :doc:`04_tool_integration/03_fem/index`, and :doc:`04_tool_integration/04_master_pendulum/index`.
- Curious about a case study? See :doc:`05_case_study/00_overview` and subsequent chapters.


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
   Detection and iterative solving using the Interface Jacobian-based 
   Co-Simulation Algorithm (IJCSA).

**Hybrid Co-Simulation**
   Event detection via zero-crossing indicators with bisection-based
   time localization and superdense time semantics.

**Multiple Master Algorithms**
   Choose from Jacobi (parallel), Gauss-Seidel (sequential), or
   Hybrid (event-driven) algorithms.

**Multi-Tool Integration**
   Seamlessly connect FMUs, OpenSim models, and NGSolve FEM models in a single system.

**Multi-Model Switching**
   Dynamically switch between multiple models of the same component during simulation.

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
   :caption: Project

   contributing

.. toctree::
   :caption: Other Links
   
   FMI Standard <https://fmi-standard.org/>
   Modelica Documentation <https://modelica.org>
   OpenModelica Documentation <https://openmodelica.org>
   OpenModelica Connection Editor <https://openmodelica.org/free-and-open-source-software/omconnectioneditoromedit/>
   NGSolve Documentation <https://ngsolve.org>
   OpenSim Documentation <https://simtk-confluence.stanford.edu/display/OpenSim/Documentation>
   OpenSim Creator <https://www.opensimcreator.com/>

Indices and Tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
