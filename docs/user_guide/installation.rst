Installation
============

Requirements
------------

SysSimX requires Python 3.10 or later.

**Core Dependencies** (installed automatically):

- ``numpy`` - Numerical computing
- ``pint`` - Physical units handling
- ``networkx`` - Graph algorithms

**Optional Dependencies** (for specific component types):

- ``fmpy`` - FMU co-simulation support
- ``ngsolve`` - FEM component support  
- ``opensim`` - OpenSim musculoskeletal models

Installation Methods
--------------------

From PyPI (Recommended)
^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   pip install syssimx

With optional dependencies:

.. code-block:: bash

   # For FMU support
   pip install syssimx[fmu]
   
   # For all optional dependencies
   pip install syssimx[all]

From Source (Development)
^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   git clone https://github.com/FlorianFrech/SystemSimulation.git
   cd SystemSimulation
   pip install -e ".[dev]"

Using Conda
^^^^^^^^^^^

.. code-block:: bash

   conda env create -f environment.yml
   conda activate syssimx

Verify Installation
-------------------

.. code-block:: python

   import syssimx
   print(syssimx.__version__)
   
   # Check available components
   from syssimx.components import FMUComponent  # Requires fmpy

Optional: NGSolve for FEM
-------------------------

NGSolve requires special installation:

.. code-block:: bash

   # Using pip (Linux/macOS)
   pip install ngsolve
   
   # Using conda (recommended)
   conda install -c conda-forge ngsolve

Optional: OpenSim
-----------------

OpenSim requires the official installer and conda package:

.. code-block:: bash

   conda install -c opensim-org opensim

See the `OpenSim documentation <https://opensim.stanford.edu/>`_ for details.
