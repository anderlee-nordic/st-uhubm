"""Command-line interface for st-uhubm.

Exit codes:
    * 0: success
    * 1: command failure
    * 2: usage error
    * 3: binary not found
    * 4: timeout
"""
from __future__ import annotations

import json
import os
import shutil

import click

from . import __version__
from .cli_backend import (
    Hub,
    HubManager,
    default_binary,
)
from .errors import (
    BinaryNotFound,
    HubCommandError,
    HubParseError,
    HubTimeout,
    ManagedHubError,
)


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)

    if value is None:
        return default

    return value.strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _ports(token: str):
    """Parse all, one port, or comma-separated ports."""
    if token.strip().lower() == "all":
        return "all"

    try:
        return [
            int(value)
            for value in token.split(",")
            if value.strip()
        ]
    except ValueError:
        raise click.BadParameter(
            f"invalid port list: {token!r}"
        ) from None


def _device_dict(device) -> dict:
    """Convert an identified device to JSON-compatible data."""
    return {
        "serial": device.serial,
        "product": device.product,
        "manufacturer": device.manufacturer,
        "sysfs_name": device.sysfs_name,
        "vendor_id": device.vendor_id,
        "product_id": device.product_id,
        "device_type": device.device_type,
    }


def _hub_dict(hub: Hub) -> dict:
    """Convert a Hub to a JSON-compatible dictionary."""
    identified = {}

    for port in range(1, hub.n_ports + 1):
        devices = hub.identified_devices(port)

        if devices:
            identified[str(port)] = [
                _device_dict(device)
                for device in devices
            ]

    return {
        "port": hub.port,
        "model": hub.model,
        "serial": hub.serial,
        "firmware": hub.firmware,
        "n_ports": hub.n_ports,
        "states": {
            str(port): hub.is_on(port)
            for port in range(
                1,
                hub.n_ports + 1,
            )
        },
        "identified_devices": identified,
    }


def _emit(obj, hub: Hub) -> None:
    """Print a Hub in human-readable or JSON form."""
    if obj.json:
        click.echo(
            json.dumps(
                _hub_dict(hub),
                indent=2,
            )
        )
        return

    click.echo(
        f"{hub.port}  {hub.model}  "
        f"(sn {hub.serial}, "
        f"{hub.n_ports} ports, "
        f"fw {hub.firmware})"
    )

    for port in range(1, hub.n_ports + 1):
        state = "on" if hub.is_on(port) else "off"
        devices = hub.identified_devices(port)

        if devices:
            descriptions = ", ".join(
                device.display_name
                for device in devices
            )
            click.echo(
                f"  {port}:{state}  {descriptions}"
            )
        else:
            click.echo(f"  {port}:{state}")


class HubCLI(click.Group):
    """Map backend exceptions to CLI exit codes."""

    def invoke(self, ctx):
        try:
            return super().invoke(ctx)
        except BinaryNotFound as exc:
            click.echo(
                f"error: {exc}",
                err=True,
            )
            ctx.exit(3)
        except HubTimeout as exc:
            click.echo(
                f"error: {exc}",
                err=True,
            )
            ctx.exit(4)
        except (
            HubCommandError,
            HubParseError,
            ManagedHubError,
        ) as exc:
            click.echo(
                f"error: {exc}",
                err=True,
            )
            ctx.exit(1)


@click.group(
    cls=HubCLI,
    context_settings={
        "help_option_names": ["-h", "--help"],
    },
)
@click.version_option(
    __version__,
    "-V",
    "--version",
    prog_name="stuhubm",
)
@click.option(
    "--binary",
    default=lambda: (
        os.environ.get("STUHUBM_BINARY")
        or default_binary()
    ),
    help=(
        "binary name or path "
        "(default: cusbi on x86, cusba on ARM)"
    ),
)
@click.option(
    "--sudo/--no-sudo",
    default=None,
    help="run the binary via sudo (default: on)",
)
@click.option(
    "--password",
    default=lambda: os.environ.get(
        "STUHUBM_PASSWORD"
    ),
    help="hub password, if changed from the default",
)
@click.option(
    "--persist",
    is_flag=True,
    default=lambda: _env_bool(
        "STUHUBM_PERSIST",
        False,
    ),
    help=(
        "remember port changes after hub power-off"
    ),
)
@click.option(
    "--timeout",
    type=int,
    default=10,
    help="per-command timeout in seconds",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="machine-readable JSON output",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="print the exact binary invocation",
)
@click.pass_context
def main(
    ctx,
    binary,
    sudo,
    password,
    persist,
    timeout,
    as_json,
    verbose,
):
    """Manage StarTech Industrial USB Hubs."""
    manager = HubManager(
        binary=binary,
        use_sudo=(
            _env_bool("STUHUBM_SUDO", True)
            if sudo is None
            else sudo
        ),
        password=password or "",
        persist=persist,
        timeout=timeout,
    )

    if verbose:
        manager.logger = lambda message: click.echo(
            message,
            err=True,
        )

    ctx.obj = type(
        "Ctx",
        (),
        {
            "mgr": manager,
            "json": as_json,
        },
    )()


