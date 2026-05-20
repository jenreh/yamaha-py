"""Input commands: list / set."""

from __future__ import annotations

import json

import typer

from yamactl.cli._common import JsonOpt, ProfileOpt, ZoneOpt, make_client
from yamactl.output.formatters import input_confirmation
from yamactl.output.rich_ui import render_inputs

app = typer.Typer(no_args_is_help=True)


@app.command("list")
def input_list(
    profile: ProfileOpt = None,
    zone: ZoneOpt = None,
    json_output: JsonOpt = False,
) -> None:
    """List available input sources."""
    inputs = make_client(profile, zone).list_inputs()
    if json_output:
        typer.echo(json.dumps({"inputs": inputs}))
    else:
        render_inputs(inputs)


@app.command("set")
def input_set(
    source: str = typer.Argument(help="Input source name (e.g. HDMI1, TUNER, USB)."),
    profile: ProfileOpt = None,
    zone: ZoneOpt = None,
) -> None:
    """Select an input source."""
    make_client(profile, zone).set_input(source)
    typer.echo(input_confirmation(source))
