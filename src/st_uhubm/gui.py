"""NiceGUI web front-end for st-uhubm."""
from __future__ import annotations

import asyncio
import os
import shutil
from datetime import datetime

import click
from nicegui import run as ng_run
from nicegui import ui

from .cli_backend import HubManager
from .errors import ManagedHubError

GREY = "opacity-50 pointer-events-none"
_HW_LOCK = asyncio.Lock()
_LOGFILE = None


def open_logfile(directory: str | None = None) -> str:
    """Open the process-wide log file."""
    global _LOGFILE

    if directory is None:
        base = (
            os.environ.get("XDG_STATE_HOME")
            or os.path.expanduser("~/.local/state")
        )
        directory = os.path.join(
            base,
            "stuhubm-gui",
            "logs",
        )

    os.makedirs(directory, exist_ok=True)

    timestamp = datetime.now().strftime(
        "%Y%m%d-%H%M%S"
    )
    path = os.path.join(
        directory,
        f"stuhubm-gui-{timestamp}.log",
    )

    _LOGFILE = open(
        path,
        "a",
        buffering=1,
        encoding="utf-8",
    )

    return path


async def confirm(
    title: str,
    message: str,
) -> bool:
    """Show a confirmation dialog."""
    with ui.dialog() as dialog, ui.card():
        ui.label(title).classes(
            "text-lg font-bold"
        )
        ui.label(message)

        with ui.row().classes(
            "w-full justify-end"
        ):
            ui.button(
                "Cancel",
                on_click=lambda: dialog.submit(False),
            ).props("flat")
            ui.button(
                "Confirm",
                on_click=lambda: dialog.submit(True),
            ).props("color=negative")

    return bool(await dialog)


