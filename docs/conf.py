# Configuration file for the Sphinx documentation builder.
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys
import warnings

from sphinx.deprecation import RemovedInSphinx10Warning

# Add the project root to the path so autodoc can find the modules
sys.path.insert(0, os.path.abspath(".."))

from syssimx.__version__ import __version__ as _pkg_version  # noqa: E402

# -- Project information -----------------------------------------------------
project = "SysSimX"
copyright = "2026, Florian Frech"
author = "Florian Frech"
version = ".".join(_pkg_version.split(".")[:2])  # e.g. "0.1"
release = _pkg_version  # e.g. "0.1.4"

# -- General configuration ---------------------------------------------------
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",  # Support for NumPy and Google style docstrings
    "sphinx.ext.viewcode",  # Add links to source code
    "sphinx.ext.intersphinx",  # Link to other projects' documentation
    'sphinx.ext.mathjax',  # Render math in docs
    
    # Add these explicitly:
    "myst_nb",
]

# Ensure Sphinx knows which source types you use
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
    ".ipynb": "myst-nb",
}

# Enable MyST math features
myst_enable_extensions = [
    "dollarmath",  # enables $...$ and $$...$$
    "amsmath",     # enables \begin{align}...\end{align} style environments
    "colon_fence", # generally useful for fenced directives in Markdown
    "deflist",     # enables definition lists
]

# Optional: allow $$...$$ inside text without extra blank lines
myst_dmath_double_inline = True  # optional, only if you need it

# Autodoc settings
autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "private-members": True,
    "show-inheritance": True,
    "member-order": "bysource",
}
autodoc_typehints = "description"
autodoc_class_signature = "separated"
autodoc_mock_imports = ["fmpy", "ngsolve", "netgen", "opensim", "OMPython"]

# Suppress ambiguous cross-reference warnings for re-exported classes
suppress_warnings = ["ref.python", "myst.header"]

# Silence MyST-NB deprecation warnings until upstream updates their parser API.
warnings.filterwarnings(
    "ignore",
    category=RemovedInSphinx10Warning,
    module=r"myst_nb\.sphinx_",
)

# Napoleon settings (for NumPy/Google docstrings)
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = True

# Autosummary
autosummary_generate = True

# Notebook settings
nb_execution_mode = "off"  # Do not execute notebooks during build else use "auto" or "force"

# Intersphinx mapping
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "scipy": ("https://docs.scipy.org/doc/scipy/", None),
}

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- Options for HTML output -------------------------------------------------
html_theme = "sphinx_book_theme"
html_static_path = ["_static"]

# Theme options
html_theme_options = {
    "repository_url": "https://github.com/FlorianFrech/SystemSimulation",
    "use_repository_button": True,
    "use_issues_button": True,
}
