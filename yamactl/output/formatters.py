"""Convert domain models to plain text / dict for output.

All output string construction lives here. CLI handlers call these functions
rather than formatting strings inline.
"""

from __future__ import annotations

from yamactl.core.models import DiscoveryCandidate, ReceiverStatus


def status_to_dict(s: ReceiverStatus) -> dict:
    return s.model_dump(exclude={"raw"})


def status_to_plain(s: ReceiverStatus) -> str:
    vol = f"{s.volume_db:+.1f} dB" if s.volume_db is not None else "unknown"
    mute = "muted" if s.mute else "unmuted"
    parts = [
        s.model or "Yamaha",
        f"power={s.power or 'unknown'}",
        f"input={s.input or 'unknown'}",
        f"volume={vol}",
        mute,
    ]
    if s.dsp_mode:
        parts.append(f"dsp={s.dsp_mode}")
    if s.sleep_minutes:
        parts.append(f"sleep={s.sleep_minutes}min")
    return "  ".join(parts)


def candidates_to_plain(candidates: list[DiscoveryCandidate]) -> str:
    lines = []
    for c in candidates:
        ynca = "YNCA" if c.ynca_available else "    "
        http = "HTTP" if c.http_available else "    "
        model = c.model or "?"
        lines.append(
            f"{c.host:<18} {ynca} {http}  confidence={c.confidence}  model={model}"
        )
    return "\n".join(lines)


# ── simple confirmation lines ─────────────────────────────────────────────────


def power_confirmation(state: str) -> str:
    return f"Power: {state}"


def mute_confirmation(enabled: bool) -> str:
    return f"Mute: {'on' if enabled else 'off'}"


def volume_confirmation(db: float) -> str:
    return f"Volume: {db:+.1f} dB"


def volume_step_confirmation(direction: str, steps: int) -> str:
    return f"Volume: {direction} {steps} step{'s' if steps != 1 else ''}"


def input_confirmation(source: str) -> str:
    return f"Input: {source}"


def dsp_mode_confirmation(mode: str) -> str:
    return f"DSP mode: {mode}"


def straight_confirmation(enabled: bool) -> str:
    return f"Straight: {'on' if enabled else 'off'}"


def direct_confirmation(enabled: bool) -> str:
    return f"Direct: {'on' if enabled else 'off'}"


def sleep_confirmation(value: str) -> str:
    return f"Sleep: {value}"


def scene_confirmation(scene: int) -> str:
    return f"Scene: loaded {scene}"
