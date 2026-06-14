"""
st-uhubm: Python wrapper for managing StarTech USB hub

Wraps StarTech's proprietary ``cusbi`` / ``cusba`` binary,
which must be installed separately.

Unofficial. Not affiliated with StarTech.com.
"""
from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("st-uhubm")
except PackageNotFoundError:   # not installed (e.g. running from a raw checkout)
    __version__ = "0.0.0+unknown"

from .cli_backend import Hub, HubManager, discover, parse_hub_info, parse_query_all
from .errors import (
    BinaryNotFound,
    HubCommandError,
    HubParseError,
    HubTimeout,
    ManagedHubError,
)

__version__ = "0.1.0"

__all__ = [
    "Hub",
    "HubManager",
    "discover",
    "parse_hub_info",
    "parse_query_all",
    "ManagedHubError",
    "BinaryNotFound",
    "HubCommandError",
    "HubParseError",
    "HubTimeout",
    "__version__",
]
