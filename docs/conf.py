"""Sphinx configuration for st-uhubm documentation."""
from importlib.metadata import (
    PackageNotFoundError,
    version as package_version,
)

project = "st-uhubm"
author = "Ander Lee"
copyright = "2026, Ander Lee"

try:
    release = package_version("st-uhubm")
except PackageNotFoundError:
    release = "0.0.0+unknown"

version = ".".join(release.split(".")[:2])

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

templates_path = ["_templates"]

exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
    "USER_MANUAL.md",
]

html_theme = "sphinx_rtd_theme"
html_static_path = []

linkcheck_ignore = [r"#.*"]
