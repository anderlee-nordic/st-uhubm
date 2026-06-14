"""Backend for communicating to StarTech Industrial USB Hubs via cusbi / cusba.

* Pure parsers (:func:`parse_query_all`, :func:`parse_hub_info`) with no I/O.
* :class:`HubManager` (configuration + subprocess invocation).
* :class:`Hub` (one device, with methods mirroring the high-level operations).

No external dependency required
"""
from __future__ import annotations

import glob
import os
import subprocess
from dataclasses import dataclass, field
from typing import Callable, Optional

from .errors import BinaryNotFound, HubCommandError, HubParseError, HubTimeout

__all__ = [
    "parse_query_all",
    "parse_hub_info",
    "Hub",
    "HubManager",
    "discover",
]


def parse_query_all(raw: str) -> list[str]:
    """Parse ``cusbi /Q -F`` output into a list of control ports (firmware v04+).

    The record is the 4-digit hub count, a comma, then the full device paths::

        "0001,/dev/ttyUSB0"               -> ["/dev/ttyUSB0"]
        "0002,/dev/ttyUSB0,/dev/ttyUSB1"  -> ["/dev/ttyUSB0", "/dev/ttyUSB1"]

    Returns an empty list if the input is empty or malformed; discovery falls
    back to device enumeration in that case rather than raising.
    """
    raw = raw.strip()
    if len(raw) < 4 or not raw[:4].isdigit() or int(raw[:4]) == 0:
        return []
    rest = raw[4:]
    if not rest.startswith(","):
        return []
    return [p for p in rest[1:].split(",") if p]


def parse_hub_info(raw: str) -> tuple[int, dict[int, bool], str, str, str]:
    """Parse ``cusbi /Q:<port> -F`` output (firmware v04+).

    The comma-delimited record is::

        "FBFFFFFF,7,v04,00020000149E,7-port Managed USB Hub"
        # bitmap(hex), port count(dec), firmware, serial, model

    Returns ``(n_ports, states, firmware, serial, model)``. The port-state
    bitmap is 32 bits, little-endian by byte; bit ``n-1`` corresponds to port
    ``n`` (``1`` = on).

    Raises :class:`HubParseError` on malformed input.
    """
    raw = raw.strip()
    fields = raw.split(",")
    try:
        n_ports = int(fields[1])
        value = int.from_bytes(bytes.fromhex(fields[0]), "little")
    except (ValueError, IndexError) as exc:
        raise HubParseError(f"could not parse hub info: {raw!r}") from exc
    firmware = fields[2].strip() if len(fields) > 2 and fields[2].strip() else "?"
    serial = fields[3].strip() if len(fields) > 3 and fields[3].strip() else "?"
    model = ",".join(fields[4:]).strip() or "?" # handle comma inside the model name
    states = {p: bool(value & (1 << (p - 1))) for p in range(1, n_ports + 1)}
    return n_ports, states, firmware, serial, model


@dataclass
class Hub:
    """A single managed USB hub, addressed by its serial control port.

    A ``Hub`` is normally obtained from :meth:`HubManager.discover` or
    :meth:`HubManager.hub` rather than built directly, so it arrives attached to
    a :class:`HubManager` that runs the binary on its behalf. The query and
    mutation methods go through that manager and keep :attr:`states` in sync, so
    reading :attr:`states` (or :meth:`is_on`) right after a call reflects the
    change with no extra round-trip. Call :meth:`refresh` to re-read the live
    state from hardware.

    Attributes:
        port: Control-port path the hub is addressed by, e.g. ``"/dev/ttyUSB0"``.
        n_ports: Number of switchable downstream ports.
        states: Map of 1-based port number to ``True`` (on) / ``False`` (off).
        firmware: Firmware revision reported by the hub, e.g. ``"v04"``.
        serial: Hub serial number, or ``"?"`` if the hub did not report one.
        model: Human-readable model string, or ``"?"`` if unknown.
        manager: :class:`HubManager` used to run commands; ``None`` until attached.

    Example:
        Read a hub and switch one port off (cached state updates in place)::

            mgr = HubManager(use_sudo=False)
            hub = mgr.hub("/dev/ttyUSB0")
            hub.set_port(3, False)
            assert hub.is_on(3) is False
    """


    port: str
    n_ports: int = 0
    states: dict[int, bool] = field(default_factory=dict)
    firmware: str = "?"
    serial: str = "?"
    model: str = "?"
    manager: "Optional[HubManager]" = None

    # helpers
    # ----------------------------------------------------------- #
    @property
    def _mgr(self) -> "HubManager":
        if self.manager is None:
            raise ManagedHubAttachmentError()
        return self.manager

    def _pw(self) -> list[str]:
        pw = self._mgr.password
        return [pw] if pw else []

    def _set_letter(self, persist: Optional[bool]) -> str:
        use_flash = self._mgr.persist if persist is None else persist
        return "F" if use_flash else "S"

    # queries
    # ----------------------------------------------------------- #
    def is_on(self, n: int) -> bool:
        """Return whether port ``n`` is currently on, per cached state."""
        return self.states.get(n, False)

    def refresh(self) -> "Hub":
        """Re-read live port states from the hub."""
        n, states, fw, serial, model = parse_hub_info(self._mgr._run(f"/Q:{self.port}", "-F"))
        self.n_ports, self.states, self.firmware = n, dict(states), fw
        self.serial, self.model = serial, model
        return self

    # switching/setting
    # ----------------------------------------------------------- #
    def set_ports(self, ports: list[int], on: bool, persist: Optional[bool] = None) -> None:
        """Turn a list of ports on or off in a single command."""
        arg = f"{1 if on else 0}:" + ",".join(str(p) for p in ports)
        self._mgr._run(f"/{self._set_letter(persist)}:{self.port}", *self._pw(), arg)
        for p in ports:
            self.states[p] = on

    def set_port(self, n: int, on: bool, persist: Optional[bool] = None) -> None:
        """Turn a single port on or off (convenience wrapper for one port)."""
        self.set_ports([n], on, persist=persist)

    def set_all(self, on: bool, persist: Optional[bool] = None) -> None:
        """Turn every port on or off in one command."""
        self._mgr._run(
            f"/{self._set_letter(persist)}:{self.port}", *self._pw(), f"{1 if on else 0}:ALL"
        )
        self.states = {p: on for p in range(1, self.n_ports + 1)}

    def toggle(self, n: int, persist: Optional[bool] = None) -> None:
        """Invert port ``n`` and update its cached state."""
        self._mgr._run(f"/{self._set_letter(persist)}:{self.port}", *self._pw(), f"T:{n}")
        if n in self.states:
            self.states[n] = not self.states[n]

    def save(self) -> None:
        """Save current port states to flash as the power-on default (``/W``)."""
        self._mgr._run(f"/W:{self.port}", *self._pw())

    def reset(self) -> None:
        """Hardware-reset the hub (``/R``)."""
        self._mgr._run(f"/R:{self.port}", *self._pw())

    def restore_defaults(self) -> None:
        """Restore factory defaults: all ports on, password ``pass`` (``/D``)."""
        self._mgr._run(f"/D:{self.port}", *self._pw())
        self.states = {p: True for p in range(1, self.n_ports + 1)}

    def change_password(self, old: str, new: str) -> None:
        """Change the hub password (``/P``). Updates the manager's password."""
        args = [f"/P:{self.port}"]
        if old:
            args.append(old)
        args.append(new)
        self._mgr._run(*args)
        self._mgr.password = new


