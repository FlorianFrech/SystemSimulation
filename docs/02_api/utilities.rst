Unit Utilities
==============

Most users specify units as strings on :class:`~syssimx.PortSpec`; connection
conversion is then automatic. These helpers are available for integration
code that needs direct access to the shared Pint registry.

.. autodata:: syssimx.utilities.units.ureg

.. autofunction:: syssimx.utilities.units.to_pint_unit
