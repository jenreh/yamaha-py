"""Power commands: on / standby."""

from __future__ import annotations

import typer

from yamactl.cli._common import ProfileOpt, ZoneOpt, make_service
from yamactl.output.formatters import power_confirmation

app = typer.Typer(no_args_is_help=True)


@app.command("on")
def power_on(
    profile: ProfileOpt = None,
    zone: ZoneOpt = None,
) -> None:
    """Power on the receiver."""
    make_service(profile, zone).set_power("on")
    typer.echo(power_confirmation("on"))


@app.command("standby")
def power_standby(
    profile: ProfileOpt = None,
    zone: ZoneOpt = None,
) -> None:
    """Put receiver into standby."""
    make_service(profile, zone).set_power("standby")
    typer.echo(power_confirmation("standby"))
