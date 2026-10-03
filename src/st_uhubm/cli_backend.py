"""Backend for communicating with StarTech Industrial USB Hubs.

* Pure parsers with no I/O.
* HubManager for configuration and command execution.
* Hub for high-level hub operations.
* Optional device identification through Linux sysfs.

No external dependency is required.
"""
from __future__ import annotations

import glob
import os
import platform
import subprocess
from dataclasses import dataclass, field
from typing import Callable, Optional

from .device import IdentifiedDevice, identify_devices
from .errors import (
    BinaryNotFound,
    HubCommandError,
    HubParseError,
    HubTimeout,
)

__all__ = [
    "default_binary",
    "parse_query_all",
    "parse_hub_info",
    "IdentifiedDevice",
    "identify_devices",
    "Hub",
    "HubManager",
    "discover",
]


def default_binary(machine: str | None = None) -> str:
    """Return the StarTech binary appropriate for the host architecture.

    ARM systems use ``cusba``; x86 systems use ``cusbi``.

    Args:
        machine: Optional machine type. If omitted,
            :func:`platform.machine` is used.
    """
    architecture = (
        machine or platform.machine()
    ).strip().lower()

    if (
        architecture in {"aarch64", "arm64"}
        or architecture.startswith("arm")
    ):
        return "cusba"

    return "cusbi"


def parse_query_all(raw: str) -> list[str]:
    """Parse hub-discovery output into a list of control ports."""
    raw = raw.strip()

    if (
        len(raw) < 4
        or not raw[:4].isdigit()
        or int(raw[:4]) == 0
    ):
        return []

    rest = raw[4:]

    if not rest.startswith(","):
        return []

    return [
        port
        for port in rest[1:].split(",")
        if port
    ]


def parse_hub_info(
    raw: str,
) -> tuple[int, dict[int, bool], str, str, str]:
    """Parse output from a hub information query.

    Supports both formats:
    - Comma-separated (x86 cusbi): FFFFFFFF,7,v04,<serial>,<model>
    - Compact (ARM cusba): FFFFFFFF07v04

    Returns:
        ``(n_ports, states, firmware, serial, model)``.

    Raises:
        HubParseError: If the output cannot be parsed.
    """
    raw = raw.strip()

    # Detect compact format (ARM cusba): no commas
    if "," not in raw:
        try:
            # Compact format: 8-char hex + 2-char decimal + firmware
            hex_states = raw[:8]
            n_ports = int(raw[8:10])
            firmware = raw[10:].strip() or "?"

            value = int.from_bytes(
                bytes.fromhex(hex_states),
                "little",
            )
            states = {
                port: bool(value & (1 << (port - 1)))
                for port in range(1, n_ports + 1)
            }

            return n_ports, states, firmware, "?", "?"
        except (ValueError, IndexError) as exc:
            raise HubParseError(
                f"could not parse hub info: {raw!r}"
            ) from exc

    # Comma-separated format (x86 cusbi)
    fields = raw.split(",")

    try:
        n_ports = int(fields[1])
        value = int.from_bytes(
            bytes.fromhex(fields[0]),
            "little",
        )
    except (ValueError, IndexError) as exc:
        raise HubParseError(
            f"could not parse hub info: {raw!r}"
        ) from exc

    firmware = (
        fields[2].strip()
        if len(fields) > 2 and fields[2].strip()
        else "?"
    )
    serial = (
        fields[3].strip()
        if len(fields) > 3 and fields[3].strip()
        else "?"
    )
    model = ",".join(fields[4:]).strip() or "?"

    states = {
        port: bool(value & (1 << (port - 1)))
        for port in range(1, n_ports + 1)
    }

    return n_ports, states, firmware, serial, model


