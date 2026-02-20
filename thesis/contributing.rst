Contributing
============

Thank you for your interest in contributing to SysSimX!

Development Setup
-----------------

1. Clone the repository:

.. code-block:: bash

   git clone https://github.com/FlorianFrech/SystemSimulation.git
   cd SystemSimulation

2. Create a virtual environment:

.. code-block:: bash

   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   # or
   .venv\Scripts\activate     # Windows

3. Install development dependencies:

.. code-block:: bash

   pip install -e ".[dev]"

4. Install pre-commit hooks:

.. code-block:: bash

   pre-commit install

Running Tests
-------------

.. code-block:: bash

   # Run all tests
   pytest

   # Run with coverage
   pytest --cov=syssimx --cov-report=html

   # Run specific test file
   pytest tests/unit/core/test_base.py

   # Run specific test
   pytest tests/unit/core/test_base.py::TestInitialization::test_basic_init

Code Style
----------

We use the following tools for code quality:

- **Ruff** - Fast Python linter and formatter
- **Black** - Code formatting (via Ruff)
- **isort** - Import sorting (via Ruff)
- **mypy** - Static type checking

Run checks manually:

.. code-block:: bash

   # Format code
   ruff format .

   # Check linting
   ruff check .

   # Type checking
   mypy syssimx

Documentation Style
-------------------

We use **Google-style docstrings**:

.. code-block:: python

   def my_function(param1: float, param2: str = "default") -> bool:
       """Short description of the function.

       Longer description if needed, explaining the purpose and
       behavior in more detail.

       Args:
           param1: Description of param1.
           param2: Description of param2. Defaults to "default".

       Returns:
           Description of return value.

       Raises:
           ValueError: When param1 is negative.
           RuntimeError: When something goes wrong.

       Example:
           >>> result = my_function(1.0, "test")
           >>> print(result)
           True

       Note:
           Additional notes about usage or implementation.

       See Also:
           related_function: Does something related.
       """

Building Documentation
----------------------

.. code-block:: bash

   cd docs
   make html
   open _build/html/index.html  # View locally

Pull Request Process
--------------------

1. Fork the repository
2. Create a feature branch: ``git checkout -b feature/my-feature``
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass: ``pytest``
6. Update documentation if needed
7. Commit with clear messages
8. Push to your fork
9. Create a Pull Request

Commit Messages
^^^^^^^^^^^^^^^

Use conventional commits:

- ``feat: Add new component type``
- ``fix: Correct event detection edge case``
- ``docs: Update quickstart guide``
- ``test: Add integration tests for hybrid algorithm``
- ``refactor: Simplify port state management``

Reporting Issues
----------------

Please include:

1. SysSimX version: ``python -c "import syssimx; print(syssimx.__version__)"``
2. Python version: ``python --version``
3. Operating system
4. Minimal reproducible example
5. Expected vs actual behavior
6. Full error traceback if applicable
