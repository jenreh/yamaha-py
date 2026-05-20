"""Tests for the HTTP XML protocol adapter (ync_http.py)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from unittest.mock import MagicMock, patch

import pytest

from yamactl.core.errors import (
    CommandTimeout,
    ProtocolUnsupported,
    ReceiverUnavailable,
    UnexpectedResponse,
)
from yamactl.protocols.ync_http import YncHttpProtocol


def _make_xml_response(body: str, rc: str = "0") -> bytes:
    """Return a minimal YAMAHA_AV response."""
    return f'<YAMAHA_AV RC="{rc}">{body}</YAMAHA_AV>'.encode()


def _make_proto(mocker, zone: str = "main") -> tuple[YncHttpProtocol, MagicMock]:
    proto = YncHttpProtocol("192.168.1.1", zone=zone)
    http_mock = MagicMock()
    mocker.patch.object(proto, "_client", http_mock)
    return proto, http_mock


class TestContextManager:
    def test_enter_returns_self(self, mocker) -> None:
        proto = YncHttpProtocol("192.168.1.1")
        with patch.object(proto, "_client"):
            assert proto.__enter__() is proto

    def test_exit_closes_client(self, mocker) -> None:
        proto, http_mock = _make_proto(mocker)
        proto.__exit__(None, None, None)
        http_mock.close.assert_called_once()


class TestPostErrors:
    def test_timeout_raises_command_timeout(self, mocker) -> None:
        import httpx  # noqa: PLC0415

        proto, http_mock = _make_proto(mocker)
        http_mock.post.side_effect = httpx.TimeoutException("timed out")
        with pytest.raises(CommandTimeout):
            proto._post("<YAMAHA_AV/>")

    def test_connect_error_raises_receiver_unavailable(self, mocker) -> None:
        import httpx  # noqa: PLC0415

        proto, http_mock = _make_proto(mocker)
        http_mock.post.side_effect = httpx.ConnectError("refused")
        with pytest.raises(ReceiverUnavailable):
            proto._post("<YAMAHA_AV/>")

    def test_http_status_error_raises_unexpected_response(self, mocker) -> None:
        import httpx  # noqa: PLC0415

        proto, http_mock = _make_proto(mocker)
        resp = MagicMock()
        resp.status_code = 500
        http_mock.post.side_effect = httpx.HTTPStatusError(
            "500", request=MagicMock(), response=resp
        )
        with pytest.raises(UnexpectedResponse):
            proto._post("<YAMAHA_AV/>")

    def test_invalid_xml_raises_unexpected_response(self, mocker) -> None:
        proto, http_mock = _make_proto(mocker)
        resp = MagicMock()
        resp.content = b"not xml at all!!!"
        http_mock.post.return_value = resp
        with pytest.raises(UnexpectedResponse):
            proto._post("<YAMAHA_AV/>")

    def test_nonzero_rc_raises_unexpected_response(self, mocker) -> None:
        proto, http_mock = _make_proto(mocker)
        resp = MagicMock()
        resp.content = _make_xml_response("", rc="3")
        http_mock.post.return_value = resp
        with pytest.raises(UnexpectedResponse):
            proto._post("<YAMAHA_AV/>")


class TestPowerMute:
    def _mock_post(self, proto: YncHttpProtocol, mocker, body: str = "") -> MagicMock:
        xml = ET.fromstring(_make_xml_response(body))
        return mocker.patch.object(proto, "_post", return_value=xml)

    def test_set_power_on(self, mocker) -> None:
        proto, _ = _make_proto(mocker)
        m = self._mock_post(proto, mocker)
        proto.set_power("on")
        m.assert_called_once()
        assert "On" in m.call_args[0][0]

    def test_set_power_standby(self, mocker) -> None:
        proto, _ = _make_proto(mocker)
        m = self._mock_post(proto, mocker)
        proto.set_power("standby")
        assert "Standby" in m.call_args[0][0]

    def test_get_mute_on(self, mocker) -> None:
        proto, _ = _make_proto(mocker)
        body = "<Main_Zone><Volume><Mute>On</Mute></Volume></Main_Zone>"
        self._mock_post(proto, mocker, body)
        assert proto.get_mute() is True

    def test_get_mute_off(self, mocker) -> None:
        proto, _ = _make_proto(mocker)
        body = "<Main_Zone><Volume><Mute>Off</Mute></Volume></Main_Zone>"
        self._mock_post(proto, mocker, body)
        assert proto.get_mute() is False

    def test_set_mute(self, mocker) -> None:
        proto, _ = _make_proto(mocker)
        m = self._mock_post(proto, mocker)
        proto.set_mute(True)
        assert "On" in m.call_args[0][0]


class TestVolume:
    def _mock_post(self, proto: YncHttpProtocol, mocker, body: str = "") -> MagicMock:
        xml = ET.fromstring(_make_xml_response(body))
        return mocker.patch.object(proto, "_post", return_value=xml)

    def test_get_volume_db(self, mocker) -> None:
        proto, _ = _make_proto(mocker)
        body = "<Main_Zone><Volume><Lvl><Val>-400</Val></Lvl></Volume></Main_Zone>"
        self._mock_post(proto, mocker, body)
        assert proto.get_volume_db() == -40.0

    def test_get_volume_db_missing_raises(self, mocker) -> None:
        proto, _ = _make_proto(mocker)
        self._mock_post(proto, mocker, "<Main_Zone/>")
        with pytest.raises(UnexpectedResponse):
            proto.get_volume_db()

    def test_set_volume_db(self, mocker) -> None:
        proto, _ = _make_proto(mocker)
        m = self._mock_post(proto, mocker)
        proto.set_volume_db(-35.0)
        assert "-350" in m.call_args[0][0]

    def test_volume_up(self, mocker) -> None:
        proto, _ = _make_proto(mocker)
        body = "<Main_Zone><Volume><Lvl><Val>-400</Val></Lvl></Volume></Main_Zone>"
        xml = ET.fromstring(_make_xml_response(body))
        m = mocker.patch.object(proto, "_post", return_value=xml)
        proto.volume_up(1)
        assert m.call_count == 2  # get + set

    def test_volume_down(self, mocker) -> None:
        proto, _ = _make_proto(mocker)
        body = "<Main_Zone><Volume><Lvl><Val>-400</Val></Lvl></Volume></Main_Zone>"
        xml = ET.fromstring(_make_xml_response(body))
        m = mocker.patch.object(proto, "_post", return_value=xml)
        proto.volume_down(1)
        assert m.call_count == 2


class TestInputsAndScene:
    def _mock_post(self, proto: YncHttpProtocol, mocker, body: str = "") -> MagicMock:
        xml = ET.fromstring(_make_xml_response(body))
        return mocker.patch.object(proto, "_post", return_value=xml)

    def test_set_input(self, mocker) -> None:
        proto, _ = _make_proto(mocker)
        m = self._mock_post(proto, mocker)
        proto.set_input("HDMI2")
        assert "HDMI2" in m.call_args[0][0]

    def test_list_inputs_fallback(self, mocker) -> None:
        proto, http_mock = _make_proto(mocker)
        http_mock.get.side_effect = Exception("no desc")
        result = proto.list_inputs()
        assert "HDMI1" in result

    def test_load_scene(self, mocker) -> None:
        proto, _ = _make_proto(mocker)
        m = self._mock_post(proto, mocker)
        proto.load_scene(2)
        m.assert_called_once()

    def test_set_dsp_mode(self, mocker) -> None:
        proto, _ = _make_proto(mocker)
        m = self._mock_post(proto, mocker)
        proto.set_dsp_mode("Hall in Munich")
        assert "Hall in Munich" in m.call_args[0][0]

    def test_set_straight(self, mocker) -> None:
        proto, _ = _make_proto(mocker)
        m = self._mock_post(proto, mocker)
        proto.set_straight(True)
        m.assert_called_once()

    def test_set_direct(self, mocker) -> None:
        proto, _ = _make_proto(mocker)
        m = self._mock_post(proto, mocker)
        proto.set_direct(False)
        m.assert_called_once()

    def test_set_sleep_off(self, mocker) -> None:
        proto, _ = _make_proto(mocker)
        m = self._mock_post(proto, mocker)
        proto.set_sleep(None)
        assert "Off" in m.call_args[0][0]

    def test_set_sleep_minutes(self, mocker) -> None:
        proto, _ = _make_proto(mocker)
        m = self._mock_post(proto, mocker)
        proto.set_sleep(60)
        assert "60" in m.call_args[0][0]


class TestRaw:
    def test_send_raw_xml(self, mocker) -> None:
        proto, _ = _make_proto(mocker)
        xml = ET.fromstring('<YAMAHA_AV RC="0"><OK/></YAMAHA_AV>')
        mocker.patch.object(proto, "_post", return_value=xml)
        result = proto.send_raw_xml("<Test/>")
        assert "YAMAHA_AV" in result

    def test_send_raw_ynca_raises(self, mocker) -> None:
        proto, _ = _make_proto(mocker)
        with pytest.raises(ProtocolUnsupported):
            proto.send_raw_ynca("@MAIN:VOL=?")


class TestGetStatus:
    def test_get_status_returns_receiver_status(self, mocker) -> None:
        proto, _ = _make_proto(mocker)
        body = (
            "<Main_Zone>"
            "<Basic_Status>"
            "<Power_Control><Power>On</Power></Power_Control>"
            "<Volume><Lvl><Val>-350</Val></Lvl><Mute>Off</Mute></Volume>"
            "<Input><Input_Sel>HDMI1</Input_Sel></Input>"
            "<Surround><Program_Sel><Current><Straight>Off</Straight>"
            "<Enhancer>On</Enhancer><Sound_Program>5ch Stereo</Sound_Program>"
            "</Current></Program_Sel></Surround>"
            "</Basic_Status>"
            "</Main_Zone>"
        )
        xml = ET.fromstring(_make_xml_response(body))
        mocker.patch.object(proto, "_post", return_value=xml)
        from yamactl.core.models import ReceiverStatus  # noqa: PLC0415

        result = proto.get_status()
        assert isinstance(result, ReceiverStatus)
        assert result.power == "on"
        assert result.volume_db == -35.0
        assert result.input == "HDMI1"


class TestTuner:
    def _empty_xml(self, mocker, proto: YncHttpProtocol) -> MagicMock:
        xml = ET.fromstring(_make_xml_response("<Tuner/>"))
        return mocker.patch.object(proto, "_post", return_value=xml)

    def test_set_tuner_band(self, mocker) -> None:
        proto, _ = _make_proto(mocker)
        m = self._empty_xml(mocker, proto)
        proto.set_tuner_band("FM")
        m.assert_called_once()
        assert "FM" in m.call_args[0][0]

    def test_set_tuner_fm_freq(self, mocker) -> None:
        proto, _ = _make_proto(mocker)
        m = self._empty_xml(mocker, proto)
        proto.set_tuner_fm_freq(89.5)
        m.assert_called_once()
        assert "8950" in m.call_args[0][0]

    def test_set_tuner_am_freq(self, mocker) -> None:
        proto, _ = _make_proto(mocker)
        m = self._empty_xml(mocker, proto)
        proto.set_tuner_am_freq(1008)
        m.assert_called_once()
        assert "1008" in m.call_args[0][0]

    def test_set_tuner_preset(self, mocker) -> None:
        proto, _ = _make_proto(mocker)
        m = self._empty_xml(mocker, proto)
        proto.set_tuner_preset(3)
        m.assert_called_once()
        assert "3" in m.call_args[0][0]

    def test_get_tuner_status_empty(self, mocker) -> None:
        proto, _ = _make_proto(mocker)
        xml = ET.fromstring(_make_xml_response("<Tuner><Play_Info/></Tuner>"))
        mocker.patch.object(proto, "_post", return_value=xml)
        from yamactl.core.models import TunerStatus  # noqa: PLC0415

        result = proto.get_tuner_status()
        assert isinstance(result, TunerStatus)


class TestNetRadio:
    def _empty_xml(self, mocker, proto: YncHttpProtocol) -> MagicMock:
        xml = ET.fromstring(_make_xml_response("<NET_RADIO/>"))
        return mocker.patch.object(proto, "_post", return_value=xml)

    def test_get_netradio_status_empty(self, mocker) -> None:
        proto, _ = _make_proto(mocker)
        xml = ET.fromstring(_make_xml_response("<NET_RADIO><Play_Info/></NET_RADIO>"))
        mocker.patch.object(proto, "_post", return_value=xml)
        from yamactl.core.models import NetRadioStatus  # noqa: PLC0415

        result = proto.get_netradio_status()
        assert isinstance(result, NetRadioStatus)

    def test_set_netradio_playback(self, mocker) -> None:
        proto, _ = _make_proto(mocker)
        m = self._empty_xml(mocker, proto)
        proto.set_netradio_playback("play")
        m.assert_called_once()

    def test_set_netradio_preset(self, mocker) -> None:
        proto, _ = _make_proto(mocker)
        m = self._empty_xml(mocker, proto)
        proto.set_netradio_preset(2)
        m.assert_called_once()

    def test_get_server_status_empty(self, mocker) -> None:
        proto, _ = _make_proto(mocker)
        xml = ET.fromstring(_make_xml_response("<SERVER><Play_Info/></SERVER>"))
        mocker.patch.object(proto, "_post", return_value=xml)
        from yamactl.core.models import NetRadioStatus  # noqa: PLC0415

        result = proto.get_server_status()
        assert isinstance(result, NetRadioStatus)
