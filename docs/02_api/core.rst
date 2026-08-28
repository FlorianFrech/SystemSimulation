Core API
========

Runtime model switching
-----------------------

Runtime replacement of one component model by another is a primary SysSimX
API. A :class:`~syssimx.MultiComponent` keeps the system-facing ports and
connections stable while a :class:`~syssimx.SwitchRegions` map selects the
active internal model. Switching is handled as a localized hybrid event, and
every committed transition is exposed as a typed
:class:`~syssimx.ModeSwitchEvent` through ``component.switch_events`` and the
returned :class:`~syssimx.SimulationResult`.

.. autoclass:: syssimx.MultiComponent
   :members: set_switch_regions, switch_regions, active_mode, active_comp, switch_events
   :show-inheritance:

.. autoclass:: syssimx.SwitchRegions
   :members: breakpoints, bands, initial_region

.. autoclass:: syssimx.ModeSwitchEvent

Component contract
------------------

A custom component declares ``input_specs`` and ``output_specs`` in its
constructor and implements exactly three required lifecycle hooks:
``_initialize_component``, ``_do_step_internal``, and
``_update_output_states``. State transfer, exact rollback, event indicators,
and direct-feedthrough evaluation are opt-in capabilities, not requirements
of a basic component.

.. autoclass:: syssimx.CoSimComponent
   :members: _initialize_component, _do_step_internal, _update_output_states, initialize, set_inputs, get_outputs, do_step, get_history, get_history_arrays, reset, free
   :show-inheritance:

Ports
-----

Port specifications are immutable and validated when constructed. The key in
``input_specs`` or ``output_specs`` must equal ``PortSpec.name``, and the
declared direction must match the collection containing it.

.. autoclass:: syssimx.PortSpec
   :members: validate_value, compatible

.. autoclass:: syssimx.PortType
   :members:

.. autoclass:: syssimx.core.port.PortState
   :members: set, get

Hybrid events
-------------

.. autoclass:: syssimx.core.events.EventIndicator
   :members: evaluate

.. autoclass:: syssimx.core.events.Event

.. autoclass:: syssimx.core.events.DenseTime
   :members: advance_micro, to_float

.. autoclass:: syssimx.core.events.InternalEventInfo
   :members: interval_width

History
-------

.. autoclass:: syssimx.core.history.PortHistory
   :members: get_values, to_dict, to_tuple

.. autoclass:: syssimx.core.history.ComponentHistory
   :members: get_port_history, get_all_histories, mode_switch_events, to_dict, to_arrays

.. autoclass:: syssimx.core.history.SystemHistory
   :members: get_component_history, get_all_histories, get_event_history, get_all_event_histories, get_mode_switch_history, get_all_mode_switch_histories
