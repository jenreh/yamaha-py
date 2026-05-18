# ruff: noqa: S314
"""Tests that HTTP XML adapter generates correct XML payloads."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import httpx
import pytest
import respx

from yamactl.protocols.ync_http import YncHttpProtocol

BASE_URL = "http://192.168.1.100:80/YamahaRemoteControl/ctrl"
OK_RESPONSE = b'<YAMAHA_AV rsp="PUT" RC="0"></YAMAHA_AV>'


def _load_fixture(name: str) -> bytes:
    from pathlib import Path  # noqa: PLC0415

    path = Path(__file__).parent.parent / "protocol_fixtures" / name
    return path.read_bytes()


@pytest.fixture
def proto() -> YncHttpProtocol:
    return YncHttpProtocol(host="192.168.1.100", port=80, timeout=1.0)


class TestPowerXml:
    @respx.mock
    def test_power_on_sends_correct_xml(self, proto) -> None:
        route = respx.post(BASE_URL).mock(
            return_value=httpx.Response(200, content=OK_RESPONSE)
        )
        with proto:
            proto.set_power("on")
        body = route.calls[0].request.content.decode()
        root = ET.fromstring(body)
        assert root.get("cmd") == "PUT"
        el = root.find(".//Power_Control/Power")
        assert el is not None
        assert el.text == "On"

    @respx.mock
    def test_power_standby_sends_correct_xml(self, proto) -> None:
        route = respx.post(BASE_URL).mock(
            return_value=httpx.Response(200, content=OK_RESPONSE)
        )
        with proto:
            proto.set_power("standby")
        body = route.calls[0].request.content.decode()
        root = ET.fromstring(body)
        el = root.find(".//Power_Control/Power")
        assert el is not None
        assert el.text == "Standby"


class TestMuteXml:
    @respx.mock
    def test_mute_on(self, proto) -> None:
        route = respx.post(BASE_URL).mock(
            return_value=httpx.Response(200, content=OK_RESPONSE)
        )
        with proto:
            proto.set_mute(True)
        body = route.calls[0].request.content.decode()
        root = ET.fromstring(body)
        el = root.find(".//Volume/Mute")
        assert el is not None
        assert el.text == "On"

    @respx.mock
    def test_mute_off(self, proto) -> None:
        route = respx.post(BASE_URL).mock(
            return_value=httpx.Response(200, content=OK_RESPONSE)
        )
        with proto:
            proto.set_mute(False)
        body = route.calls[0].request.content.decode()
        root = ET.fromstring(body)
        el = root.find(".//Volume/Mute")
        assert el.text == "Off"


class TestVolumeXml:
    @respx.mock
    def test_set_volume_encodes_correctly(self, proto) -> None:
        route = respx.post(BASE_URL).mock(
            return_value=httpx.Response(200, content=OK_RESPONSE)
        )
        with proto:
            proto.set_volume_db(-45.0)
        body = route.calls[0].request.content.decode()
        root = ET.fromstring(body)
        val = root.find(".//Volume/Lvl/Val")
        assert val is not None
        assert val.text == "-450"

    @respx.mock
    def test_set_volume_positive(self, proto) -> None:
        route = respx.post(BASE_URL).mock(
            return_value=httpx.Response(200, content=OK_RESPONSE)
        )
        with proto:
            proto.set_volume_db(5.5)
        body = route.calls[0].request.content.decode()
        root = ET.fromstring(body)
        val = root.find(".//Volume/Lvl/Val")
        assert val.text == "55"

    @respx.mock
    def test_get_volume_uses_get_cmd(self, proto) -> None:
        vol_xml = _load_fixture("volume_response.xml")
        route = respx.post(BASE_URL).mock(
            return_value=httpx.Response(200, content=vol_xml)
        )
        with proto:
            proto.get_volume_db()
        body = route.calls[0].request.content.decode()
        root = ET.fromstring(body)
        assert root.get("cmd") == "GET"


class TestInputXml:
    @respx.mock
    def test_set_input(self, proto) -> None:
        route = respx.post(BASE_URL).mock(
            return_value=httpx.Response(200, content=OK_RESPONSE)
        )
        with proto:
            proto.set_input("HDMI2")
        body = route.calls[0].request.content.decode()
        root = ET.fromstring(body)
        el = root.find(".//Input/Input_Sel")
        assert el is not None
        assert el.text == "HDMI2"


class TestSceneXml:
    @respx.mock
    def test_load_scene_3(self, proto) -> None:
        route = respx.post(BASE_URL).mock(
            return_value=httpx.Response(200, content=OK_RESPONSE)
        )
        with proto:
            proto.load_scene(3)
        body = route.calls[0].request.content.decode()
        root = ET.fromstring(body)
        el = root.find(".//Scene/Scene_Load")
        assert el is not None
        assert el.text == "Scene 3"


class TestSoundXml:
    @respx.mock
    def test_set_dsp_mode(self, proto) -> None:
        route = respx.post(BASE_URL).mock(
            return_value=httpx.Response(200, content=OK_RESPONSE)
        )
        with proto:
            proto.set_dsp_mode("7ch Surround")
        body = route.calls[0].request.content.decode()
        root = ET.fromstring(body)
        el = root.find(".//Surround/Program_Sel/Current/Sound_Program")
        assert el is not None
        assert el.text == "7ch Surround"

    @respx.mock
    def test_set_straight_on(self, proto) -> None:
        route = respx.post(BASE_URL).mock(
            return_value=httpx.Response(200, content=OK_RESPONSE)
        )
        with proto:
            proto.set_straight(True)
        body = route.calls[0].request.content.decode()
        root = ET.fromstring(body)
        el = root.find(".//Surround/Straight")
        assert el.text == "On"

    @respx.mock
    def test_set_sleep_60(self, proto) -> None:
        route = respx.post(BASE_URL).mock(
            return_value=httpx.Response(200, content=OK_RESPONSE)
        )
        with proto:
            proto.set_sleep(60)
        body = route.calls[0].request.content.decode()
        root = ET.fromstring(body)
        el = root.find(".//Power_Control/Sleep")
        assert el.text == "60"

    @respx.mock
    def test_set_sleep_off(self, proto) -> None:
        route = respx.post(BASE_URL).mock(
            return_value=httpx.Response(200, content=OK_RESPONSE)
        )
        with proto:
            proto.set_sleep(None)
        body = route.calls[0].request.content.decode()
        root = ET.fromstring(body)
        el = root.find(".//Power_Control/Sleep")
        assert el.text == "Off"


class TestZone2Xml:
    @respx.mock
    def test_zone2_tag_in_xml(self) -> None:
        proto = YncHttpProtocol(host="192.168.1.100", zone="zone2", timeout=1.0)
        route = respx.post(BASE_URL).mock(
            return_value=httpx.Response(200, content=OK_RESPONSE)
        )
        with proto:
            proto.set_mute(True)
        body = route.calls[0].request.content.decode()
        assert "Zone_2" in body
        assert "Main_Zone" not in body