@dataclass
class Hub:
    """A managed USB hub addressed by its serial control port."""

    port: str
    n_ports: int = 0
    states: dict[int, bool] = field(
        default_factory=dict
    )
    firmware: str = "?"
    serial: str = "?"
    model: str = "?"
    manager: "Optional[HubManager]" = None
    _identified_devices: dict[
        int,
        list[IdentifiedDevice],
    ] = field(
        default_factory=dict,
        init=False,
        repr=False,
    )

    @property
    def _mgr(self) -> "HubManager":
        if self.manager is None:
            raise ManagedHubAttachmentError()

        return self.manager

    def _pw(self) -> list[str]:
        password = self._mgr.password
        return [password] if password else []

    def _set_letter(
        self,
        persist: Optional[bool],
    ) -> str:
        use_flash = (
            self._mgr.persist
            if persist is None
            else persist
        )
        return "F" if use_flash else "S"

    def is_on(self, port: int) -> bool:
        """Return whether a port is on according to cached state."""
        return self.states.get(port, False)

    def identified_devices(
        self,
        port: int,
    ) -> list[IdentifiedDevice]:
        """Return identified devices connected to a managed port."""
        return list(
            self._identified_devices.get(port, [])
        )

    def refresh_device_identification(self) -> None:
        """Refresh device identification using Linux sysfs."""
        self._identified_devices = identify_devices(
            self.port,
            self.n_ports,
        )

    def refresh(self) -> "Hub":
        """Refresh hub state and attached-device identification."""
        raw = self._mgr._run(
            f"/Q:{self.port}",
            "-F",
        )
        (
            n_ports,
            states,
            firmware,
            serial,
            model,
        ) = parse_hub_info(raw)

        self.n_ports = n_ports
        self.states = dict(states)
        self.firmware = firmware
        self.serial = serial
        self.model = model
        self.refresh_device_identification()

        return self

    def set_ports(
        self,
        ports: list[int],
        on: bool,
        persist: Optional[bool] = None,
    ) -> None:
        """Turn one or more ports on or off."""
        argument = (
            f"{1 if on else 0}:"
            + ",".join(
                str(port)
                for port in ports
            )
        )

        self._mgr._run(
            f"/{self._set_letter(persist)}:{self.port}",
            *self._pw(),
            argument,
        )

        for port in ports:
            self.states[port] = on

    def set_port(
        self,
        port: int,
        on: bool,
        persist: Optional[bool] = None,
    ) -> None:
        """Turn one port on or off."""
        self.set_ports(
            [port],
            on,
            persist=persist,
        )

    def set_all(
        self,
        on: bool,
        persist: Optional[bool] = None,
    ) -> None:
        """Turn every managed port on or off."""
        self._mgr._run(
            f"/{self._set_letter(persist)}:{self.port}",
            *self._pw(),
            f"{1 if on else 0}:ALL",
        )

        self.states = {
            port: on
            for port in range(
                1,
                self.n_ports + 1,
            )
        }

    def toggle(
        self,
        port: int,
        persist: Optional[bool] = None,
    ) -> None:
        """Invert one port and update its cached state."""
        self._mgr._run(
            f"/{self._set_letter(persist)}:{self.port}",
            *self._pw(),
            f"T:{port}",
        )

        if port in self.states:
            self.states[port] = not self.states[port]

    def save(self) -> None:
        """Save current port states to flash."""
        self._mgr._run(
            f"/W:{self.port}",
            *self._pw(),
        )

    def reset(self) -> None:
        """Hardware-reset the hub."""
        self._mgr._run(
            f"/R:{self.port}",
            *self._pw(),
        )

    def restore_defaults(self) -> None:
        """Restore the hub's factory defaults."""
        self._mgr._run(
            f"/D:{self.port}",
            *self._pw(),
        )

        self.states = {
            port: True
            for port in range(
                1,
                self.n_ports + 1,
            )
        }

    def change_password(
        self,
        old: str,
        new: str,
    ) -> None:
        """Change the hub password."""
        arguments = [f"/P:{self.port}"]

        if old:
            arguments.append(old)

        arguments.append(new)
        self._mgr._run(*arguments)
        self._mgr.password = new


class ManagedHubAttachmentError(RuntimeError):
    """Raised when a Hub is not attached to a HubManager."""

    def __init__(self) -> None:
        super().__init__(
            "Hub is not attached to a HubManager"
        )


@dataclass
class HubManager:
    """Configuration and command execution for managed USB hubs."""

    binary: str = field(
        default_factory=default_binary
    )
    use_sudo: bool = True
    password: str = ""
    persist: bool = False
    timeout: int = 10
    logger: Optional[Callable[[str], None]] = None

    def _run(
        self,
        *args: str,
        timeout: Optional[int] = None,
    ) -> str:
        argv: list[str] = (
            (["sudo"] if self.use_sudo else [])
            + [self.binary, *args]
        )

        if self.logger:
            self.logger("$ " + " ".join(argv))

        try:
            process = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                timeout=timeout or self.timeout,
            )
        except FileNotFoundError as exc:
            raise BinaryNotFound(
                self.binary
            ) from exc
        except subprocess.TimeoutExpired as exc:
            seconds = timeout or self.timeout
            raise HubTimeout(
                f"command timed out after {seconds}s"
            ) from exc

        if self.logger:
            if process.stdout.strip():
                self.logger(process.stdout.strip())

            if process.stderr.strip():
                self.logger(
                    "[stderr] "
                    + process.stderr.strip()
                )

        if process.returncode != 0:
            raise HubCommandError(
                argv,
                process.returncode,
                process.stderr.strip(),
            )

        return process.stdout

    def discover(self) -> list[Hub]:
        """Find managed hubs and read their current state."""
        ports: list[str] = []

        try:
            ports = parse_query_all(
                self._run("/Q", "-F")
            )
        except HubCommandError:
            ports = []

        if not ports:
            ports = [
                os.path.basename(path)
                for path in sorted(
                    glob.glob("/dev/ttyUSB*")
                )
            ]

        hubs: list[Hub] = []

        for port in ports:
            try:
                raw = self._run(
                    f"/Q:{port}",
                    "-F",
                )
                (
                    n_ports,
                    states,
                    firmware,
                    serial,
                    model,
                ) = parse_hub_info(raw)
            except (
                HubCommandError,
                HubParseError,
            ):
                continue

            hub = Hub(
                port=port,
                n_ports=n_ports,
                states=dict(states),
                firmware=firmware,
                serial=serial,
                model=model,
                manager=self,
            )
            hub.refresh_device_identification()
            hubs.append(hub)

        return hubs

    def hub(self, port: str) -> Hub:
        """Return a populated Hub for a known control port."""
        return Hub(
            port=port,
            manager=self,
        ).refresh()


def discover(**kwargs) -> list[Hub]:
    """Build a HubManager and discover connected hubs."""
    return HubManager(**kwargs).discover()
