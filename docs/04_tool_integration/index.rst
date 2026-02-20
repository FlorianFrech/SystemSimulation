Tool Integration
======================

In this tutorial section, we explore how to integrate models from

- ``Modelica`` via ``OMPython`` as ``FMUComponent``
- Musculoskeletal models from ``OpenSim`` as ``OpenSimComponent``, and 
- finite element models from ``Netgen/NGSolve`` as ``FEMComponent``

in the ``syssimx`` framework.

The tool integration tutorials focus on the implementation of pendulum models using different modeling approaches.

Each tutorial provides step-by-step instructions on how to set up the models.

Equivalent pendulum models as `CoSimComponent` implementations can be found in
the `demos/ControlledPendulum/src/master_pendulum` directory of the
`syssimx` repository.

.. toctree::
   :maxdepth: 2
   :numbered:

   01_modelica/index
   02_opensim/index
   03_fem/index
   04_master_pendulum/index
