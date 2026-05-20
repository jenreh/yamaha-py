"""Scene commands: load."""

from __future__ import annotations

import typer

from yamactl.cli._common import ProfileOpt, ZoneOpt, make_client
from yamactl.output.formatters import scene_confirmation

app = typer.Typer(no_args_is_help=True)


@app.command("load")
def scene_load(
    scene: int = typer.Argument(help="Scene number 1–4."),
    profile: ProfileOpt = None,
    zone: ZoneOpt = None,
) -> None:
    """Load a Yamaha scene preset (1–4)."""
    if scene not in (1, 2, 3, 4):
        typer.echo(f"Error: scene must be 1–4, got {scene}", err=True)
        raise typer.Exit(2)
    make_client(profile, zone).load_scene(scene)
    typer.echo(scene_confirmation(scene))
