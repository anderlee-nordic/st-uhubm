"""Exception hierarchy for st_uhubm."""
from __future__ import annotations


class ManagedHubError(Exception):
    """Base class for all errors raised by this package."""


class BinaryNotFound(ManagedHubError):
    """The StarTech binary (cusbi/cusba) could not be located."""

    def __init__(self, binary: str) -> None:
        super().__init__(
            f"StarTech binary not found: {binary!r} "
            f"(install cusbi/cusba and put it on PATH, or pass --binary)"
        )
        self.binary = binary


class HubCommandError(ManagedHubError):
    """The Startech binary returned a non-zero exit code."""

    def __init__(self, argv: list[str], returncode: int, stderr: str = "") -> None:
        detail = f" ({stderr})" if stderr else ""
        super().__init__(
            f"command failed (exit {returncode}): {' '.join(argv)}{detail}"
        )
        self.argv = argv
        self.returncode = returncode
        self.stderr = stderr


class HubParseError(ManagedHubError):
    """The Startech binary's output could not be parsed."""


class HubTimeout(ManagedHubError):
    """A command exceeded the configured timeout."""
