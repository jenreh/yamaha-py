"""Mute commands: on / off / toggle."""

from __future__ import annotations

import typer

from yamactl.cli._common import ProfileOpt, ZoneOpt, make_service
from yamactl.output.formatters import mute_confirmation

app = typer.Typer(no_args_is_help=True)


@app.command("on")
def mute_on(profile: ProfileOpt = None, zone: ZoneOpt = None) -> None:
    """Enable mute."""
    make_service(profile, zone).set_mute(True)
    typer.echo(mute_confirmation(True))


@app.command("off")
def mute_off(profile: ProfileOpt = None, zone: ZoneOpt = None) -> None:
    """Disable mute."""
    make_service(profile, zone).set_mute(False)
    typer.echo(mute_confirmation(False))


@app.command("toggle")
def mute_toggle(profile: ProfileOpt = None, zone: ZoneOpt = None) -> None:
    """Toggle mute state."""
    new_state = make_service(profile, zone).toggle_mute()
    typer.echo(mute_confirmation(new_state))
