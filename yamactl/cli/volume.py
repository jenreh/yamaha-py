"""Volume commands: get / set / up / down."""

from __future__ import annotations

import json

import typer

from yamactl.cli._common import JsonOpt, ProfileOpt, ZoneOpt, make_service
from yamactl.core.models import VOLUME_MAX, VOLUME_MIN
from yamactl.output.formatters import volume_confirmation, volume_step_confirmation

app = typer.Typer(no_args_is_help=True)


@app.command("get")
def volume_get(
    profile: ProfileOpt = None,
    zone: ZoneOpt = None,
    json_output: JsonOpt = False,
) -> None:
    """Get current volume in dB."""
    db = make_service(profile, zone).get_volume_db()
    if json_output:
        typer.echo(json.dumps({"volume_db": db}))
    else:
        typer.echo(volume_confirmation(db))


@app.command("set")
def volume_set(
    db: float = typer.Argument(
        help=f"Volume in dB ({VOLUME_MIN} to {VOLUME_MAX}). Use -- before negative values: volume set -- -48"
    ),
    profile: ProfileOpt = None,
    zone: ZoneOpt = None,
) -> None:
    """Set volume to an absolute dB value."""
    make_service(profile, zone).set_volume_db(db)
    typer.echo(volume_confirmation(db))


@app.command("up")
def volume_up(
    steps: int = typer.Option(1, "--steps", "-s", help="Number of 0.5 dB steps."),
    profile: ProfileOpt = None,
    zone: ZoneOpt = None,
) -> None:
    """Increase volume by N steps (1 step = 0.5 dB)."""
    make_service(profile, zone).volume_up(steps)
    typer.echo(volume_step_confirmation("up", steps))


@app.command("down")
def volume_down(
    steps: int = typer.Option(1, "--steps", "-s", help="Number of 0.5 dB steps."),
    profile: ProfileOpt = None,
    zone: ZoneOpt = None,
) -> None:
    """Decrease volume by N steps (1 step = 0.5 dB)."""
    make_service(profile, zone).volume_down(steps)
    typer.echo(volume_step_confirmation("down", steps))
