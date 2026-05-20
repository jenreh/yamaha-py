"""YamaCtlClient — public SDK for controlling a Yamaha AV receiver."""

from __future__ import annotations

from yamactl.core.config import load_profile
from yamactl.core.models import (
    NetRadioStatus,
    PowerState,
    ReceiverConfig,
    ReceiverStatus,
    TunerStatus,
    ZoneName,
)
from yamactl.core.service import ReceiverService


class YamaCtlClient:
    """Context-manager SDK wrapping :class:`ReceiverService`.

    Usage::

        with YamaCtlClient.from_profile() as client:
            status = client.get_status()
            client.set_volume(-30.0)
    """

    def __init__(self, config: ReceiverConfig) -> None:
        self._service = ReceiverService(config)

    @classmethod
    def from_profile(
        cls,
        profile: str | None = None,
        zone_override: ZoneName | None = None,
    ) -> YamaCtlClient:
        """Load YAML config and return a ready client."""
        cfg = load_profile(profile)
        if zone_override is not None:
            cfg = cfg.model_copy(update={"zone": zone_override})
        return cls(cfg)

    def __enter__(self) -> YamaCtlClient:
        return self

    def __exit__(self, *args: object) -> None:
        pass  # protocol connections are managed per-call inside _run()

    # ── Status ─────────────────────────────────────────────────────────────

    def get_status(self) -> ReceiverStatus:
        """Return full receiver status."""
        return self._service.get_status()

    # ── Power ──────────────────────────────────────────────────────────────

    def set_power(self, state: PowerState) -> None:
        """Set power state ('on' or 'standby')."""
        self._service.set_power(state)

    # ── Volume ─────────────────────────────────────────────────────────────

    def get_volume(self) -> float:
        """Return current volume in dB."""
        return self._service.get_volume_db()

    def set_volume(self, db: float) -> None:
        """Set volume in dB (clamped to [-80.5, 16.5] in 0.5 dB steps)."""
        self._service.set_volume_db(db)

    def volume_up(self, steps: int = 1) -> None:
        """Increase volume by N steps (1 step = 0.5 dB)."""
        self._service.volume_up(steps)

    def volume_down(self, steps: int = 1) -> None:
        """Decrease volume by N steps (1 step = 0.5 dB)."""
        self._service.volume_down(steps)

    # ── Mute ───────────────────────────────────────────────────────────────

    def get_mute(self) -> bool:
        """Return current mute state."""
        return self._service.get_mute()

    def set_mute(self, enabled: bool) -> None:
        """Enable or disable mute."""
        self._service.set_mute(enabled)

    def toggle_mute(self) -> bool:
        """Toggle mute; return the new state."""
        return self._service.toggle_mute()

    # ── Input ──────────────────────────────────────────────────────────────

    def list_inputs(self) -> list[str]:
        """Return available input source names."""
        return self._service.list_inputs()

    def set_input(self, source: str) -> None:
        """Select input source by name."""
        self._service.set_input(source)

    # ── Scene ──────────────────────────────────────────────────────────────

    def load_scene(self, number: int) -> None:
        """Load a scene preset (1–4)."""
        self._service.load_scene(number)

    # ── Sound ──────────────────────────────────────────────────────────────

    def set_dsp_mode(self, mode: str) -> None:
        """Set DSP / surround mode."""
        self._service.set_dsp_mode(mode)

    def set_straight(self, enabled: bool) -> None:
        """Enable or disable Straight mode (bypasses DSP)."""
        self._service.set_straight(enabled)

    def set_direct(self, enabled: bool) -> None:
        """Enable or disable Pure Direct mode."""
        self._service.set_direct(enabled)

    def set_sleep(self, minutes: int | None) -> None:
        """Set or clear the sleep timer (pass None to cancel)."""
        self._service.set_sleep(minutes)

    # ── Tuner ──────────────────────────────────────────────────────────────

    def get_tuner_status(self) -> TunerStatus:
        """Return current tuner status."""
        return self._service.get_tuner_status()

    def set_tuner_band(self, band: str) -> None:
        """Switch tuner band ('FM' or 'AM')."""
        self._service.set_tuner_band(band)

    def set_tuner_fm_freq(self, mhz: float) -> None:
        """Tune to FM frequency in MHz."""
        self._service.set_tuner_fm_freq(mhz)

    def set_tuner_am_freq(self, khz: int) -> None:
        """Tune to AM frequency in kHz."""
        self._service.set_tuner_am_freq(khz)

    def set_tuner_preset(self, num: int) -> None:
        """Recall a tuner preset by number."""
        self._service.set_tuner_preset(num)

    # ── Net Radio ──────────────────────────────────────────────────────────

    def get_netradio_status(self) -> NetRadioStatus:
        """Return current net radio / server playback status."""
        return self._service.get_netradio_status()

    def play_netradio_url(self, url: str, title: str = "") -> None:
        """Start playing a streaming URL."""
        self._service.play_netradio_url(url, title)

    def pause_netradio_url(self) -> None:
        """Pause net radio / server playback."""
        self._service.pause_netradio_url()

    def stop_netradio_url(self) -> None:
        """Stop net radio / server playback."""
        self._service.stop_netradio_url()

    def set_netradio_playback(self, action: str) -> None:
        """Send a playback action ('Play', 'Pause', 'Stop')."""
        self._service.set_netradio_playback(action)

    def set_netradio_preset(self, num: int) -> None:
        """Recall a net radio preset by number."""
        self._service.set_netradio_preset(num)

    # ── Raw (diagnostics) ──────────────────────────────────────────────────

    def send_raw_ynca(self, command: str) -> str:
        """Send a raw YNCA command and return the response."""
        return self._service.send_raw_ynca(command)

    def send_raw_xml(self, xml: str) -> str:
        """Send a raw XML envelope and return the XML response."""
        return self._service.send_raw_xml(xml)

    def get_server_status(self) -> NetRadioStatus:
        """Return server / USB playback status."""
        return self._service.get_server_status()
