"""FastMCP server — expose Yamaha receiver control as MCP tools."""

from __future__ import annotations

from typing import Annotated, Literal

from fastmcp import FastMCP
from pydantic import Field

from yamactl.client import YamaCtlClient

mcp: FastMCP = FastMCP(
    name="yamactl",
    instructions=(
        "Control a Yamaha AV receiver over the local network. "
        "Use the default configured profile. "
        "Tools cover power, volume, mute, input selection, scene presets, "
        "tuner (FM/AM) and net radio / streaming playback."
    ),
)

# ── helpers ───────────────────────────────────────────────────────────────────


def _client() -> YamaCtlClient:
    """Return a client using the default profile and main zone."""
    return YamaCtlClient.from_profile()


# ── Status ────────────────────────────────────────────────────────────────────


@mcp.tool
def get_receiver_status() -> dict:
    """Return full receiver status (power, input, volume, mute, DSP mode)."""
    with _client() as c:
        return c.get_status().model_dump()


# ── Power ─────────────────────────────────────────────────────────────────────


@mcp.tool
def set_power(state: Literal["on", "standby"]) -> str:
    """Power the receiver on or put it into standby."""
    with _client() as c:
        c.set_power(state)
    return f"Power: {state}"


# ── Volume ────────────────────────────────────────────────────────────────────


@mcp.tool
def get_volume() -> dict:
    """Return the current volume in dB."""
    with _client() as c:
        db = c.get_volume()
    return {"volume_db": db}


@mcp.tool
def set_volume(
    db: Annotated[float, Field(description="Volume in dB (-80.5 to 16.5)", ge=-80.5, le=16.5)],
) -> str:
    """Set volume to an absolute dB value."""
    with _client() as c:
        c.set_volume(db)
    return f"Volume: {db:+.1f} dB"


@mcp.tool
def volume_up(steps: Annotated[int, Field(description="Number of 0.5 dB steps", ge=1)] = 1) -> str:
    """Increase volume by N steps (1 step = 0.5 dB)."""
    with _client() as c:
        c.volume_up(steps)
    return f"Volume up {steps} step(s)"


@mcp.tool
def volume_down(steps: Annotated[int, Field(description="Number of 0.5 dB steps", ge=1)] = 1) -> str:
    """Decrease volume by N steps (1 step = 0.5 dB)."""
    with _client() as c:
        c.volume_down(steps)
    return f"Volume down {steps} step(s)"


# ── Mute ──────────────────────────────────────────────────────────────────────


@mcp.tool
def get_mute() -> dict:
    """Return the current mute state."""
    with _client() as c:
        enabled = c.get_mute()
    return {"mute": enabled}


@mcp.tool
def set_mute(enabled: bool) -> str:
    """Enable or disable mute."""
    with _client() as c:
        c.set_mute(enabled)
    return f"Mute: {'on' if enabled else 'off'}"


@mcp.tool
def toggle_mute() -> dict:
    """Toggle mute; returns the new state."""
    with _client() as c:
        new_state = c.toggle_mute()
    return {"mute": new_state}


# ── Input ─────────────────────────────────────────────────────────────────────


@mcp.tool
def list_inputs() -> dict:
    """Return all available input source names."""
    with _client() as c:
        inputs = c.list_inputs()
    return {"inputs": inputs}


@mcp.tool
def set_input(source: Annotated[str, Field(description="Input source name, e.g. HDMI1, TUNER, USB")]) -> str:
    """Select an input source."""
    with _client() as c:
        c.set_input(source)
    return f"Input: {source}"


# ── Scene ─────────────────────────────────────────────────────────────────────


@mcp.tool
def load_scene(number: Annotated[int, Field(description="Scene preset number 1–4", ge=1, le=4)]) -> str:
    """Load a Yamaha scene preset (1–4)."""
    with _client() as c:
        c.load_scene(number)
    return f"Scene {number} loaded"


# ── Tuner ─────────────────────────────────────────────────────────────────────


@mcp.tool
def get_tuner_status() -> dict:
    """Return tuner status (band, frequency, preset, RDS)."""
    with _client() as c:
        return c.get_tuner_status().model_dump()


@mcp.tool
def set_tuner_band(band: Literal["FM", "AM"]) -> str:
    """Switch the tuner band."""
    with _client() as c:
        c.set_tuner_band(band)
    return f"Tuner band: {band}"


@mcp.tool
def set_tuner_fm_freq(
    mhz: Annotated[float, Field(description="FM frequency in MHz, e.g. 89.5")],
) -> str:
    """Tune the FM tuner to a frequency in MHz."""
    with _client() as c:
        c.set_tuner_fm_freq(mhz)
    return f"Tuner FM: {mhz:.2f} MHz"


@mcp.tool
def set_tuner_am_freq(
    khz: Annotated[int, Field(description="AM frequency in kHz, e.g. 810")],
) -> str:
    """Tune the AM tuner to a frequency in kHz."""
    with _client() as c:
        c.set_tuner_am_freq(khz)
    return f"Tuner AM: {khz} kHz"


@mcp.tool
def set_tuner_preset(
    num: Annotated[int, Field(description="Preset number (1 or above)", ge=1)],
) -> str:
    """Recall a stored tuner preset."""
    with _client() as c:
        c.set_tuner_preset(num)
    return f"Tuner preset: {num}"


# ── Net Radio / Streaming ─────────────────────────────────────────────────────


@mcp.tool
def get_netradio_status() -> dict:
    """Return net radio / streaming now-playing info."""
    with _client() as c:
        return c.get_netradio_status().model_dump()


@mcp.tool
def play_netradio_url(
    url: Annotated[str, Field(description="Streaming URL (http/https)")],
    title: Annotated[str, Field(description="Display title for the stream")] = "",
) -> str:
    """Start playing a streaming URL via UPnP."""
    with _client() as c:
        c.play_netradio_url(url, title)
    label = title or url
    return f"Net Radio: playing '{label}'"


@mcp.tool
def pause_netradio() -> str:
    """Pause net radio / streaming playback."""
    with _client() as c:
        c.pause_netradio_url()
    return "Net Radio: paused"


@mcp.tool
def stop_netradio() -> str:
    """Stop net radio / streaming playback."""
    with _client() as c:
        c.stop_netradio_url()
    return "Net Radio: stopped"


# ── Entry point ───────────────────────────────────────────────────────────────


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
