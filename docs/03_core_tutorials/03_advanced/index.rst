Advanced
======================

This section contains advanced tutorials that cover more of the hybrid simulation capabilities of the System Simulation framework.

This includes event chains, where events trigger other events in a chain reaction, and strong simultaneity, where multiple events occur at the same time and require careful handling to ensure correct simulation results.

Further we will introduce a concept of internal event reporting, where components can report events internally for more efficient system handling by the master algorithm.

Finally we look at runtime model switching, where one component of a running co-simulation is exchanged for an alternative model of the same subsystem, and at how expressing the switching condition as an event indicator places the transition on the crossing instead of on the communication grid.

.. toctree::
   :maxdepth: 1
   :numbered:

   01_hybrid_event_chain
   02_hybrid_strong_simultaneity
   03_hybrid_internal_reporting
   04_multi_component_switching
