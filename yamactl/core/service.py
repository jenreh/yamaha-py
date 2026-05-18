"""Service layer — adapter selection, validation, retry logic."""

from __future__ import annotations

import time

from yamactl.core.config import load_profile
from yamactl.core.errors import CommandTimeout, ReceiverUnavailable, YamaCtlError
from yamactl.core.models import (
    PowerState,
    ReceiverConfig,
    ReceiverStatus,
    VOLUME_MAX,
    VOLUME_MIN,
    VOLUME_STEP,
    ZoneName,
)
from yamactl.core.ports import ReceiverProtocol


class ReceiverService:
    def __init__(self, config: ReceiverConfig) -> None:
        self._config = config

    @classmethod
    def from_profile(
        cls,
        profile: str | None = None,
        zone_override: ZoneName | None = None,
    ) -> "ReceiverService":
        cfg = load_profile(profile)
        if zone_override is not None:
            cfg = cfg.model_copy(update={"zone": zone_override})
        return cls(cfg)

    def _make_protocol(self) -> ReceiverProtocol:
        from yamactl.protocols.ync_http import YncHttpProtocol
        from yamactl.protocols.ynca_tcp import YncaTcpProtocol

        if self._config.protocol == "ynca":
            return YncaTcpProtocol(
                host=self._config.host,
                port=self._config.port or 50000,
                zone=self._config.zone,
                timeout=self._config.timeout_seconds,
            )
        return YncHttpProtocol(
            host=self._config.host,
            port=self._config.port or 80,
            zone=self._config.zone,
            timeout=self._config.timeout_seconds,
        )

    def _run(self, fn):  # type: ignore[no-untyped-def]
        """Execute fn(protocol) with retry logic."""
        last_exc: Exception | None = None
        for attempt in range(max(1, self._config.retries)):
            try:
                with self._make_protocol() as proto:
                    return fn(proto)
            except (CommandTimeout, ReceiverUnavailable) as exc:
                last_exc = exc
                if attempt < self._config.retries - 1:
                    time.sleep(0.5)
                continue
            except YamaCtlError:
                raise
        assert last_exc is not None
        raise last_exc

    @staticmethod
    def _clamp_volume(value: float) -> float:
        rounded = round(round(value / VOLUME_STEP) * VOLUME_STEP, 1)
        if rounded < VOLUME_MIN or rounded > VOLUME_MAX:
            raise ValueError(
                f"Volume {value} dB out of range [{VOLUME_MIN}, {VOLUME_MAX}]"
            )
        return rounded

    def get_status(self) -> ReceiverStatus:
        status = self._run(lambda p: p.get_status())
        status.profile = self._config.name
        return status

    def set_power(self, state: PowerState) -> None:
        self._run(lambda p: p.set_power(state))

    def get_mute(self) -> bool:
        return self._run(lambda p: p.get_mute())

    def set_mute(self, enabled: bool) -> None:
        self._run(lambda p: p.set_mute(enabled))

    def toggle_mute(self) -> bool:
        current = self.get_mute()
        new_state = not current
        self.set_mute(new_state)
        return new_state

    def get_volume_db(self) -> float:
        return self._run(lambda p: p.get_volume_db())

    def set_volume_db(self, value: float) -> None:
        clamped = self._clamp_volume(value)
        self._run(lambda p: p.set_volume_db(clamped))

    def volume_up(self, steps: int = 1) -> None:
        self._run(lambda p: p.volume_up(steps))

    def volume_down(self, steps: int = 1) -> None:
        self._run(lambda p: p.volume_down(steps))

    def set_input(self, source: str) -> None:
        self._run(lambda p: p.set_input(source))

    def list_inputs(self) -> list[str]:
        return self._run(lambda p: p.list_inputs())

    def load_scene(self, scene: int) -> None:
        if scene not in (1, 2, 3, 4):
            raise ValueError(f"Scene must be 1–4, got {scene}")
        self._run(lambda p: p.load_scene(scene))

    def set_dsp_mode(self, mode: str) -> None:
        self._run(lambda p: p.set_dsp_mode(mode))

    def set_straight(self, enabled: bool) -> None:
        self._run(lambda p: p.set_straight(enabled))

    def set_direct(self, enabled: bool) -> None:
        self._run(lambda p: p.set_direct(enabled))

    def set_sleep(self, minutes: int | None) -> None:
        self._run(lambda p: p.set_sleep(minutes))

    def send_raw_ynca(self, command: str) -> str:
        return self._run(lambda p: p.send_raw_ynca(command))

    def send_raw_xml(self, xml: str) -> str:
        return self._run(lambda p: p.send_raw_xml(xml))
