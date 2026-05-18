"""Rich table renderers."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table
from rich import print as rprint

from yamactl.core.models import ReceiverStatus, DiscoveryCandidate

console = Console()


def render_status(s: ReceiverStatus) -> None:
    table = Table(title=f"{s.model or 'Yamaha'} — {s.host}", show_header=False, box=None)
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
