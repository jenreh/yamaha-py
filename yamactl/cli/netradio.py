"""Net Radio commands — URL preset management and playback control via UPnP."""

from __future__ import annotations

import json

import typer
from rich import print as rprint

from yamactl.cli._common import JsonOpt, ProfileOpt, make_service
from yamactl.core.config import load_profile, save_profile
from yamactl.output.rich_ui import render_netradio_status

app = typer.Typer(no_args_is_help=True)
url_app = typer.Typer(no_args_is_help=True, help="Manage streaming URL presets.")
app.add_typer(url_app, name="url")


@app.command("status")
def netradio_status(
    profile: ProfileOpt = None,
    json_output: JsonOpt = False,
) -> None:
    """Show Net Radio / Server now-playing info."""
    svc = make_service(profile, None)
    receiver = svc.get_status()
    if receiver.input == "SERVER":
        s = svc.get_server_status()
    else:
        s = svc.get_netradio_status()
    if json_output:
        typer.echo(json.dumps(s.model_dump()))
    else:
        render_netradio_status(s)


@app.command("play")
def netradio_play(
    name: str = typer.Argument(
        default="", help="URL preset name. Omit to resume last stream."
    ),
    profile: ProfileOpt = None,
) -> None:
    """Play a named URL preset, or resume the last played stream."""
    cfg = load_profile(profile)
    resolved = name or cfg.netradio_last
    if not resolved:
        typer.echo("Error: no preset name given and no last stream recorded.", err=True)
        raise typer.Exit(2)
    url = cfg.netradio_presets.get(resolved)
    if not url:
        available = ", ".join(cfg.netradio_presets) or "(none)"
        typer.echo(
            f"Error: preset '{resolved}' not found. Available: {available}", err=True
        )
        raise typer.Exit(2)
    save_profile(cfg.model_copy(update={"netradio_last": resolved}))
    make_service(profile, None).play_netradio_url(url, resolved)
    typer.echo(f"Net Radio: playing '{resolved}'")


@app.command("pause")
def netradio_pause(profile: ProfileOpt = None) -> None:
    """Pause playback."""
    make_service(profile, None).pause_netradio_url()
    typer.echo("Net Radio: pause")


@app.command("stop")
def netradio_stop(profile: ProfileOpt = None) -> None:
    """Stop playback."""
    make_service(profile, None).stop_netradio_url()
    typer.echo("Net Radio: stop")


@app.command("list")
def netradio_list(profile: ProfileOpt = None) -> None:
    """List all streaming URL presets."""
    cfg = load_profile(profile)
    if not cfg.netradio_presets:
        typer.echo("No URL presets. Use: netradio url add <name> <url>")
        return
    for name, url in cfg.netradio_presets.items():
        typer.echo(f"  {name:<20} {url}")


# ── url subcommands ───────────────────────────────────────────────────────────


@url_app.command("add")
def url_add(
    name: str = typer.Argument(help="Preset name (e.g. '1live')."),
    url: str = typer.Argument(help="Streaming URL (http/https)."),
    profile: ProfileOpt = None,
) -> None:
    """Add or update a streaming URL preset."""
    cfg = load_profile(profile)
    cfg.netradio_presets[name] = url
    save_profile(cfg)
    rprint(f"[green]Saved[/green] '{name}' → {url}")


@url_app.command("list")
def url_list(profile: ProfileOpt = None) -> None:
    """List all streaming URL presets."""
    cfg = load_profile(profile)
    if not cfg.netradio_presets:
        typer.echo("No URL presets. Use: netradio url add <name> <url>")
        return
    for name, url in cfg.netradio_presets.items():
        typer.echo(f"  {name:<20} {url}")


@url_app.command("remove")
def url_remove(
    name: str = typer.Argument(help="Preset name to remove."),
    profile: ProfileOpt = None,
) -> None:
    """Remove a streaming URL preset."""
    cfg = load_profile(profile)
    if name not in cfg.netradio_presets:
        typer.echo(f"Error: preset '{name}' not found.", err=True)
        raise typer.Exit(2)
    del cfg.netradio_presets[name]
    save_profile(cfg)
    typer.echo(f"Removed '{name}'")
