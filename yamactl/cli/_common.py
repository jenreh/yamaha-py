"""Shared CLI helpers — profile/zone options and client factory."""

from __future__ import annotations

from typing import Annotated

import typer

from yamactl.client import YamaCtlClient
from yamactl.core.models import ZoneName

ProfileOpt = Annotated[
    str | None, typer.Option("--profile", "-p", help="Config profile name.")
]
ZoneOpt = Annotated[
    str | None, typer.Option("--zone", "-z", help="Zone: main or zone2.")
]
JsonOpt = Annotated[bool, typer.Option("--json", help="Output as JSON.")]


def make_client(profile: str | None, zone: str | None) -> YamaCtlClient:
    zone_name: ZoneName | None = None
    if zone is not None:
        if zone not in ("main", "zone2"):
            typer.echo(
                f"Error: --zone must be 'main' or 'zone2', got '{zone}'", err=True
            )
            raise typer.Exit(2)
        zone_name = zone  # type: ignore[assignment]
    return YamaCtlClient.from_profile(profile, zone_name)
