Tool Integration
======================

In this tutorial section, we will explore how to include `FMUs` from `OpenModelica`, `Netgen/NGSolve` FEM, and `OpenSim` musculoskeletal Models into `syssimx` simulations.

The tool integration tutorials focus on the implementation of pendulum models using different modeling approaches.

Each tutorial provides step-by-step instructions on how to set up the models.

Equivalent pendulum models as `CoSimComponent` implementations can be found in the `demos\ControlledPendulum\src\master_pendulum` directory of the `syssimx` repository.

FEM
-----

.. toctree::
   :maxdepth: 1
   :numbered:

   fem/01_fem_pendulum_basics
   fem/02_fem_pendulum_torque
   fem/03_fem_pendulum_contact
