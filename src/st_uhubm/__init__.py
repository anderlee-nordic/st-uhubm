"""Python tools for controlling StarTech Managed Industrial USB Hubs.

The package wraps StarTech's proprietary ``cusbi`` and ``cusba`` programs,
which must be installed separately.

Unofficial. Not affiliated with StarTech.com.
"""
from __future__ import annotations

from importlib.metadata import (
    PackageNotFoundError,
    version,
)

try:
    __version__ = version("st-uhubm")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"

from .cli_backend import (
    Hub,
    HubManager,
    default_binary,
    discover,
    parse_hub_info,
    parse_query_all,
)
from .device import (
    IdentifiedDevice,
    identify_devices,
)
from .errors import (
    BinaryNotFound,
    HubCommandError,
    HubParseError,
    HubTimeout,
    ManagedHubError,
)

__all__ = [
    "BinaryNotFound",
    "Hub",
    "HubCommandError",
    "HubManager",
    "HubParseError",
    "HubTimeout",
    "IdentifiedDevice",
    "ManagedHubError",
    "__version__",
    "default_binary",
    "discover",
    "identify_devices",
    "parse_hub_info",
    "parse_query_all",
]
