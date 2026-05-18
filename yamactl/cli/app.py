"""Root Typer application — registers all sub-apps and handles errors."""

from __future__ import annotations

import sys

import typer
from rich import print as rprint

from yamactl.cli import (
    config_cmds,
    input_,
    mute,
    netradio,
    power,
    raw,
    scene,
    sound,
    status,
    tuner,
    volume,
)
from yamactl.core.errors import EXIT_CODES, YamaCtlError

app = typer.Typer(
    name="yamactl",
    help="Offline LAN CLI for Yamaha RX-V475 AV receiver.",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)

app.add_typer(power.app, name="power", help="Power control.")
app.add_typer(volume.app, name="volume", help="Volume control.")
app.add_typer(mute.app, name="mute", help="Mute control.")
app.add_typer(input_.app, name="input", help="Input source selection.")
app.add_typer(sound.app, name="sound", help="DSP / surround mode and sleep timer.")
app.add_typer(scene.app, name="scene", help="Yamaha scene presets.")
app.add_typer(tuner.app, name="tuner", help="Tuner control (band, frequency, presets).")
app.add_typer(
    netradio.app,
    name="netradio",
    help="Netradio playback. Add radio URLs with: yamactl netradio url add <name> <url> first.",
)
app.add_typer(raw.app, name="raw", help="Send raw protocol commands for diagnostics.")
app.add_typer(config_cmds.app, name="config", help="Manage receiver profiles.")

app.command("status")(status.status)
app.command("discover")(status.discover)


def run() -> None:
    try:
        app()
    except YamaCtlError as exc:
        code = EXIT_CODES.get(type(exc), 1)
        rprint(f"[red]Error:[/red] {exc}", file=sys.stderr)
        raise SystemExit(code) from exc
    except KeyboardInterrupt:
        raise SystemExit(130) from None
