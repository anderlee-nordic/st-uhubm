"""Command-line interface: the ``stuhubm`` console script.

Commands map onto the StarTech binary; use --verbose to see the exact invocation.

Exit codes:
    * 0 ok
    * 1 command failed
    * 2 usage error
    * 3 binary not found
    * 4 timeout.
"""
from __future__ import annotations

import json
import os
import shutil

import click

from . import __version__
from .cli_backend import Hub, HubManager
from .errors import (
    BinaryNotFound,
    HubCommandError,
    HubParseError,
    HubTimeout,
    ManagedHubError,
)


def _env_bool(name: str, default: bool) -> bool:
    val = os.environ.get(name)
    return default if val is None else val.strip().lower() in ("1", "true", "yes", "on")


def _ports(token: str):
    """Parse a PORTS argument: 'all', a single port, or a comma list."""
    if token.strip().lower() == "all":
        return "all"
    try:
        return [int(x) for x in token.split(",") if x.strip()]
    except ValueError:
        raise click.BadParameter(f"invalid port list: {token!r}")


def _hub_dict(hub: Hub) -> dict:
    return {
        "port": hub.port,
        "model": hub.model,
        "serial": hub.serial,
        "firmware": hub.firmware,
        "n_ports": hub.n_ports,
        "states": {str(p): hub.is_on(p) for p in range(1, hub.n_ports + 1)},
    }


def _emit(obj, hub: Hub) -> None:
    if obj.json:
        click.echo(json.dumps(_hub_dict(hub), indent=2))
    else:
        cells = "  ".join(f"{p}:{'on' if hub.is_on(p) else 'off'}" for p in range(1, hub.n_ports + 1))
        click.echo(f"{hub.port}  {hub.model}  (sn {hub.serial}, "
                   f"{hub.n_ports} ports, fw {hub.firmware})\n  {cells}")


class HubCLI(click.Group):
    """Group that maps backend exceptions to the  exit codes."""

    def invoke(self, ctx):
        try:
            return super().invoke(ctx)
        except BinaryNotFound as exc:
            click.echo(f"error: {exc}", err=True); ctx.exit(3)
        except HubTimeout as exc:
            click.echo(f"error: {exc}", err=True); ctx.exit(4)
        except (HubCommandError, HubParseError, ManagedHubError) as exc:
            click.echo(f"error: {exc}", err=True); ctx.exit(1)


@click.group(cls=HubCLI, context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, "-V", "--version", prog_name="stuhubm")
@click.option("--binary", default=lambda: os.environ.get("STUHUBM_BINARY", "cusbi"),
              help="set binary name or path (cusbi for x86, cusba for ARM)")
@click.option("--sudo/--no-sudo", default=None, help="run the binary via sudo (default: on)")
@click.option("--password", default=lambda: os.environ.get("STUHUBM_PASSWORD"),
              help="hub password, if changed from the default")
@click.option("--persist", is_flag=True, default=lambda: _env_bool("STUHUBM_PERSIST", False),
              help="write changes to flash immediately (/F instead of /S)")
@click.option("--timeout", type=int, default=10, help="per-command timeout (seconds)")
@click.option("--json", "as_json", is_flag=True, help="machine-readable JSON output")
@click.option("--verbose", is_flag=True, help="print the exact binary invocation")
@click.pass_context
def main(ctx, binary, sudo, password, persist, timeout, as_json, verbose):
    """Manage StarTech Industrial USB Hubs (unofficial)."""
    mgr = HubManager(
        binary=binary,
        use_sudo=_env_bool("STUHUBM_SUDO", True) if sudo is None else sudo,
        password=password or "",
        persist=persist,
        timeout=timeout,
    )
    if verbose:
        mgr.logger = lambda m: click.echo(m, err=True)
    ctx.obj = type("Ctx", (), {"mgr": mgr, "json": as_json})()


@main.command()
@click.pass_obj
def health(obj):
    """Check the binary is present and list hubs."""
    located = shutil.which(obj.mgr.binary) or (obj.mgr.binary if os.path.isfile(obj.mgr.binary) else None)
    if not located:
        click.echo(f"binary: NOT FOUND ({obj.mgr.binary})", err=True)
        raise SystemExit(3)
    click.echo(f"binary: {located}")
    click.echo(f"sudo:   {'yes' if obj.mgr.use_sudo else 'no'}")
    hubs = obj.mgr.discover()
    click.echo(f"hubs:   {len(hubs)} detected" if hubs else "hubs:   none detected")
    for h in hubs:
        click.echo(f"  - {h.port}  {h.model} (sn {h.serial}, {h.n_ports} ports, fw {h.firmware})")


@main.command("list")
@click.pass_obj
def list_(obj):
    """Discover connected hubs."""
    hubs = obj.mgr.discover()
    if obj.json:
        click.echo(json.dumps([_hub_dict(h) for h in hubs], indent=2))
    elif not hubs:
        click.echo("no managed hubs detected")
    else:
        for h in hubs:
            _emit(obj, h)


@main.command()
@click.argument("port")
@click.pass_obj
def status(obj, port):
    """Show port states of a hub."""
    _emit(obj, obj.mgr.hub(port))


@main.command()
@click.argument("port")
@click.argument("ports")
@click.pass_obj
def on(obj, port, ports):
    """Turn the given port(s) on (PORTS = N | N,N,N | all)."""
    hub, p = obj.mgr.hub(port), _ports(ports)
    hub.set_all(True) if p == "all" else hub.set_ports(p, True)
    _emit(obj, hub.refresh())


@main.command()
@click.argument("port")
@click.argument("ports")
@click.pass_obj
def off(obj, port, ports):
    """Turn the given port(s) off (PORTS = N | N,N,N | all)."""
    hub, p = obj.mgr.hub(port), _ports(ports)
    hub.set_all(False) if p == "all" else hub.set_ports(p, False)
    _emit(obj, hub.refresh())


@main.command()
@click.argument("port")
@click.argument("ports")
@click.pass_obj
def toggle(obj, port, ports):
    """Invert the given port(s) (PORTS = N | N,N,N)."""
    p = _ports(ports)
    if p == "all":
        raise click.BadParameter("'toggle' does not accept 'all'")
    hub = obj.mgr.hub(port)
    for n in p:
        hub.toggle(n)
    _emit(obj, hub.refresh())


@main.command("all")
@click.argument("port")
@click.argument("state", type=click.Choice(["on", "off"]))
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
    click.echo(f"{port}: current port states saved to flash")


@main.command()
@click.argument("port")
@click.pass_obj
def reset(obj, port):
    """Hardware-reset the hub."""
    Hub(port=port, manager=obj.mgr).reset()
    click.echo(f"{port}: reset requested")


@main.command()
@click.argument("port")
@click.pass_obj
def restore(obj, port):
    """Restore factory defaults (all ports on, password 'pass')."""
    Hub(port=port, manager=obj.mgr).restore_defaults()
    click.echo(f"{port}: factory defaults restored")


@main.command()
@click.argument("port")
@click.pass_obj
def passwd(obj, port):
    """Change the hub password."""
    old = click.prompt("Old password (blank if default 'pass')",
                       default="", hide_input=True, show_default=False)
    new = click.prompt("New password (max 8 chars)",
                       hide_input=True, confirmation_prompt=True)
    if not new or len(new) > 8:
        raise click.ClickException("password must be 1-8 characters")
    Hub(port=port, manager=obj.mgr).change_password(old, new)
    click.echo(f"{port}: password changed")


if __name__ == "__main__":
    main()
