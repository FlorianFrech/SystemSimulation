System API
==========

Assembly and execution
----------------------

.. autoclass:: syssimx.System
   :members: add_component, add_connection, add_event_connection, set_algorithm, initialize, run, get_history, describe, reset

.. autoclass:: syssimx.Connection
   :members: key

.. autoclass:: syssimx.EventConnection
   :members: event_name, target_comp, key

Results
-------

``SimulationResult`` preserves the unit metadata recorded by component ports.
Long-format tables include a ``unit`` column, wide tables store units in
``DataFrame.attrs['units']``, and wide CSV headers include units. Malformed or
misaligned histories raise an exception instead of being silently omitted.
DataFrame and CSV support requires the ``results`` installation extra.

.. autoclass:: syssimx.SimulationResult
   :members: from_system, component_names, to_dataframe, to_csv

Experimental declarative loader and CLI
---------------------------------------

.. warning::

   The YAML/JSON schema, loader functions, and ``syssimx`` command-line
   interface are experimental. They may change between minor releases and are
   not part of the stable framework API. YAML input requires the ``config``
   installation extra; JSON uses the Python standard library.

.. autofunction:: syssimx.system.loader.load_config

.. autofunction:: syssimx.system.loader.build_system

.. autofunction:: syssimx.system.loader.run_from_config

.. autoexception:: syssimx.system.loader.ConfigError