@main.command()
@click.pass_obj
def health(obj):
    """Check the binary and list detected hubs."""
    located = (
        shutil.which(obj.mgr.binary)
        or (
            obj.mgr.binary
            if os.path.isfile(obj.mgr.binary)
            else None
        )
    )

    if not located:
        click.echo(
            f"binary: NOT FOUND ({obj.mgr.binary})",
            err=True,
        )
        raise SystemExit(3)

    click.echo(f"binary: {located}")
    click.echo(
        f"sudo:   "
        f"{'yes' if obj.mgr.use_sudo else 'no'}"
    )

    hubs = obj.mgr.discover()

    if hubs:
        click.echo(f"hubs:   {len(hubs)} detected")
    else:
        click.echo("hubs:   none detected")

    for hub in hubs:
        click.echo(
            f"  - {hub.port}  {hub.model} "
            f"(sn {hub.serial}, "
            f"{hub.n_ports} ports, "
            f"fw {hub.firmware})"
        )

        for port in range(1, hub.n_ports + 1):
            for device in hub.identified_devices(port):
                click.echo(
                    f"      port {port}: "
                    f"{device.display_name}"
                )


@main.command("list")
@click.pass_obj
def list_(obj):
    """Discover connected hubs."""
    hubs = obj.mgr.discover()

    if obj.json:
        click.echo(
            json.dumps(
                [
                    _hub_dict(hub)
                    for hub in hubs
                ],
                indent=2,
            )
        )
    elif not hubs:
        click.echo("no managed hubs detected")
    else:
        for hub in hubs:
            _emit(obj, hub)


@main.command()
@click.argument("port")
@click.pass_obj
def status(obj, port):
    """Show port states and identified devices."""
    _emit(obj, obj.mgr.hub(port))


@main.command()
@click.argument("port")
@click.argument("ports")
@click.pass_obj
def on(obj, port, ports):
    """Turn the selected ports on."""
    hub = obj.mgr.hub(port)
    selected = _ports(ports)

    if selected == "all":
        hub.set_all(True)
    else:
        hub.set_ports(selected, True)

    _emit(obj, hub.refresh())


@main.command()
@click.argument("port")
@click.argument("ports")
@click.pass_obj
def off(obj, port, ports):
    """Turn the selected ports off."""
    hub = obj.mgr.hub(port)
    selected = _ports(ports)

    if selected == "all":
        hub.set_all(False)
    else:
        hub.set_ports(selected, False)

    _emit(obj, hub.refresh())


@main.command()
@click.argument("port")
@click.argument("ports")
@click.pass_obj
def toggle(obj, port, ports):
    """Invert the selected ports."""
    selected = _ports(ports)

    if selected == "all":
        raise click.BadParameter(
            "'toggle' does not accept 'all'"
        )

    hub = obj.mgr.hub(port)

    for selected_port in selected:
        hub.toggle(selected_port)

    _emit(obj, hub.refresh())


@main.command("all")
@click.argument("port")
@click.argument(
    "state",
    type=click.Choice(["on", "off"]),
)
@click.pass_obj
def all_(obj, port, state):
    """Turn all ports on or off."""
    hub = obj.mgr.hub(port)
    hub.set_all(state == "on")
    _emit(obj, hub.refresh())


@main.command()
@click.argument("port")
@click.pass_obj
def save(obj, port):
    """Save current port states to flash."""
    obj.mgr.hub(port).save()
    click.echo(
        f"{port}: current port states saved to flash"
    )


@main.command()
@click.argument("port")
@click.pass_obj
def reset(obj, port):
    """Hardware-reset the hub."""
    Hub(
        port=port,
        manager=obj.mgr,
    ).reset()
    click.echo(f"{port}: reset requested")


@main.command()
@click.argument("port")
@click.pass_obj
def restore(obj, port):
    """Restore factory defaults."""
    Hub(
        port=port,
        manager=obj.mgr,
    ).restore_defaults()

    click.echo(
        f"{port}: factory defaults restored"
    )


@main.command()
@click.argument("port")
@click.pass_obj
def passwd(obj, port):
    """Change the hub password."""
    old = click.prompt(
        "Old password (blank if default 'pass')",
        default="",
        hide_input=True,
        show_default=False,
    )
    new = click.prompt(
        "New password (max 8 chars)",
        hide_input=True,
        confirmation_prompt=True,
    )

    if not new or len(new) > 8:
        raise click.ClickException(
            "password must be 1-8 characters"
        )

    Hub(
        port=port,
        manager=obj.mgr,
    ).change_password(old, new)

    click.echo(f"{port}: password changed")


if __name__ == "__main__":
    main()
