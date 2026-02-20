Changelog
=========

All notable changes to syssimx will be documented in this file.

The format is based on `Keep a Changelog <https://keepachangelog.com/>`_,
and this project adheres to `Semantic Versioning <https://semver.org/>`_.

[Unreleased]
------------

Added
^^^^^
- Comprehensive documentation with Sphinx
- User guide covering all major features
- Hybrid co-simulation examples

[0.1.0] - 2026-01-19
--------------------

Initial release of SysSimX.

Added
^^^^^

**Core Framework**

- ``CoSimComponent`` abstract base class for all simulation components
- Port system with ``PortSpec`` and ``PortState`` for typed I/O
- ``ComponentHistory`` for automatic output recording
- Unit handling with Pint integration

**Component Types**

- ``FMUComponent`` for FMI 2.0 Co-Simulation FMUs
- ``FEMComponent`` base class for NGSolve models
- ``OpenSimComponent`` for musculoskeletal models
- ``MultiComponent`` for hybrid multi-representation models

**System Orchestration**

- ``System`` class for component integration
- ``Connection`` and ``EventConnection`` data classes
- Graph-based dependency analysis with NetworkX
- Automatic algebraic loop detection (SCC analysis)
- Generation-based execution ordering

**Master Algorithms**

- ``JacobiAlgorithm`` for parallel stepping
- ``GaussSeidelAlgorithm`` for sequential stepping
- ``HybridAlgorithm`` for event-driven simulation
- ``IJCSAAlgorithm`` for algebraic loop solving

**Hybrid Co-Simulation**

- Event indicators for zero-crossing detection
- Bisection-based event time localization
- Superdense time (``DenseTime``) for event ordering
- Event handler commutativity checking
- Internal event hints for FEM micro-stepping

**Utilities**

- Unit registry based on Pint
- System graph visualization

**Testing**

- Comprehensive unit test suite
- Integration tests for algorithms
- Hybrid simulation test scenarios
