Co-Simulation Components
===================================

FMU Component
-------------

.. automodule:: syssimx.components.fmu
   :members:
   :undoc-members:
   :show-inheritance:

NGSolve Structural-Dynamics FEM Component
-----------------------------------------

``FEMComponent`` is an abstract base for transient structural mechanics in
NGSolve. It supplies constant-average-acceleration Newmark state management,
micro-stepping, rollback, and field-history support. Subclasses still define
the mesh, finite-element spaces, variational form, solver, ports, and physical
state mapping. It is not a backend-neutral adapter for arbitrary FEM analyses.

.. automodule:: syssimx.components.fem
   :members:
   :undoc-members:
   :show-inheritance:

OpenSim Component
-----------------

.. automodule:: syssimx.components.opensim
   :members:
   :undoc-members:
   :show-inheritance:
