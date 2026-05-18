"""Rich table renderers."""

from __future__ import annotations

from rich import print as rprint
from rich.console import Console
from rich.table import Table

from yamactl.core.models import (
    DiscoveryCandidate,
    NetRadioListInfo,
    NetRadioStatus,
    ReceiverStatus,
    TunerStatus,
)

console = Console()


def render_status(s: ReceiverStatus) -> None:
    table = Table(
        title=f"{s.model or 'Yamaha'} — {s.host}", show_header=False, box=None
    )
    table.add_column("Key", style="bold cyan", min_width=14)
    table.add_column("Value")

    power_style = "green" if s.power == "on" else "yellow"
    table.add_row("Power", f"[{power_style}]{s.power or 'unknown'}[/{power_style}]")
    table.add_row("Input", s.input or "—")

    if s.volume_db is not None:
        table.add_row("Volume", f"{s.volume_db:+.1f} dB")
    else:
        table.add_row("Volume", "—")

    mute_val = "[red]muted[/red]" if s.mute else "off"
    table.add_row("Mute", mute_val)

    if s.dsp_mode:
        table.add_row("DSP Mode", s.dsp_mode)
    if s.sleep_minutes:
        table.add_row("Sleep", f"{s.sleep_minutes} min")
    if s.profile:
        table.add_row("Profile", s.profile)

    console.print(table)


def render_tuner_status(s: TunerStatus) -> None:
    table = Table(title="Tuner", show_header=False, box=None)
    table.add_column("Key", style="bold cyan", min_width=14)
    table.add_column("Value")
    table.add_row("Band", s.band or "—")
    if s.band == "FM" and s.fm_freq_mhz is not None:
        table.add_row("Frequency", f"{s.fm_freq_mhz:.2f} MHz")
    elif s.band == "AM" and s.am_freq_khz is not None:
        table.add_row("Frequency", f"{s.am_freq_khz} kHz")
    if s.preset:
        table.add_row("Preset", s.preset)
    if s.fm_mode:
        table.add_row("FM Mode", s.fm_mode)
    if s.rds_station:
        table.add_row("RDS Station", s.rds_station)
    if s.tuned is not None:
        table.add_row(
            "Tuned", "[green]yes[/green]" if s.tuned else "[yellow]no[/yellow]"
        )
    console.print(table)


def render_netradio_list(lst: NetRadioListInfo) -> None:
    layer_info = f"Layer {lst.layer}" if lst.layer else ""
    title = f"Net Radio — {lst.layer_name or 'Menu'}" + (
        f" ({layer_info})" if layer_info else ""
    )
    table = Table(title=title, show_header=True, box=None)
    table.add_column("#", style="dim", width=3)
    table.add_column("Item")
    table.add_column("Type", style="dim")

    for e in lst.entries:
        if not e.text or e.attribute == "Unselectable":
            continue
        color = "cyan" if e.attribute == "Container" else "green"
        table.add_row(str(e.line), f"[{color}]{e.text}[/{color}]", e.attribute)

    console.print(table)
    if lst.max_line and lst.current_line and lst.max_line > 8:
        rprint(
            f"[dim]Items {lst.current_line}–{min(lst.current_line + 7, lst.max_line)} of {lst.max_line}. Use 'select' and 'back' to navigate.[/dim]"
        )


def render_netradio_status(s: NetRadioStatus) -> None:
    pb_color = "green" if s.playback == "Play" else "yellow"
    table = Table(title="Net Radio", show_header=False, box=None)
    table.add_column("Key", style="bold cyan", min_width=14)
    table.add_column("Value")
    if s.available is not None:
        table.add_row(
            "Available", "[green]yes[/green]" if s.available else "[yellow]no[/yellow]"
        )
    if s.playback:
        table.add_row("Playback", f"[{pb_color}]{s.playback}[/{pb_color}]")
    table.add_row("Station", s.station or "—")
    if s.song:
        table.add_row("Song", s.song)
    if s.album:
        table.add_row("Album", s.album)
    if s.elapsed_time:
        table.add_row("Elapsed", s.elapsed_time)
    console.print(table)


def render_inputs(inputs: list[str]) -> None:
    for inp in inputs:
        rprint(f"  [cyan]•[/cyan] {inp}")


def render_discovery(candidates: list[DiscoveryCandidate]) -> None:
    if not candidates:
        rprint("[yellow]No Yamaha receivers found.[/yellow]")
        return
    table = Table(title="Discovered Yamaha Receivers")
    table.add_column("Host", style="cyan")
    table.add_column("Model")
    table.add_column("YNCA")
    table.add_column("HTTP")
    table.add_column("Confidence")

    for c in candidates:
        ynca_mark = "[green]✓[/green]" if c.ynca_available else "[dim]—[/dim]"
        http_mark = "[green]✓[/green]" if c.http_available else "[dim]—[/dim]"
        conf_color = "green" if c.confidence == "high" else "yellow"
        table.add_row(
            c.host,
            c.model or "—",
            ynca_mark,
            http_mark,
            f"[{conf_color}]{c.confidence}[/{conf_color}]",
        )
    console.print(table)
