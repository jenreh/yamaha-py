"""HTTP XML adapter — fallback protocol via httpx + stdlib XML."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

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
    PowerState,
    ReceiverStatus,
    ZoneName,
)

_ZONE_TAG: dict[ZoneName, str] = {
    "main": "Main_Zone",
    "zone2": "Zone_2",
}

# Known RX-V475 inputs (fallback when desc.xml parse fails)
_RXV475_INPUTS = [
    "HDMI1", "HDMI2", "HDMI3", "HDMI4",
    "AV1", "AV2", "AV3",
    "V-AUX", "AUDIO1", "AUDIO2",
    "TUNER", "USB", "NET RADIO", "SERVER", "AirPlay",
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
        self._client = httpx.Client(timeout=timeout)

    def __enter__(self) -> "YncHttpProtocol":
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
            root = ET.fromstring(response.text)
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
            f"<Volume>"
            f"<Lvl><Val>{raw}</Val><Exp>1</Exp><Unit>dB</Unit></Lvl>"
            f"</Volume>"
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
            root = ET.fromstring(response.text)
            # Try to extract input list from desc.xml
            inputs: list[str] = []
            for el in root.iter("Input_Sel_Item_Info"):
                name = el.find("Param")
                if name is not None and name.text:
                    inputs.append(name.text)
            if inputs:
                return inputs
        except Exception:
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
            volume_db=int(vol_raw) / 10.0 if vol_raw and vol_raw.lstrip("-").isdigit() else None,
            dsp_mode=text("Surround/Program_Sel/Current/Sound_Program"),
            sleep_minutes=int(sleep_raw) if sleep_raw and sleep_raw.isdigit() else None,
        )

    # ── raw ──────────────────────────────────────────────────────────────────

    def send_raw_xml(self, xml: str) -> str:
        root = self._post(xml)
        return ET.tostring(root, encoding="unicode")

    def send_raw_ynca(self, command: str) -> str:
        raise ProtocolUnsupported(
            "Raw YNCA not supported on http_xml adapter. Use --profile with protocol=ynca."
        )
