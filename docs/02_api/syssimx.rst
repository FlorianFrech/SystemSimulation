Public API
==========

SysSimX deliberately keeps the stable, top-level API small. The following
names can be imported directly from ``syssimx``:

Core simulation
---------------

- :class:`~syssimx.System`
- :class:`~syssimx.Connection` and :class:`~syssimx.EventConnection`
- :class:`~syssimx.CoSimComponent`
- :class:`~syssimx.PortSpec` and :class:`~syssimx.PortType`
- :class:`~syssimx.SimulationResult`

Runtime model switching
-----------------------

- :class:`~syssimx.MultiComponent`
- :class:`~syssimx.SwitchRegions`
- :class:`~syssimx.ModeSwitchEvent`

These switching types are the primary interface for event-localized runtime
model replacement. See :doc:`core` for the contract and
:doc:`../03_core_tutorials/03_advanced/04_multi_component_switching` for a
worked example.

Optional integrations
---------------------

``FMUComponent``, ``FEMComponent``, and ``OpenSimComponent`` are available
when their backend extras are installed. ``SystemGraphVisualizer`` requires
the ``viz`` extra. See :doc:`components` and :doc:`viz`.

The loader and command-line interface are experimental and intentionally not
part of this stable top-level surface. See the warning in :doc:`system`.
