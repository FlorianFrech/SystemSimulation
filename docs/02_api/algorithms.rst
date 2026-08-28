Master Algorithms
=================

Choose and configure an algorithm explicitly with
``system.set_algorithm(...)`` before initialization. A system containing
hybrid event sources uses :class:`HybridAlgorithm`: SysSimX promotes the
untouched default automatically, but rejects an explicitly selected
non-hybrid algorithm instead of silently replacing it. The configured
``HybridAlgorithm`` instance and its tolerances are preserved.

.. autoclass:: syssimx.system.algorithms.base.Algorithm
   :members: step
   :show-inheritance:

.. autoclass:: syssimx.system.algorithms.jacobi.JacobiAlgorithm
   :members: step
   :show-inheritance:

.. autoclass:: syssimx.system.algorithms.gauss_seidel.GaussSeidelAlgorithm
   :members: step
   :show-inheritance:

.. autoclass:: syssimx.system.algorithms.hybrid.HybridAlgorithm
   :members: step
   :show-inheritance:

.. autoclass:: syssimx.system.algorithms.ijcsa.IJCSAAlgorithm
   :members: step
   :show-inheritance:
