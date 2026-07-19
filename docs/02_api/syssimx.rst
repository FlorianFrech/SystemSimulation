SysSimX Package
===============

.. automodule:: syssimx
   :no-members:
   :no-undoc-members:
   :no-private-members:
   :no-inherited-members:
   :no-index:

The top-level package re-exports the most commonly used classes for convenient
imports. Detailed API documentation for those classes is available in the
module-specific pages in this API reference.

Re-exported names
-----------------

- :class:`~syssimx.core.base.CoSimComponent`, :class:`~syssimx.core.base.PortSpec`,
  :class:`~syssimx.core.base.PortType` — see :doc:`core`
- :class:`~syssimx.system.system.System`,
  :class:`~syssimx.system.connection.Connection`,
  :class:`~syssimx.system.connection.EventConnection`,
  :class:`~syssimx.system.results.SimulationResult` — see :doc:`system`
- :class:`~syssimx.viz.system_graph_visualizer.SystemGraphVisualizer` — see :doc:`viz`
- ``FMUComponent``, ``FEMComponent``, ``OpenSimComponent`` — available when the
  corresponding optional backend is installed; see :doc:`components`

The declarative loader (:func:`~syssimx.system.loader.build_system`,
:func:`~syssimx.system.loader.run_from_config`,
:func:`~syssimx.system.loader.load_config`,
:class:`~syssimx.system.loader.ConfigError`) is importable from
``syssimx.system``; see :doc:`system`.

Command-Line Interface
----------------------

.. automodule:: syssimx.cli
   :members:
   :undoc-members:
   :show-inheritance:
