"""Sphinx configuration for st-uhubm documentation."""
from importlib.metadata import PackageNotFoundError, version as _pkg_version

project = "st-uhubm"
author = "Your Name"
copyright = "2026, Your Name"

try:
    release = _pkg_version("st-uhubm")
except PackageNotFoundError:          # not installed (e.g. local checkout)
    release = "0.1.0"
version = ".".join(release.split(".")[:2])

extensions = [
    "sphinx.ext.autodoc",       # API docs from docstrings (optional, future use)
    "sphinx.ext.napoleon",      # Google/NumPy-style docstrings
    "sphinx.ext.viewcode",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "USER_MANUAL.md"]

html_theme = "sphinx_rtd_theme"
html_static_path = []           # none yet; avoids a build warning

# Don't fail the build on the manual's same-page (#anchor) links.
linkcheck_ignore = [r"#.*"]
