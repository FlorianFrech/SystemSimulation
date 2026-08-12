Netgen/NGSolve
==============


.. figure:: /_static/fem_pendulum_swing.gif
   :alt: FEM pendulum swing
   :width: 600px

   Animation of the FEM pendulum swing.


This sequence builds a nonlinear, deformable pendulum model step by step using Netgen/NGSolve, starting from core dynamics and extending to actuation and contact.

The notebooks first derive and exercise the NGSolve model directly. The
reusable SysSimX integration point is
:class:`~syssimx.components.fem.FEMComponent`, an abstract base specifically
for transient structural dynamics with Newmark integration. The case-study
``FEMPendulum`` subclass supplies the pendulum mesh, spaces, variational form,
nonlinear solver, ports, state mapping, and contact behavior. This adapter is
not a generic wrapper for static, thermal, or arbitrary NGSolve analyses.

From NGSolve Model to ``FEMComponent``
--------------------------------------

A structural adapter defines its port contract during construction and
implements three required hooks:

1. ``_initialize_component(t0)`` builds the mesh, spaces, Newmark state,
   variational form, and solver.
2. ``_solve_step()`` solves one internal structural sub-step using the value
   already stored in ``tau_step``.
3. ``_update_output_states(...)`` maps the finite-element state to output
   ports.

The base class then owns the macro-step loop, Newmark state shift and update,
accepted-step history, and complete rollback snapshots. A minimal subclass has
the following shape:

.. code-block:: python

   from ngsolve import Parameter

   from syssimx.components import FEMComponent
   from syssimx.core import PortSpec, PortType


   class StructuralModel(FEMComponent):
       def __init__(self, name: str):
           super().__init__(name)
           self.input_specs = {
               "load": PortSpec("load", PortType.REAL, "in", unit="N")
           }
           self.output_specs = {
               "displacement": PortSpec(
                   "displacement", PortType.REAL, "out", unit="m"
               )
           }

       def _initialize_component(self, t0: float) -> None:
           self._mesh = build_mesh()
           self._fes = build_structural_space(self._mesh)
           self._init_newmark_state(self._fes)
           self.tau_step = Parameter(0.0)
           self._solver = build_variational_solver(self)

       def _solve_step(self) -> None:
           self._solver.solve()

       def _update_output_states(self, t=None, event_names=None) -> None:
           value = extract_displacement(self._gf_u)
           self.outputs["displacement"].set(value, t=t)

For contact or adaptive integration, override ``_pre_solve`` and
``_post_solve``. Implement ``get_state`` and ``set_state`` when the component
participates in runtime model switching. Register event indicators and report
internal event intervals when the hybrid master must localize structural
events. The full pendulum implementation is the reference for those optional
capabilities.

Main takeaways across the three notebooks:

- The pendulum is modeled as a thin 2D hyperelastic body (Neo-Hookean, plane stress) with nonlinear elastodynamics. The 2D reduction is used for reduced computational cost.
- A hinge-like pivot is enforced with a mixed FE formulation (`VectorH1 + NumberSpace`) using mean-zero displacement constraints on the rotation edge.
- Time integration is performed with Newmark-style updates and nonlinear solves (`Variation(...)` + Newton minimization).
- A rigid-body proxy angle is extracted from the deformable solution for interpretation and verification.

What each tutorial does:

- ``01_fem_pendulum_basics``

  - Builds geometry/mesh, material law, FE spaces, and the full weak form (internal energy, inertia, gravity, hinge constraint).
  - Runs transient simulation and visualizes displacement and stress evolution.
  - Establishes the baseline model (no external torque, no contact).

- ``02_fem_pendulum_torque``

  - Adds pivot actuation by converting a desired torque into a zero-resultant traction distribution on the hinge boundary.
  - Implements this as a follower load so the traction remains normal to the deformed boundary during large rotations.
  - Verifies behavior with/without follower load and compares FEM response to a rigid-body reference (gravity off/on).

- ``03_fem_pendulum_contact``

  - Extends the actuated pendulum with wall contact by adding a second body and a contact boundary pair.
  - Uses an incremental normal-gap penalty energy to resist penetration and tracks minimum contact gap for diagnostics.
  - Compares non-adaptive vs adaptive time stepping for energy behavior and studies stiff vs compliant pendulum responses during impact.

.. toctree::
   :maxdepth: 1
   :numbered:

   01_fem_pendulum_basics
   02_fem_pendulum_torque
   03_fem_pendulum_contact
