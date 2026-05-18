"""Raw protocol commands for diagnostics."""

from __future__ import annotations

import typer

from yamactl.cli._common import ProfileOpt, ZoneOpt, make_service

app = typer.Typer(no_args_is_help=True)


@app.command("ynca")
def raw_ynca(
    command: str = typer.Argument(help='Raw YNCA command string, e.g. "@MAIN:VOL=?"'),
    profile: ProfileOpt = None,
    zone: ZoneOpt = None,
) -> None:
    """Send a raw YNCA command and print the response."""
    result = make_service(profile, zone).send_raw_ynca(command)
    typer.echo(result)


@app.command("xml")
def raw_xml(
    xml: str = typer.Argument(help="Full YAMAHA_AV XML envelope to send."),
    profile: ProfileOpt = None,
    zone: ZoneOpt = None,
) -> None:
    """Send a raw XML command and print the XML response."""
    result = make_service(profile, zone).send_raw_xml(xml)
    typer.echo(result)
