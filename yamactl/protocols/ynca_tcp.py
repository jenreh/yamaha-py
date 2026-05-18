"""YNCA TCP adapter — primary protocol via the `ynca` library."""

from __future__ import annotations

from yamactl.core.errors import (
    ProtocolUnsupported,
    ReceiverBusy,
    ReceiverUnavailable,
)
from yamactl.core.models import PowerState, ReceiverStatus, ZoneName

# ynca library imports are deferred to __enter__ so that import errors surface
# with a clear message if the package is somehow missing.


def _parse_sleep(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


class YncaTcpProtocol:
    def __init__(
        self,
        host: str,
        port: int = 50000,
        zone: ZoneName = "main",
        timeout: float = 3.0,
    ) -> None:
        self._url = f"socket://{host}:{port}"
        self._host = host
        self._zone = zone
        self._timeout = timeout
        self._api = None

    def __enter__(self) -> "YncaTcpProtocol":
        try:
            import ynca  # noqa: PLC0415

            self._api = ynca.YncaApi(self._url)
            self._api.initialize()
        except ImportError as exc:
            raise ReceiverUnavailable(
                "ynca package not installed. Run: pip install ynca"
            ) from exc
        except Exception as exc:
            msg = str(exc).lower()
            if "already" in msg or "busy" in msg or "connection refused" in msg:
                raise ReceiverBusy(
                    f"Receiver at {self._host} already has an active YNCA connection. "
                    "Close other clients or switch to --protocol http_xml."
                ) from exc
            raise ReceiverUnavailable(
                f"Cannot connect to receiver at {self._host}:50000 via YNCA: {exc}"
            ) from exc
        return self

    def __exit__(self, *args: object) -> None:
        if self._api is not None:
            try:
                import time  # noqa: PLC0415
                time.sleep(0.5)  # ynca queues commands on background thread; wait before close
                self._api.close()
            except Exception:
                pass
            self._api = None

    def _assert_connected(self) -> None:
        if self._api is None:
            raise RuntimeError("YncaTcpProtocol used outside context manager")

    @property
    def _zone_obj(self):  # type: ignore[no-untyped-def]
        self._assert_connected()
        return self._api.main if self._zone == "main" else self._api.zone2  # type: ignore[union-attr]

    # ── power ────────────────────────────────────────────────────────────────

    def set_power(self, state: PowerState) -> None:
        from ynca.enums import Pwr  # noqa: PLC0415

        self._zone_obj.pwr = Pwr.ON if state == "on" else Pwr.STANDBY

    # ── mute ─────────────────────────────────────────────────────────────────

    def get_mute(self) -> bool:
        from ynca.enums import Mute  # noqa: PLC0415

        return self._zone_obj.mute == Mute.ON

    def set_mute(self, enabled: bool) -> None:
        from ynca.enums import Mute  # noqa: PLC0415

        self._zone_obj.mute = Mute.ON if enabled else Mute.OFF

    # ── volume ───────────────────────────────────────────────────────────────

    def get_volume_db(self) -> float:
        return float(self._zone_obj.vol)

    def set_volume_db(self, value: float) -> None:
        self._zone_obj.vol = value

    def volume_up(self, steps: int = 1) -> None:
        self._zone_obj.vol_up(steps)

    def volume_down(self, steps: int = 1) -> None:
        self._zone_obj.vol_down(steps)

    # ── input ────────────────────────────────────────────────────────────────

    def set_input(self, source: str) -> None:
        self._zone_obj.inp = source

    def list_inputs(self) -> list[str]:
        self._assert_connected()
        inpname = getattr(self._api.sys, "inpname", None)  # type: ignore[union-attr]
        if inpname:
            return list(inpname)
        # fallback: return inputs from zone
        return []

    # ── scene ────────────────────────────────────────────────────────────────

    def load_scene(self, scene: int) -> None:
        # ynca scene attribute may vary by library version
        if hasattr(self._zone_obj, "scene"):
            self._zone_obj.scene = scene
        else:
            raise ProtocolUnsupported(
                "Scene loading not supported in this ynca library version. "
                "Use --protocol http_xml instead."
            )

    # ── sound ────────────────────────────────────────────────────────────────

    def set_dsp_mode(self, mode: str) -> None:
        self._zone_obj.soundprg = mode

    def set_straight(self, enabled: bool) -> None:
        from ynca.enums import Straight  # noqa: PLC0415

        self._zone_obj.straight = Straight.ON if enabled else Straight.OFF

    def set_direct(self, enabled: bool) -> None:
        # Direct mode attribute name varies; try common names
        zone = self._zone_obj
        if hasattr(zone, "puredirmode"):
            zone.puredirmode = "On" if enabled else "Off"
        elif hasattr(zone, "direct"):
            zone.direct = "On" if enabled else "Off"
        else:
            raise ProtocolUnsupported(
                "Direct mode not found in this ynca library version. "
                "Use --protocol http_xml instead."
            )

    def set_sleep(self, minutes: int | None) -> None:
        self._zone_obj.sleep = minutes if minutes is not None else 0

    # ── status ───────────────────────────────────────────────────────────────

    def get_status(self) -> ReceiverStatus:
        from ynca.enums import Pwr  # noqa: PLC0415

        self._assert_connected()
        zone = self._zone_obj
        sys = self._api.sys  # type: ignore[union-attr]

        pwr = getattr(zone, "pwr", None)
        vol = getattr(zone, "vol", None)
        mute = getattr(zone, "mute", None)
        inp = getattr(zone, "inp", None)
        soundprg = getattr(zone, "soundprg", None)
        sleep = getattr(zone, "sleep", None)
        modelname = getattr(sys, "modelname", None)

        return ReceiverStatus(
            host=self._host,
            model=str(modelname) if modelname else None,
            power="on" if pwr == Pwr.ON else "standby",
            input=str(inp) if inp else None,
            mute=str(mute).upper() == "ON" if mute is not None else None,
            volume_db=float(vol) if vol is not None else None,
            dsp_mode=str(soundprg) if soundprg else None,
            sleep_minutes=_parse_sleep(sleep),
        )

    # ── raw ──────────────────────────────────────────────────────────────────

    def send_raw_ynca(self, command: str) -> str:
        # Access the underlying connection to send raw YNCA strings
        self._assert_connected()
        if hasattr(self._api, "_connection"):
            conn = self._api._connection  # type: ignore[union-attr]
            conn.put(command)
            # Raw response retrieval depends on ynca internals; best-effort
            return f"Sent: {command}"
        raise ProtocolUnsupported(
            "Direct raw YNCA send not available in this ynca library version."
        )

    def send_raw_xml(self, xml: str) -> str:
        raise ProtocolUnsupported(
            "Raw XML not supported on ynca adapter. Use --protocol http_xml."
        )
