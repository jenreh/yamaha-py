"""Tests that HTTP XML adapter parses receiver responses correctly."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import respx

from yamactl.core.errors import CommandTimeout, ReceiverUnavailable, UnexpectedResponse
from yamactl.protocols.ync_http import YncHttpProtocol

BASE_URL = "http://192.168.1.100:80/YamahaRemoteControl/ctrl"
FIXTURES = Path(__file__).parent.parent / "protocol_fixtures"


def fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


@pytest.fixture
def proto() -> YncHttpProtocol:
    return YncHttpProtocol(host="192.168.1.100", port=80, timeout=1.0)


class TestStatusParsing:
    @respx.mock
    def test_parses_basic_status(self, proto) -> None:
        respx.post(BASE_URL).mock(
            return_value=httpx.Response(200, content=fixture("basic_status.xml"))
        )
        with proto:
            status = proto.get_status()
        assert status.power == "on"
        assert status.input == "HDMI1"
        assert status.mute is False
        assert status.volume_db == -45.0
        assert status.dsp_mode == "7ch Surround"

    @respx.mock
    def test_standby_power(self, proto) -> None:
        xml = b"""<YAMAHA_AV rsp="GET" RC="0">
          <Main_Zone><Basic_Status>
            <Power_Control><Power>Standby</Power></Power_Control>
            <Volume><Lvl><Val>-500</Val><Exp>1</Exp><Unit>dB</Unit></Lvl><Mute>Off</Mute></Volume>
            <Input><Input_Sel>HDMI1</Input_Sel></Input>
            <Surround><Program_Sel>Stereo</Program_Sel></Surround>
          </Basic_Status></Main_Zone>
        </YAMAHA_AV>"""
        respx.post(BASE_URL).mock(return_value=httpx.Response(200, content=xml))
        with proto:
            status = proto.get_status()
        assert status.power == "standby"


class TestMuteParsing:
    @respx.mock
    def test_mute_on(self, proto) -> None:
        respx.post(BASE_URL).mock(
            return_value=httpx.Response(200, content=fixture("mute_on.xml"))
        )
        with proto:
            assert proto.get_mute() is True

    @respx.mock
    def test_mute_off(self, proto) -> None:
        xml = b'<YAMAHA_AV rsp="GET" RC="0"><Main_Zone><Volume><Mute>Off</Mute></Volume></Main_Zone></YAMAHA_AV>'
        respx.post(BASE_URL).mock(return_value=httpx.Response(200, content=xml))
        with proto:
            assert proto.get_mute() is False


class TestVolumeParsing:
    @respx.mock
    def test_parses_volume(self, proto) -> None:
        respx.post(BASE_URL).mock(
            return_value=httpx.Response(200, content=fixture("volume_response.xml"))
        )
        with proto:
            vol = proto.get_volume_db()
        assert vol == -45.0

    @respx.mock
    def test_parses_positive_volume(self, proto) -> None:
        xml = b'<YAMAHA_AV rsp="GET" RC="0"><Main_Zone><Volume><Lvl><Val>55</Val><Exp>1</Exp><Unit>dB</Unit></Lvl></Volume></Main_Zone></YAMAHA_AV>'
        respx.post(BASE_URL).mock(return_value=httpx.Response(200, content=xml))
        with proto:
            vol = proto.get_volume_db()
        assert vol == 5.5


class TestErrorHandling:
    @respx.mock
    def test_receiver_rc_nonzero_raises(self, proto) -> None:
        xml = b'<YAMAHA_AV rsp="PUT" RC="3"></YAMAHA_AV>'
        respx.post(BASE_URL).mock(return_value=httpx.Response(200, content=xml))
        with proto, pytest.raises(UnexpectedResponse, match="RC=3"):
            proto.set_power("on")

    @respx.mock
    def test_invalid_xml_raises(self, proto) -> None:
        respx.post(BASE_URL).mock(
            return_value=httpx.Response(200, content=b"not xml at all")
        )
        with proto, pytest.raises(UnexpectedResponse):
            proto.get_status()

    @respx.mock
    def test_connect_error_raises_receiver_unavailable(self, proto) -> None:
        respx.post(BASE_URL).mock(side_effect=httpx.ConnectError("refused"))
        with proto, pytest.raises(ReceiverUnavailable):
            proto.set_power("on")

    @respx.mock
    def test_timeout_raises_command_timeout(self, proto) -> None:
        respx.post(BASE_URL).mock(side_effect=httpx.TimeoutException("timeout"))
        with proto, pytest.raises(CommandTimeout):
            proto.set_power("on")
