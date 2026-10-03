"""Identify supported USB devices through Linux sysfs."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

SEGGER_VENDOR_ID = "1366"
NORDIC_VENDOR_ID = "1915"
PPK2_PRODUCT_ID = "c00a"
STARTECH_VENDOR_ID = "14b0"

SYS_TTY_ROOT = Path("/sys/class/tty")
SYS_USB_ROOT = Path("/sys/bus/usb/devices")


@dataclass(frozen=True)
class IdentifiedDevice:
    """A supported USB device identified on a managed hub port."""

    serial: str
    product: str
    manufacturer: str
    sysfs_name: str = ""
    vendor_id: str = ""
    product_id: str = ""
    device_type: str = "USB device"

    @property
    def display_name(self) -> str:
        """Return a human-readable product and serial description."""
        name = self.product or self.device_type

        if not self.serial:
            return name

        serial_prefix = (
            "CDC ID"
            if self.device_type == "Nordic PPK2"
            else "S/N"
        )
        return f"{name} — {serial_prefix} {self.serial}"


def _read(path: Path, default: str = "") -> str:
    """Read and trim a sysfs attribute, returning default on failure."""
    try:
        return path.read_text(errors="replace").strip()
    except (OSError, UnicodeError):
        return default


def _normalize_serial(serial: str, device_type: str) -> str:
    """Normalize a USB serial number for display."""
    serial = serial.strip()

    if device_type == "SEGGER J-Link" and serial.isdigit():
        return serial.lstrip("0") or "0"

    return serial


def _is_usb_device(path: Path) -> bool:
    """Return whether a sysfs path represents a USB device."""
    return (
        (path / "idVendor").is_file()
        and (path / "idProduct").is_file()
    )


def _is_usb_hub(path: Path) -> bool:
    """Return whether a sysfs USB device is a hub."""
    if not _is_usb_device(path):
        return False

    try:
        return int(_read(path / "maxchild", "0")) > 0
    except ValueError:
        return False


def _usb_device_from_tty(control_port: str) -> Path | None:
    """Find the USB device that owns a tty control port."""
    tty_name = os.path.basename(control_port)
    tty_device = SYS_TTY_ROOT / tty_name / "device"

    try:
        current = tty_device.resolve(strict=True)
    except OSError:
        return None

    for candidate in (current, *current.parents):
        if _is_usb_device(candidate):
            return candidate

    return None


def _managed_hub_root(control_device: Path) -> Path | None:
    """Find the outermost StarTech hub for a control interface.

    The seven-port model contains two cascaded four-port hub chips. Its control
    interface is connected to the inner hub, so the outermost StarTech ancestor
    is used as the topology root.
    """
    startech_hubs: list[Path] = []

    for candidate in (control_device, *control_device.parents):
        if not _is_usb_hub(candidate):
            continue

        if _read(candidate / "idVendor").lower() == STARTECH_VENDOR_ID:
            startech_hubs.append(candidate)

    if not startech_hubs:
        return None

    return startech_hubs[-1]


def _usb_route(hub: Path, device: Path) -> list[int]:
    """Return the USB route from the managed hub to a child device.

    For example, relative to hub ``1-13``:

    * ``1-13.2`` returns ``[2]``
    * ``1-13.4.1`` returns ``[4, 1]``
    * ``1-13.4.3`` returns ``[4, 3]``
    """
    try:
        hub_name = hub.resolve().name
        device_name = device.resolve().name.split(":", 1)[0]
    except OSError:
        return []

    prefix = f"{hub_name}."

    if not device_name.startswith(prefix):
        return []

    route_text = device_name[len(prefix):]

    try:
        return [
            int(component)
            for component in route_text.split(".")
        ]
    except ValueError:
        return []


def _managed_port(hub: Path, device: Path) -> int | None:
    """Translate a Linux USB route into a managed hub port.

    The confirmed topology for the StarTech seven-port model is:

    * outer hub port 1 -> managed port 1
    * outer hub port 2 -> managed port 2
    * outer hub port 3 -> managed port 3
    * outer hub port 4 -> internal cascaded hub
    * inner hub port 1 -> managed port 4
    * inner hub port 2 -> managed port 5
    * inner hub port 3 -> managed port 6
    * inner hub port 4 -> hub control interface
    """
    route = _usb_route(hub, device)

    if not route:
        return None

    if len(route) == 1:
        return route[0]

    if route[0] == 4 and 1 <= route[1] <= 3:
        return 3 + route[1]

    return None


def _is_descendant(parent: Path, child: Path) -> bool:
    """Return whether child is located below parent in sysfs."""
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except (OSError, ValueError):
        return False


def _supported_device_type(
    vendor_id: str,
    product_id: str,
) -> str | None:
    """Return the supported device type for a USB VID/PID pair."""
    vendor_id = vendor_id.lower()
    product_id = product_id.lower()

    if vendor_id == SEGGER_VENDOR_ID:
        return "SEGGER J-Link"

    if (
        vendor_id == NORDIC_VENDOR_ID
        and product_id == PPK2_PRODUCT_ID
    ):
        return "Nordic PPK2"

    return None


def identify_devices(
    control_port: str,
    n_ports: int | None = None,
) -> dict[int, list[IdentifiedDevice]]:
    """Identify supported devices below a managed StarTech hub.

    Currently supported:

    * SEGGER J-Link devices with USB vendor ID ``1366``
    * Nordic PPK2 devices with USB ID ``1915:c00a``

    Args:
        control_port: Hub control tty, such as ``/dev/ttyUSB0``.
        n_ports: Optional maximum managed port number.

    Returns:
        Identified devices indexed by managed hub port. Missing or
        inaccessible sysfs information produces an empty mapping.
    """
    control_device = _usb_device_from_tty(control_port)

    if control_device is None:
        return {}

    hub = _managed_hub_root(control_device)

    if hub is None or not SYS_USB_ROOT.is_dir():
        return {}

    try:
        entries = list(SYS_USB_ROOT.iterdir())
    except OSError:
        return {}

    result: dict[int, list[IdentifiedDevice]] = {}

    for entry in entries:
        if ":" in entry.name:
            continue

        vendor_id = _read(entry / "idVendor").lower()
        product_id = _read(entry / "idProduct").lower()
        device_type = _supported_device_type(
            vendor_id,
            product_id,
        )

        if device_type is None:
            continue

        try:
            device_path = entry.resolve(strict=True)
        except OSError:
            continue

        if not _is_descendant(hub, device_path):
            continue

        port = _managed_port(hub, device_path)

        if port is None or port < 1:
            continue

        if n_ports is not None and port > n_ports:
            continue

        if device_type == "Nordic PPK2":
            default_product = "PPK2"
            default_manufacturer = "Nordic Semiconductor"
        else:
            default_product = "J-Link"
            default_manufacturer = "SEGGER"

        identified_device = IdentifiedDevice(
            serial=_normalize_serial(
                _read(entry / "serial"),
                device_type,
            ),
            product=_read(
                entry / "product",
                default_product,
            ),
            manufacturer=_read(
                entry / "manufacturer",
                default_manufacturer,
            ),
            sysfs_name=entry.name,
            vendor_id=vendor_id,
            product_id=product_id,
            device_type=device_type,
        )

        result.setdefault(port, []).append(
            identified_device
        )

    for devices in result.values():
        devices.sort(
            key=lambda device: (
                device.device_type,
                device.serial,
                device.product,
                device.sysfs_name,
            )
        )

    return result