class Session:
    """Per-browser-client application state."""

    def __init__(self) -> None:
        self.mgr = HubManager(logger=self.log)
        self.hubs = []
        self.busy = False
        self.panel = None
        self.spinner = None
        self.log_widget = None
        self.cards = ui.refreshable(
            self._render_cards
        )

    def log(self, message: str) -> None:
        """Write to the GUI console and log file."""
        line = (
            f"[{datetime.now():%Y-%m-%d %H:%M:%S}] "
            f"{message}"
        )

        if self.log_widget:
            self.log_widget.push(line)

        if _LOGFILE:
            _LOGFILE.write(line + "\n")

    def set_busy(self, busy: bool) -> None:
        """Update the GUI busy state."""
        if self.panel:
            if busy:
                self.panel.classes(add=GREY)
            else:
                self.panel.classes(remove=GREY)

        if self.spinner:
            self.spinner.set_visibility(busy)

    async def action(
        self,
        function=None,
        settle: float = 0.0,
    ) -> bool:
        """Run a backend action and rediscover hubs."""
        if self.busy:
            ui.notify(
                "Busy — wait for the current action "
                "to finish",
                type="warning",
            )
            return False

        self.busy = True
        self.set_busy(True)
        success = True

        try:
            async with _HW_LOCK:
                if function:
                    await ng_run.io_bound(function)

                if settle:
                    await asyncio.sleep(settle)

                self.hubs = (
                    await ng_run.io_bound(
                        self.mgr.discover
                    )
                    or []
                )
        except ManagedHubError as exc:
            success = False
            self.log(f"! {exc}")
            ui.notify(
                str(exc),
                type="negative",
            )
        finally:
            self.busy = False
            self.set_busy(False)
            self.cards.refresh()

        return success

    async def change_password(self, hub) -> None:
        """Show the password-change dialog."""
        with (
            ui.dialog() as dialog,
            ui.card().classes("w-96"),
        ):
            ui.label(
                f"Change password — {hub.port}"
            ).classes("text-lg font-bold")

            old = (
                ui.input(
                    "Old password "
                    "(leave blank if default)"
                )
                .props("type=password")
                .classes("w-full")
            )
            new = (
                ui.input(
                    "New password (max 8 chars)"
                )
                .props(
                    "type=password maxlength=8"
                )
                .classes("w-full")
            )

            with ui.row().classes(
                "w-full justify-end"
            ):
                ui.button(
                    "Cancel",
                    on_click=lambda: dialog.submit(
                        False
                    ),
                ).props("flat")
                ui.button(
                    "Change",
                    on_click=lambda: dialog.submit(
                        True
                    ),
                ).props("color=primary")

        if not (await dialog and new.value):
            return

        if await self.action(
            lambda: hub.change_password(
                old.value,
                new.value,
            )
        ):
            ui.notify(
                f"{hub.port}: password changed",
                type="positive",
            )

    def _toggle(self, hub, port):
        """Create a handler for one port switch."""
        return lambda event: self.action(
            lambda: hub.set_port(
                port,
                bool(event.value),
            )
        )

    def _action_row(self, hub) -> None:
        """Render hub-level action buttons."""

        async def save():
            if await self.action(
                lambda: hub.save()
            ):
                ui.notify(
                    f"{hub.port}: saved to flash",
                    type="positive",
                )

        async def reset():
            accepted = await confirm(
                "Reset hub",
                (
                    f"Hardware-reset {hub.port}? "
                    "Ports drop briefly."
                ),
            )

            if accepted:
                await self.action(
                    hub.reset,
                    settle=2.0,
                )

        async def restore():
            accepted = await confirm(
                "Restore defaults",
                (
                    "Restore factory defaults on "
                    f"{hub.port}? Password resets "
                    "to 'pass' and all ports turn on."
                ),
            )

            if accepted:
                await self.action(
                    hub.restore_defaults,
                    settle=1.0,
                )

        buttons = [
            (
                "All On",
                "positive",
                lambda: self.action(
                    lambda: hub.set_all(True)
                ),
            ),
            (
                "All Off",
                "grey-8",
                lambda: self.action(
                    lambda: hub.set_all(False)
                ),
            ),
            (
                "Save to flash",
                "primary",
                save,
            ),
            (
                "Reset",
                "amber-9",
                reset,
            ),
            (
                "Restore",
                "negative",
                restore,
            ),
            (
                "Change password",
                "primary",
                lambda: self.change_password(hub),
            ),
        ]

        with ui.row().classes("gap-2 mt-2"):
            for label, color, callback in buttons:
                ui.button(
                    label,
                    on_click=callback,
                ).props(f"color={color}")

    def _device_color(self, device) -> str:
        """Return the color for a device type."""
        if device.device_type == "Nordic PPK2":
            return "text-purple"

        return "text-positive"

    def _render_device(self, device) -> None:
        """Render one identified device."""
        ui.label(
            device.product or device.device_type
        ).classes("text-sm font-medium")

        if device.serial:
            serial_prefix = (
                "CDC ID"
                if device.device_type == "Nordic PPK2"
                else "S/N"
            )
            ui.label(
                f"{serial_prefix} {device.serial}"
            ).classes(
                f"text-xs "
                f"{self._device_color(device)}"
            )
        else:
            ui.label(
                "Serial unavailable"
            ).classes("text-xs text-warning")

    def _render_cards(self) -> None:
        """Render hubs, ports, and identified devices."""
        if not self.hubs:
            ui.label(
                "No hubs loaded. Click Discover."
            ).classes("text-grey italic")
            return

        for hub in self.hubs:
            with ui.card().classes("w-full"):
                with ui.row().classes(
                    "w-full items-center "
                    "justify-between"
                ):
                    ui.label(
                        f"Hub {hub.port}"
                    ).classes("text-lg font-bold")

                    description = (
                        f"{hub.model} · sn {hub.serial} · "
                        f"{hub.n_ports} ports · "
                        f"fw {hub.firmware}"
                    )
                    ui.label(
                        description
                    ).classes("text-grey")

                with ui.row().classes(
                    "flex-wrap gap-3 w-full"
                ):
                    for port in range(
                        1,
                        hub.n_ports + 1,
                    ):
                        devices = (
                            hub.identified_devices(port)
                        )

                        with ui.card().classes(
                            "min-w-52 p-3 gap-1"
                        ):
                            ui.switch(
                                f"Port {port}",
                                value=hub.is_on(port),
                                on_change=self._toggle(
                                    hub,
                                    port,
                                ),
                            )

                            if devices:
                                for device in devices:
                                    self._render_device(
                                        device
                                    )
                            elif hub.is_on(port):
                                ui.label(
                                    "No J-Link or PPK2 "
                                    "identified"
                                ).classes(
                                    "text-xs text-grey"
                                )
                            else:
                                ui.label(
                                    "Port off"
                                ).classes(
                                    "text-xs text-grey"
                                )

                self._action_row(hub)

    def build(self) -> None:
        """Build the GUI."""
        with ui.column().classes(
            "w-full max-w-5xl mx-auto p-4 gap-4"
        ):
            ui.label(
                "USB Hub Dashboard"
            ).classes("text-2xl font-bold")

            ui.label(
                "Manage StarTech Industrial USB Hub "
                "and identify connected J-Link and "
                "PPK2 devices"
            ).classes("text-grey")

            with ui.expansion(
                "Settings",
                icon="settings",
            ).classes("w-full"):
                with ui.column().classes(
                    "gap-2 w-full"
                ):
                    (
                        ui.input(
                            "Binary "
                            "(cusbi / cusba / path)"
                        )
                        .bind_value(
                            self.mgr,
                            "binary",
                        )
                        .classes("w-full")
                    )

                    ui.switch(
                        "Use sudo"
                    ).bind_value(
                        self.mgr,
                        "use_sudo",
                    )

                    (
                        ui.input(
                            "Hub password "
                            "(leave blank if default)"
                        )
                        .props("type=password")
                        .bind_value(
                            self.mgr,
                            "password",
                        )
                        .classes("w-full")
                    )

                    ui.switch(
                        "Remember port changes "
                        "after hub power-off"
                    ).bind_value(
                        self.mgr,
                        "persist",
                    )

            with ui.row().classes(
                "items-center gap-2"
            ):
                self.spinner = ui.spinner(size="lg")
                self.spinner.set_visibility(False)
                auto = ui.switch(
                    "Auto-refresh (5s)"
                )

            self.panel = ui.column().classes(
                "w-full gap-4"
            )

            with self.panel:
                ui.button(
                    "Discover",
                    icon="search",
                    on_click=lambda: self.action(),
                ).props("color=primary")
                self.cards()

            ui.label(
                "Console"
            ).classes("text-lg font-bold mt-2")

            self.log_widget = ui.log().classes(
                "w-full h-64 font-mono text-xs "
                "bg-black text-green-400 p-2"
            )

            ui.timer(
                5.0,
                lambda: (
                    self.action()
                    if auto.value and not self.busy
                    else None
                ),
            )

        if not shutil.which(self.mgr.binary):
            self.log(
                f"(note: '{self.mgr.binary}' "
                "not on PATH — set a full path "
                "in Settings)"
            )


@ui.page("/")
def main_page() -> None:
    """Create one session per browser connection."""
    Session().build()


@click.command()
@click.option(
    "--host",
    default="127.0.0.1",
    show_default=True,
)
@click.option(
    "--port",
    default=8080,
    type=int,
    show_default=True,
)
@click.option(
    "--log-dir",
    default=None,
    help=(
        "per-run log directory "
        "(default: "
        "$XDG_STATE_HOME/stuhubm-gui/logs)"
    ),
)
@click.option(
    "--native",
    is_flag=True,
    help=(
        "open as a desktop window "
        "(requires pywebview)"
    ),
)
def run(host, port, log_dir, native) -> None:
    """Run the managed USB hub web GUI."""
    path = open_logfile(log_dir)
    print(f"stuhubm-gui logging to {path}")

    ui.run(
        title="USB Hub Dashboard",
        host=host,
        port=port,
        native=native,
        reload=False,
        show=not native,
    )


if __name__ in {"__main__", "__mp_main__"}:
    run()
