"""YNCA TCP adapter — primary protocol via the `ynca` library."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ynca import YncaApi as _YncaApi

from yamactl.core.errors import (
    ProtocolUnsupported,
    ReceiverBusy,
    ReceiverUnavailable,
)
from yamactl.core.models import (
    NetRadioListEntry,
    NetRadioListInfo,
    NetRadioStatus,
    PowerState,
    ReceiverStatus,
    TunerStatus,
    ZoneName,
)

# ynca library imports are deferred to __enter__ so that import errors surface
# with a clear message if the package is somehow missing.


def _parse_sleep(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(str(value))
    except ValueError, TypeError:
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
        self._api: _YncaApi | None = None

    def __enter__(self) -> YncaTcpProtocol:
        try:
            import ynca  # noqa: PLC0415

            api: _YncaApi = ynca.YncaApi(self._url)
            api.initialize()
            self._api = api
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

                time.sleep(
                    0.5
                )  # ynca queues commands on background thread; wait before close
                self._api.close()
            except Exception:  # noqa: S110
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

        return bool(self._zone_obj.mute == Mute.ON)

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
        inpname = getattr(self._api.sys, "inpname", None)  # type: ignore[union-attr, attr-defined]
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
        sys = self._api.sys  # type: ignore[union-attr, attr-defined]

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

    # ── tuner ────────────────────────────────────────────────────────────────

    @property
    def _tun(self):  # type: ignore[no-untyped-def]
        self._assert_connected()
        return self._api.tun  # type: ignore[union-attr]

    def get_tuner_status(self) -> TunerStatus:
        tun = self._tun
        band = getattr(tun, "band", None)
        fmfreq = getattr(tun, "fmfreq", None)
        amfreq = getattr(tun, "amfreq", None)
        preset = getattr(tun, "preset", None)
        fmmode = getattr(tun, "fmmode", None)
        rds = getattr(tun, "rdsprgservice", None)
        tuned = getattr(tun, "tuned", None)
        return TunerStatus(
            band=str(band) if band is not None else None,
            fm_freq_mhz=int(fmfreq) / 100.0 if fmfreq is not None else None,
            am_freq_khz=int(amfreq) if amfreq is not None else None,
            preset=str(preset) if preset is not None else None,
            fm_mode=str(fmmode) if fmmode is not None else None,
            rds_station=str(rds) if rds is not None else None,
            tuned=str(tuned).upper() == "TUNED" if tuned is not None else None,
        )

    def set_tuner_band(self, band: str) -> None:
        self._tun.band = band

    def set_tuner_fm_freq(self, mhz: float) -> None:
        self._tun.fmfreq = round(mhz * 100)

    def set_tuner_am_freq(self, khz: int) -> None:
        self._tun.amfreq = khz

    def set_tuner_preset(self, preset_num: int) -> None:
        self._tun.preset = preset_num

    # ── net radio ────────────────────────────────────────────────────────────

    @property
    def _netradio(self):  # type: ignore[no-untyped-def]
        self._assert_connected()
        return self._api.netradio  # type: ignore[union-attr]

    def get_netradio_status(self) -> NetRadioStatus:
        nr = self._netradio
        avail = getattr(nr, "avail", None)
        playback = getattr(nr, "playback", None)
        station = getattr(nr, "station", None)
        song = getattr(nr, "song", None)
        album = getattr(nr, "album", None)
        elapsed = getattr(nr, "elapsedtime", None)
        return NetRadioStatus(
            available=str(avail).upper() == "READY" if avail is not None else None,
            playback=str(playback) if playback is not None else None,
            station=str(station) if station else None,
            song=str(song) if song else None,
            album=str(album) if album else None,
            elapsed_time=str(elapsed) if elapsed is not None else None,
        )

    def set_netradio_playback(self, action: str) -> None:
        self._netradio.playback = action

    def set_netradio_preset(self, preset_num: int) -> None:
        self._netradio.preset = preset_num

    def get_netradio_list(self) -> NetRadioListInfo:
        nr = self._netradio
        entries: list[NetRadioListEntry] = []
        for i in range(1, 9):
            txt = getattr(nr, f"line{i}txt", None)
            atrib = getattr(nr, f"line{i}atrib", None)
            if txt is not None:
                entries.append(
                    NetRadioListEntry(
                        line=i,
                        text=str(txt),
                        attribute=str(atrib) if atrib is not None else "",
                    )
                )
        listlayer = getattr(nr, "listlayer", None)
        listlayername = getattr(nr, "listlayername", None)
        currline = getattr(nr, "currline", None)
        maxline = getattr(nr, "maxline", None)
        return NetRadioListInfo(
            layer=int(listlayer) if listlayer is not None else None,
            layer_name=str(listlayername) if listlayername else None,
            current_line=int(currline) if currline is not None else None,
            max_line=int(maxline) if maxline is not None else None,
            entries=entries,
        )

    def netradio_select(self, line: int) -> None:
        nr = self._netradio
        if hasattr(nr, "listinfo"):
            nr.listinfo = f"SelectLine_{line}"
        else:
            raise ProtocolUnsupported(
                "Net Radio list selection not available in this ynca version."
            )

    def netradio_back(self) -> None:
        nr = self._netradio
        if hasattr(nr, "listinfo"):
            nr.listinfo = "ReturnToUpperLayer"
        else:
            raise ProtocolUnsupported(
                "Net Radio navigation not available in this ynca version."
            )

    def netradio_cursor(self, direction: str) -> None:
        nr = self._netradio
        ynca_val = "CurUp" if direction == "Up" else "CurDown"
        if hasattr(nr, "listinfo"):
            nr.listinfo = ynca_val
        else:
            raise ProtocolUnsupported(
                "Net Radio cursor not available in this ynca version."
            )

    def get_server_status(self) -> NetRadioStatus:
        self._assert_connected()
        srv = getattr(self._api, "server", None)
        if srv is None:
            return NetRadioStatus()
        avail = getattr(srv, "avail", None)
        playback = getattr(srv, "playback", None)
        station = getattr(srv, "station", None)
        song = getattr(srv, "song", None)
        album = getattr(srv, "album", None)
        elapsed = getattr(srv, "elapsedtime", None)
        return NetRadioStatus(
            available=str(avail).upper() == "READY" if avail is not None else None,
            playback=str(playback) if playback is not None else None,
            station=str(station) if station else None,
            song=str(song) if song else None,
            album=str(album) if album else None,
            elapsed_time=str(elapsed) if elapsed is not None else None,
        )

    def play_netradio_url(self, url: str, title: str) -> None:
        import time  # noqa: PLC0415

        from yamactl.protocols.upnp import play_url  # noqa: PLC0415

        self._zone_obj.inp = "SERVER"
        time.sleep(1.5)
        play_url(self._host, url, title, timeout=self._timeout + 5.0)

    def pause_netradio_url(self) -> None:
        from yamactl.protocols.upnp import pause_url  # noqa: PLC0415

        pause_url(self._host, timeout=self._timeout + 5.0)

    def stop_netradio_url(self) -> None:
        from yamactl.protocols.upnp import stop_url  # noqa: PLC0415

        stop_url(self._host, timeout=self._timeout + 5.0)

    # ── raw ──────────────────────────────────────────────────────────────────

    def send_raw_ynca(self, command: str) -> str:
        # Access the underlying connection to send raw YNCA strings
        self._assert_connected()
        if hasattr(self._api, "_connection"):
            conn = self._api._connection  # type: ignore[union-attr, attr-defined]  # noqa: SLF001
            conn.put(command)  # type: ignore[union-attr, call-arg]
            # Raw response retrieval depends on ynca internals; best-effort
            return f"Sent: {command}"
        raise ProtocolUnsupported(
            "Direct raw YNCA send not available in this ynca library version."
        )

    def send_raw_xml(self, xml: str) -> str:  # noqa: ARG002
        raise ProtocolUnsupported(
            "Raw XML not supported on ynca adapter. Use --protocol http_xml."
        )
