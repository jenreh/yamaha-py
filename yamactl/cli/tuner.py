"""Tuner commands: status / band / fm / am / preset."""

from __future__ import annotations

import json

import typer

from yamactl.cli._common import JsonOpt, ProfileOpt, make_client
from yamactl.output.rich_ui import render_tuner_status

app = typer.Typer(no_args_is_help=True)


@app.command("status")
def tuner_status(
    profile: ProfileOpt = None,
    json_output: JsonOpt = False,
) -> None:
    """Show tuner status (band, frequency, preset, RDS)."""
    s = make_client(profile, None).get_tuner_status()
    if json_output:
        typer.echo(json.dumps(s.model_dump()))
    else:
        render_tuner_status(s)


@app.command("band")
def tuner_band(
    band: str = typer.Argument(help="FM or AM"),
    profile: ProfileOpt = None,
) -> None:
    """Switch tuner band."""
    b = band.upper()
    if b not in ("FM", "AM"):
        typer.echo(f"Error: band must be FM or AM, got '{band}'", err=True)
        raise typer.Exit(2)
    make_client(profile, None).set_tuner_band(b)
    typer.echo(f"Tuner band: {b}")


@app.command("fm")
def tuner_fm(
    freq: float = typer.Argument(help="FM frequency in MHz (e.g. 87.50)."),
    profile: ProfileOpt = None,
) -> None:
    """Tune FM frequency in MHz."""
    make_client(profile, None).set_tuner_fm_freq(freq)
    typer.echo(f"Tuner FM: {freq:.2f} MHz")


@app.command("am")
def tuner_am(
    freq: int = typer.Argument(help="AM frequency in kHz (e.g. 810)."),
    profile: ProfileOpt = None,
) -> None:
    """Tune AM frequency in kHz."""
    make_client(profile, None).set_tuner_am_freq(freq)
    typer.echo(f"Tuner AM: {freq} kHz")


@app.command("preset")
def tuner_preset(
    preset: int = typer.Argument(help="Preset number (1+)."),
    profile: ProfileOpt = None,
) -> None:
    """Recall a tuner preset."""
    if preset < 1:
        typer.echo(f"Error: preset must be >= 1, got {preset}", err=True)
        raise typer.Exit(2)
    make_client(profile, None).set_tuner_preset(preset)
    typer.echo(f"Tuner preset: {preset}")
