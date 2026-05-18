"""Config management commands: init / show / set-host / set-protocol."""

from __future__ import annotations

import json

import typer

from yamactl.cli._common import JsonOpt
from yamactl.core.config import (
    config_path,
    get_default_profile,
    list_profiles,
    load_profile,
    save_profile,
    set_default_profile,
)
from yamactl.core.models import ProtocolName, ReceiverConfig, ZoneName

app = typer.Typer(no_args_is_help=True)


@app.command("init")
def config_init(
    name: str = typer.Option(..., "--name", "-n", help="Profile name."),
    host: str = typer.Option(..., "--host", "-h", help="Receiver IP address."),
    protocol: str = typer.Option("ynca", "--protocol", help="Protocol: ynca or http_xml."),
    zone: str = typer.Option("main", "--zone", "-z", help="Default zone: main or zone2."),
    timeout: float = typer.Option(3.0, "--timeout", help="Connection timeout in seconds."),
    retries: int = typer.Option(1, "--retries", help="Number of retries on timeout."),
    set_default: bool = typer.Option(True, "--default/--no-default", help="Set as default profile."),
) -> None:
    """Create or update a receiver profile."""
    if protocol not in ("ynca", "http_xml"):
        typer.echo("Error: --protocol must be 'ynca' or 'http_xml'", err=True)
        raise typer.Exit(2)
    if zone not in ("main", "zone2"):
        typer.echo("Error: --zone must be 'main' or 'zone2'", err=True)
        raise typer.Exit(2)

    cfg = ReceiverConfig(
        name=name,
        host=host,
        protocol=protocol,  # type: ignore[arg-type]
        zone=zone,  # type: ignore[arg-type]
        timeout_seconds=timeout,
        retries=retries,
    )
    save_profile(cfg, set_default=set_default)
    default_note = " (set as default)" if set_default else ""
    typer.echo(f"Profile '{name}' saved → {host} via {protocol}{default_note}")
    typer.echo(f"Config: {config_path()}")


@app.command("show")
def config_show(
    profile: str = typer.Option(None, "--profile", "-p", help="Profile name."),
    json_output: JsonOpt = False,
) -> None:
    """Show config file path and profile details."""
    profiles = list_profiles()
    default = get_default_profile()

    if json_output:
        typer.echo(
            json.dumps(
                {"default_profile": default, "profiles": profiles},
                indent=2,
            )
        )
        return

    typer.echo(f"Config file: {config_path()}")
    typer.echo(f"Default profile: {default or '(none)'}")
    typer.echo(f"Profiles: {', '.join(profiles.keys()) or '(none)'}")

    if profile:
        cfg = load_profile(profile)
        typer.echo(f"\n[{cfg.name}]")
        typer.echo(f"  host     = {cfg.host}")
        typer.echo(f"  protocol = {cfg.protocol}")
        typer.echo(f"  zone     = {cfg.zone}")
        typer.echo(f"  timeout  = {cfg.timeout_seconds}s")
        typer.echo(f"  retries  = {cfg.retries}")


@app.command("set-host")
def config_set_host(
    host: str = typer.Argument(help="New receiver IP address."),
    profile: str = typer.Option(None, "--profile", "-p", help="Profile to update."),
) -> None:
    """Update the host IP for a profile."""
    cfg = load_profile(profile)
    updated = cfg.model_copy(update={"host": host})
    save_profile(updated)
    typer.echo(f"Profile '{cfg.name}' host updated to {host}")


@app.command("set-protocol")
def config_set_protocol(
    protocol: str = typer.Argument(help="Protocol: ynca or http_xml."),
    profile: str = typer.Option(None, "--profile", "-p", help="Profile to update."),
) -> None:
    """Update the protocol for a profile."""
    if protocol not in ("ynca", "http_xml"):
        typer.echo("Error: protocol must be 'ynca' or 'http_xml'", err=True)
        raise typer.Exit(2)
    cfg = load_profile(profile)
    updated = cfg.model_copy(update={"protocol": protocol})
    save_profile(updated)
    typer.echo(f"Profile '{cfg.name}' protocol updated to {protocol}")


@app.command("set-default")
def config_set_default(
    name: str = typer.Argument(help="Profile name to set as default."),
) -> None:
    """Set the default profile."""
    set_default_profile(name)
    typer.echo(f"Default profile: {name}")
