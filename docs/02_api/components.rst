Backend Components
==================

FMU component
-------------

.. autoclass:: syssimx.components.fmu.FMUComponent
   :members: initialize, do_step, get_state, set_state, reset, free
   :show-inheritance:

NGSolve structural-dynamics FEM component
-----------------------------------------

``FEMComponent`` is an abstract base for transient structural mechanics in
NGSolve. It supplies constant-average-acceleration Newmark state management,
micro-stepping, rollback, and field-history support. Subclasses define the
mesh, finite-element spaces, variational form, solver, ports, and physical
state mapping.

.. autoclass:: syssimx.components.fem.FEMComponent
   :members: initialize, do_step, get_state, set_state, reset, free
   :show-inheritance:

OpenSim component
-----------------

.. autoclass:: syssimx.components.opensim.OpenSimComponent
   :members: initialize, do_step, get_state, set_state, reset, free
   :show-inheritance:
