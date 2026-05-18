"""Status and discover commands."""

from __future__ import annotations

import json
from typing import Optional

import typer

from yamactl.cli._common import JsonOpt, ProfileOpt, ZoneOpt, make_service
from yamactl.output.formatters import status_to_dict, status_to_plain
from yamactl.output.rich_ui import render_discovery, render_status


def status(
    profile: ProfileOpt = None,
    zone: ZoneOpt = None,
    json_output: JsonOpt = False,
) -> None:
    """Show full receiver status."""
    result = make_service(profile, zone).get_status()
    if json_output:
        typer.echo(json.dumps(status_to_dict(result), indent=2))
    else:
        render_status(result)


def discover(
    subnet: Optional[str] = typer.Option(
        None,
        "--subnet",
        help="CIDR subnet to scan, e.g. 192.168.178.0/24. Required — no auto-scan for safety.",
    ),
    allow_public_ip: bool = typer.Option(
        False,
        "--allow-public-ip",
        help="Allow scanning non-RFC-1918 addresses (use with caution).",
    ),
    json_output: JsonOpt = False,
) -> None:
    """Discover Yamaha receivers on the local network."""
    from yamactl.discovery.network import scan_subnet

    if subnet is None:
        typer.echo(
            "Error: --subnet is required. Example: --subnet 192.168.178.0/24\n"
            "       (auto-scan disabled for security — LAN-only policy)",
            err=True,
        )
        raise typer.Exit(2)

    typer.echo(f"Scanning {subnet} for Yamaha receivers…")
    candidates = scan_subnet(subnet, allow_public_ip=allow_public_ip)

    if json_output:
        typer.echo(
            json.dumps(
                [c.model_dump() for c in candidates],
                indent=2,
            )
        )
        return

    render_discovery(candidates)

    if not candidates:
        return

    save = typer.confirm("\nSave a discovered receiver as a profile?", default=False)
    if not save:
        return

    hosts = [c.host for c in candidates]
    host = typer.prompt("Enter host IP to save", default=hosts[0])
    candidate = next((c for c in candidates if c.host == host), None)

    name = typer.prompt("Profile name", default="livingroom")
    protocol = typer.prompt(
        "Protocol",
        default=candidate.protocol if candidate else "ynca",
    )

    from yamactl.core.config import save_profile
    from yamactl.core.models import ReceiverConfig

    cfg = ReceiverConfig(name=name, host=host, protocol=protocol)  # type: ignore[arg-type]
    save_profile(cfg, set_default=True)
    typer.echo(f"Saved profile '{name}' → {host} ({protocol}). Set as default.")
