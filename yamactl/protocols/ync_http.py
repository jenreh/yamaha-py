"""HTTP XML adapter — fallback protocol via httpx + stdlib XML."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import httpx

from yamactl.core.errors import (
    CommandTimeout,
    ProtocolUnsupported,
    ReceiverUnavailable,
    UnexpectedResponse,
)
from yamactl.core.models import (
    VOLUME_MAX,
    VOLUME_MIN,
    VOLUME_STEP,
    NetRadioListEntry,
    NetRadioListInfo,
    NetRadioStatus,
    PowerState,
    ReceiverStatus,
    TunerStatus,
    ZoneName,
)

_ZONE_TAG: dict[ZoneName, str] = {
    "main": "Main_Zone",
    "zone2": "Zone_2",
}

# Known RX-V475 inputs (fallback when desc.xml parse fails)
_RXV475_INPUTS = [
    "HDMI1",
    "HDMI2",
    "HDMI3",
    "HDMI4",
    "AV1",
    "AV2",
    "AV3",
    "V-AUX",
    "AUDIO1",
    "AUDIO2",
    "TUNER",
    "USB",
    "NET RADIO",
    "SERVER",
    "AirPlay",
]


class YncHttpProtocol:
    def __init__(
        self,
        host: str,
        port: int = 80,
        zone: ZoneName = "main",
        timeout: float = 3.0,
    ) -> None:
        self._ctrl_url = f"http://{host}:{port}/YamahaRemoteControl/ctrl"
        self._desc_url = f"http://{host}:{port}/YamahaRemoteControl/desc.xml"
        self._zone_tag = _ZONE_TAG[zone]
        self._host = host
        self._timeout = timeout
        self._client = httpx.Client(timeout=timeout)

    def __enter__(self) -> YncHttpProtocol:
        return self

    def __exit__(self, *args: object) -> None:
        self._client.close()

    def _post(self, xml: str) -> ET.Element:
        try:
            response = self._client.post(
                self._ctrl_url,
                content=xml.encode("utf-8"),
                headers={"Content-Type": "text/xml"},
            )
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise CommandTimeout(f"Receiver at {self._host} timed out: {exc}") from exc
        except httpx.ConnectError as exc:
            raise ReceiverUnavailable(
                f"Cannot connect to receiver at {self._host}: {exc}"
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise UnexpectedResponse(
                f"HTTP {exc.response.status_code} from receiver"
            ) from exc
        try:
            root = ET.fromstring(response.content)  # noqa: S314
        except ET.ParseError as exc:
            raise UnexpectedResponse(f"Invalid XML from receiver: {exc}") from exc
        rc = root.get("RC", "0")
        if rc != "0":
            raise UnexpectedResponse(f"Receiver error RC={rc}")
        return root

    def _put(self, inner_xml: str) -> None:
        self._post(
            f'<YAMAHA_AV cmd="PUT">'
            f"<{self._zone_tag}>{inner_xml}</{self._zone_tag}>"
            f"</YAMAHA_AV>"
        )

    def _get(self, inner_xml: str) -> ET.Element:
        return self._post(
            f'<YAMAHA_AV cmd="GET">'
            f"<{self._zone_tag}>{inner_xml}</{self._zone_tag}>"
            f"</YAMAHA_AV>"
        )

    def _find_text(self, root: ET.Element, path: str) -> str | None:
        el = root.find(f".//{self._zone_tag}/{path}")
        return el.text if el is not None else None

    # ── power ────────────────────────────────────────────────────────────────

    def set_power(self, state: PowerState) -> None:
        value = "On" if state == "on" else "Standby"
        self._put(f"<Power_Control><Power>{value}</Power></Power_Control>")

    # ── mute ─────────────────────────────────────────────────────────────────

    def get_mute(self) -> bool:
        root = self._get("<Volume><Mute>GetParam</Mute></Volume>")
        return self._find_text(root, "Volume/Mute") == "On"

    def set_mute(self, enabled: bool) -> None:
        value = "On" if enabled else "Off"
        self._put(f"<Volume><Mute>{value}</Mute></Volume>")

    # ── volume ───────────────────────────────────────────────────────────────

    def get_volume_db(self) -> float:
        root = self._get("<Volume><Lvl><Val>GetParam</Val></Lvl></Volume>")
        raw = self._find_text(root, "Volume/Lvl/Val")
        if raw is None:
            raise UnexpectedResponse("No volume value in receiver response")
        return int(raw) / 10.0

    def set_volume_db(self, value: float) -> None:
        raw = str(int(value * 10))
        self._put(
            f"<Volume><Lvl><Val>{raw}</Val><Exp>1</Exp><Unit>dB</Unit></Lvl></Volume>"
        )

    def volume_up(self, steps: int = 1) -> None:
        current = self.get_volume_db()
        self.set_volume_db(min(current + steps * VOLUME_STEP, VOLUME_MAX))

    def volume_down(self, steps: int = 1) -> None:
        current = self.get_volume_db()
        self.set_volume_db(max(current - steps * VOLUME_STEP, VOLUME_MIN))

    # ── input ────────────────────────────────────────────────────────────────

    def set_input(self, source: str) -> None:
        self._put(f"<Input><Input_Sel>{source}</Input_Sel></Input>")

    def list_inputs(self) -> list[str]:
        try:
            response = self._client.get(self._desc_url)
            response.raise_for_status()
            root = ET.fromstring(response.text)  # noqa: S314
            # Try to extract input list from desc.xml
            inputs: list[str] = []
            for el in root.iter("Input_Sel_Item_Info"):
                name = el.find("Param")
                if name is not None and name.text:
                    inputs.append(name.text)
            if inputs:
                return inputs
        except Exception:  # noqa: S110
            pass
        return _RXV475_INPUTS

    # ── scene ────────────────────────────────────────────────────────────────

    def load_scene(self, scene: int) -> None:
        self._put(f"<Scene><Scene_Load>Scene {scene}</Scene_Load></Scene>")

    # ── sound ────────────────────────────────────────────────────────────────

    def set_dsp_mode(self, mode: str) -> None:
        self._put(
            f"<Surround><Program_Sel><Current>"
            f"<Sound_Program>{mode}</Sound_Program>"
            f"</Current></Program_Sel></Surround>"
        )

    def set_straight(self, enabled: bool) -> None:
        value = "On" if enabled else "Off"
        self._put(f"<Surround><Straight>{value}</Straight></Surround>")

    def set_direct(self, enabled: bool) -> None:
        value = "On" if enabled else "Off"
        self._put(f"<Surround><Direct>{value}</Direct></Surround>")

    def set_sleep(self, minutes: int | None) -> None:
        value = str(minutes) if minutes is not None else "Off"
        self._put(f"<Power_Control><Sleep>{value}</Sleep></Power_Control>")

    # ── status ───────────────────────────────────────────────────────────────

    def get_status(self) -> ReceiverStatus:
        root = self._get("<Basic_Status>GetParam</Basic_Status>")

        # Basic_Status wraps all fields — include it in the path
        def text(path: str) -> str | None:
            return self._find_text(root, f"Basic_Status/{path}")

        vol_raw = text("Volume/Lvl/Val")
        sleep_raw = text("Power_Control/Sleep")

        return ReceiverStatus(
            host=self._host,
            power="on" if text("Power_Control/Power") == "On" else "standby",
            input=text("Input/Input_Sel"),
            mute=text("Volume/Mute") == "On",
            volume_db=int(vol_raw) / 10.0
            if vol_raw and vol_raw.lstrip("-").isdigit()
            else None,
            dsp_mode=text("Surround/Program_Sel/Current/Sound_Program"),
            sleep_minutes=int(sleep_raw) if sleep_raw and sleep_raw.isdigit() else None,
        )

    # ── tuner ────────────────────────────────────────────────────────────────

    def _tuner_put(self, inner_xml: str) -> None:
        self._post(f'<YAMAHA_AV cmd="PUT"><Tuner>{inner_xml}</Tuner></YAMAHA_AV>')

    def _tuner_get(self, inner_xml: str) -> ET.Element:
        return self._post(
            f'<YAMAHA_AV cmd="GET"><Tuner>{inner_xml}</Tuner></YAMAHA_AV>'
        )

    def get_tuner_status(self) -> TunerStatus:
        root = self._tuner_get("<Play_Info>GetParam</Play_Info>")

        def t(path: str) -> str | None:
            el = root.find(f".//Tuner/Play_Info/{path}")
            return el.text if el is not None else None

        fm_raw = t("Tuning/Freq/FM/Val")
        am_raw = t("Tuning/Freq/AM/Val")
        tuned_raw = t("Signal_Info/Tuned")
        return TunerStatus(
            band=t("Tuning/Band"),
            fm_freq_mhz=int(fm_raw) / 100.0
            if fm_raw and fm_raw.lstrip("-").isdigit()
            else None,
            am_freq_khz=int(am_raw) if am_raw and am_raw.isdigit() else None,
            preset=t("Preset/Preset_Sel"),
            fm_mode=t("FM_Mode"),
            rds_station=t("Meta_Info/Program_Service") or None,
            tuned=tuned_raw == "Assert" if tuned_raw else None,
        )

    def set_tuner_band(self, band: str) -> None:
        # RX-V series: band lives inside Play_Control/Tuning on some models,
        # directly in Play_Control on others — try the nested form first.
        self._tuner_put(
            f"<Play_Control><Tuning><Band>{band}</Band></Tuning></Play_Control>"
        )

    def set_tuner_fm_freq(self, mhz: float) -> None:
        val = str(round(mhz * 100))
        self._tuner_put(
            f"<Play_Control><Tuning><Freq><FM>"
            f"<Val>{val}</Val><Exp>2</Exp><Unit>MHz</Unit>"
            f"</FM></Freq></Tuning></Play_Control>"
        )

    def set_tuner_am_freq(self, khz: int) -> None:
        self._tuner_put(
            f"<Play_Control><Tuning><Freq><AM>"
            f"<Val>{khz}</Val><Exp>0</Exp><Unit>kHz</Unit>"
            f"</AM></Freq></Tuning></Play_Control>"
        )

    def set_tuner_preset(self, preset_num: int) -> None:
        self._tuner_put(
            f"<Play_Control><Preset><Preset_Sel>{preset_num}</Preset_Sel></Preset></Play_Control>"
        )

    # ── net radio ────────────────────────────────────────────────────────────

    def _netradio_put(self, inner_xml: str) -> None:
        self._post(
            f'<YAMAHA_AV cmd="PUT"><NET_RADIO>{inner_xml}</NET_RADIO></YAMAHA_AV>'
        )

    def _netradio_get(self, inner_xml: str) -> ET.Element:
        return self._post(
            f'<YAMAHA_AV cmd="GET"><NET_RADIO>{inner_xml}</NET_RADIO></YAMAHA_AV>'
        )

    def get_netradio_status(self) -> NetRadioStatus:
        root = self._netradio_get("<Play_Info>GetParam</Play_Info>")

        def t(path: str) -> str | None:
            el = root.find(f".//NET_RADIO/Play_Info/{path}")
            return el.text if el is not None else None

        avail = t("Feature_Availability")
        return NetRadioStatus(
            available=avail == "Ready" if avail else None,
            playback=t("Playback_Info"),
            station=t("Meta_Info/Station") or None,
            song=t("Meta_Info/Song") or None,
            album=t("Meta_Info/Album") or None,
            elapsed_time=t("Play_Time") or None,
        )

    def set_netradio_playback(self, action: str) -> None:
        self._netradio_put(
            f"<Play_Control><Playback>{action}</Playback></Play_Control>"
        )

    def set_netradio_preset(self, preset_num: int) -> None:
        self._netradio_put(
            f"<Play_Control><Preset><Preset_Sel>{preset_num}</Preset_Sel></Preset></Play_Control>"
        )

    def get_netradio_list(self) -> NetRadioListInfo:
        root = self._netradio_get("<List_Info>GetParam</List_Info>")

        def t(path: str) -> str | None:
            el = root.find(f".//NET_RADIO/List_Info/{path}")
            return el.text if el is not None else None

        entries: list[NetRadioListEntry] = []
        for i in range(1, 9):
            txt = t(f"Current_List/Line_{i}/Txt")
            attr = t(f"Current_List/Line_{i}/Attribute") or ""
            if txt is not None:
                entries.append(NetRadioListEntry(line=i, text=txt, attribute=attr))

        layer_raw = t("Menu_Layer")
        cur_raw = t("Cursor_Position/Current_Line")
        max_raw = t("Cursor_Position/Max_Line")
        return NetRadioListInfo(
            layer=int(layer_raw) if layer_raw and layer_raw.isdigit() else None,
            layer_name=t("Menu_Name"),
            current_line=int(cur_raw) if cur_raw and cur_raw.isdigit() else None,
            max_line=int(max_raw) if max_raw and max_raw.isdigit() else None,
            entries=entries,
        )

    def netradio_select(self, line: int) -> None:
        self._netradio_put(
            f"<List_Control><Direct_Sel>Line_{line}</Direct_Sel></List_Control>"
        )

    def netradio_back(self) -> None:
        self._netradio_put("<List_Control><Return>Return</Return></List_Control>")

    def netradio_cursor(self, direction: str) -> None:
        self._netradio_put(f"<List_Control><Cursor>{direction}</Cursor></List_Control>")

    def get_server_status(self) -> NetRadioStatus:
        root = self._post(
            '<YAMAHA_AV cmd="GET"><SERVER><Play_Info>GetParam</Play_Info></SERVER></YAMAHA_AV>'
        )

        def t(path: str) -> str | None:
            el = root.find(f".//SERVER/Play_Info/{path}")
            return el.text if el is not None else None

        avail = t("Feature_Availability")
        return NetRadioStatus(
            available=avail == "Ready" if avail else None,
            playback=t("Playback_Info"),
            station=t("Meta_Info/Station") or None,
            song=t("Meta_Info/Song") or None,
            album=t("Meta_Info/Album") or None,
            elapsed_time=t("Play_Time") or None,
        )

    def play_netradio_url(self, url: str, title: str) -> None:
        import time  # noqa: PLC0415

        from yamactl.protocols.upnp import play_url  # noqa: PLC0415

        self.set_input("SERVER")
        time.sleep(1.5)
        play_url(self._host, url, title, timeout=self._timeout + 5.0)

    def pause_netradio_url(self) -> None:
        from yamactl.protocols.upnp import pause_url  # noqa: PLC0415

        pause_url(self._host, timeout=self._timeout + 5.0)

    def stop_netradio_url(self) -> None:
        from yamactl.protocols.upnp import stop_url  # noqa: PLC0415

        stop_url(self._host, timeout=self._timeout + 5.0)

    # ── raw ──────────────────────────────────────────────────────────────────

    def send_raw_xml(self, xml: str) -> str:
        root = self._post(xml)
        return ET.tostring(root, encoding="unicode")

    def send_raw_ynca(self, command: str) -> str:  # noqa: ARG002
        raise ProtocolUnsupported(
            "Raw YNCA not supported on http_xml adapter. Use --profile with protocol=ynca."
        )
