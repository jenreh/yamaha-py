"""Sound commands: mode / straight / direct / sleep."""

from __future__ import annotations

from typing import Optional

import typer

from yamactl.cli._common import ProfileOpt, ZoneOpt, make_service
from yamactl.core.models import DSP_MODES
from yamactl.output.formatters import (
    direct_confirmation,
    dsp_mode_confirmation,
    sleep_confirmation,
    straight_confirmation,
)

app = typer.Typer(no_args_is_help=True)


@app.command("mode")
def sound_mode(
    mode: Optional[str] = typer.Argument(default=None, help='DSP mode name (e.g. "Hall in Munich").'),
    list_modes: bool = typer.Option(False, "--list", "-l", help="List available DSP modes."),
    profile: ProfileOpt = None,
    zone: ZoneOpt = None,
) -> None:
    """Set DSP / surround mode."""
    if list_modes:
        for m in DSP_MODES:
            typer.echo(m)
        return
    if mode is None:
        typer.echo("Error: provide a mode name or use --list to see available modes.", err=True)
        raise typer.Exit(2)
    make_service(profile, zone).set_dsp_mode(mode)
    typer.echo(dsp_mode_confirmation(mode))


@app.command("straight")
def sound_straight(
    state: str = typer.Argument(help="on or off"),
    profile: ProfileOpt = None,
    zone: ZoneOpt = None,
) -> None:
    """Enable or disable Straight mode (bypasses DSP)."""
    enabled = _parse_onoff(state, "straight")
    make_service(profile, zone).set_straight(enabled)
    typer.echo(straight_confirmation(enabled))


@app.command("direct")
def sound_direct(
    state: str = typer.Argument(help="on or off"),
    profile: ProfileOpt = None,
    zone: ZoneOpt = None,
) -> None:
    """Enable or disable Pure Direct mode."""
    enabled = _parse_onoff(state, "direct")
    make_service(profile, zone).set_direct(enabled)
    typer.echo(direct_confirmation(enabled))


@app.command("sleep")
def sound_sleep(
    value: str = typer.Argument(help="Sleep timer in minutes (30/60/90/120) or 'off'."),
    profile: ProfileOpt = None,
    zone: ZoneOpt = None,
) -> None:
    """Set or clear the sleep timer."""
    minutes: Optional[int]
    if value.lower() == "off":
        minutes = None
    elif value.isdigit():
        minutes = int(value)
    else:
        typer.echo(f"Error: sleep value must be a number or 'off', got '{value}'", err=True)
        raise typer.Exit(2)
    make_service(profile, zone).set_sleep(minutes)
    typer.echo(sleep_confirmation(value))


def _parse_onoff(value: str, name: str) -> bool:
    if value.lower() == "on":
        return True
    if value.lower() == "off":
        return False
    typer.echo(f"Error: {name} must be 'on' or 'off', got '{value}'", err=True)
    raise typer.Exit(2)