class ManagedHubAttachmentError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("Hub is not attached to a HubManager")


@dataclass
class HubManager:
    """Configuration and command execution for one or more managed hubs.

    A ``HubManager`` holds *how* to invoke StarTech's ``cusbi`` / ``cusba``
    binary — path, ``sudo``, password, persistence, timeout — and turns its
    output into :class:`Hub` objects. It is the single entry point to the
    hardware: :meth:`discover` enumerates connected hubs and :meth:`hub` returns
    one known hub with its state populated. Every :class:`Hub` it produces is
    attached back to this manager, so the hub's own methods reuse this config.

    Attributes:
        binary: Binary name or path (``"cusbi"`` on x86/AMD64, ``"cusba"`` on ARM).
        use_sudo: Run the binary via ``sudo`` (needed to open the tty unless a
            udev rule grants access).
        password: Hub password; sent with mutating commands when non-empty.
        persist: When ``True``, writes go straight to flash (``/F``) instead of
            the volatile ``/S`` form.
        timeout: Per-command timeout in seconds.
        logger: Optional callable invoked with the exact argv and the binary's
            output; used by the CLI ``--verbose`` flag and the GUI console.

    Example:
        Discover hubs and turn every port on::

            mgr = HubManager(binary="cusbi", use_sudo=True)
            for hub in mgr.discover():
                hub.set_all(True)
    """

    binary: str = "cusbi"
    use_sudo: bool = True
    password: str = ""
    persist: bool = False
    timeout: int = 10
    logger: Optional[Callable[[str], None]] = None

    def _run(self, *args: str, timeout: Optional[int] = None) -> str:
        argv: list[str] = (["sudo"] if self.use_sudo else []) + [self.binary, *args]
        if self.logger:
            self.logger("$ " + " ".join(argv))
        try:
            proc = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                timeout=timeout or self.timeout,
            )
        except FileNotFoundError as exc:
            raise BinaryNotFound(self.binary) from exc
        except subprocess.TimeoutExpired as exc:
            raise HubTimeout(f"command timed out after {timeout or self.timeout}s") from exc

        if self.logger:
            if proc.stdout.strip():
                self.logger(proc.stdout.strip())
            if proc.stderr.strip():
                self.logger("[stderr] " + proc.stderr.strip())

        if proc.returncode != 0:
            raise HubCommandError(argv, proc.returncode, proc.stderr.strip())
        return proc.stdout

    def discover(self) -> list[Hub]:
        """Find connected managed hubs and read their current state."""
        ports: list[str] = []
        try:
            ports = parse_query_all(self._run("/Q", "-F"))
        except HubCommandError:
            ports = []
        if not ports:  # fall back to raw device enumeration
            ports = [os.path.basename(p) for p in sorted(glob.glob("/dev/ttyUSB*"))]

        hubs: list[Hub] = []
        for port in ports:
            try:
                n, states, fw, serial, model = parse_hub_info(self._run(f"/Q:{port}", "-F"))
            except (HubCommandError, HubParseError):
                continue
            hubs.append(Hub(port=port, n_ports=n, states=dict(states), firmware=fw,
                            serial=serial, model=model, manager=self))
        return hubs

    def hub(self, port: str) -> Hub:
        """Return a :class:`Hub` for a known control port, reading its state."""
        return Hub(port=port, manager=self).refresh()


def discover(**kwargs) -> list[Hub]:
    """Build a :class:`HubManager` from ``kwargs`` and discover hubs."""
    return HubManager(**kwargs).discover()
