SysSimX Documentation
=====================

.. image:: https://img.shields.io/badge/python-3.10+-blue.svg
   :alt: Python 3.10+

.. image:: https://img.shields.io/badge/license-MIT-green.svg
   :alt: MIT License

**SysSimX** is a free and open-source Python library for heterogeneous system co-simulation, 
enabling seamless integration of diverse simulation models including:

- **FMU Components** - `Functional Mock-up Units (FMI 2.0 Co-Simulation) <https://fmi-standard.org/>`_
- **FEM Components** - `Finite Element Method solvers (NGSolve) <https://ngsolve.org/>`_
- **OpenSim Components** - Musculoskeletal biomechanics models using `OpenSim <https://opensim.stanford.edu/>`_
- **Custom Python Components** - User-defined models implemented directly in Python

.. note::

   SysSimX is designed for researchers and engineers who need to couple
   multi-physics models from different simulation environments especially in
   the domains of mechanical, electrical, and biomechanical systems.

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
   Automatic dependency analysis with SCC-based generation scheduling
   for optimal parallel execution.

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

Contents
--------

.. toctree::
   :maxdepth: 2
   :caption: Getting Started
   :numbered:

   getting_started/installation
   getting_started/quickstart
   getting_started/concepts

.. toctree:: 
   :maxdepth: 2
   :caption: Theory and Background
   :numbered:

   user_guide/components
   user_guide/systems
   user_guide/hybrid
   theory_background/introduction
   theory_background/components
   theory_background/systems
   theory_background/hybrid

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/syssimx
   api/core
   api/components
   api/system
   api/algorithms
   api/utilities

.. toctree::
   :maxdepth: 2
   :caption: Tutorials

   tutorials/beginners/index
   tutorials/intermediate/index
   tutorials/advanced/index
   tutorials/tool_integration/index

.. toctree::
   :maxdepth: 1
   :caption: Development

   contributing
   changelog

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
