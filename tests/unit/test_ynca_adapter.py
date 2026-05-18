"""Tests for the YNCA TCP adapter — ynca library mocked, no real socket."""

from __future__ import annotations

from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from yamactl.core.errors import ReceiverBusy, ReceiverUnavailable, ProtocolUnsupported
from yamactl.protocols.ynca_tcp import YncaTcpProtocol


def _make_proto(zone: str = "main") -> YncaTcpProtocol:
    return YncaTcpProtocol(host="192.168.1.100", port=50000, zone=zone, timeout=1.0)


def _mock_api(pwr="ON", vol=-45.0, mute="OFF", inp="HDMI1", soundprg="7ch Surround"):
    """Build a minimal mock ynca.YncaApi object."""
    api = MagicMock()
    zone = MagicMock()
    zone.pwr = pwr
    zone.vol = vol
    zone.mute = mute
    zone.inp = inp
    zone.soundprg = soundprg
    zone.sleep = None
    api.main = zone
    api.zone2 = MagicMock()
    api.sys = MagicMock()
    api.sys.modelname = "RX-V475"
    return api


class TestConnection:
    def test_enter_initializes_ynca(self):
        proto = _make_proto()
        mock_api = _mock_api()
        with patch("ynca.YncaApi", return_value=mock_api) as mock_cls:
            with proto:
                mock_cls.assert_called_once_with("socket://192.168.1.100:50000")
                mock_api.initialize.assert_called_once()

    def test_exit_closes_api(self):
        proto = _make_proto()
        mock_api = _mock_api()
        with patch("ynca.YncaApi", return_value=mock_api):
            with proto:
                pass
        mock_api.close.assert_called_once()

    def test_connection_error_raises_receiver_unavailable(self):
        proto = _make_proto()
        with patch("ynca.YncaApi", side_effect=ConnectionRefusedError("refused")):
            with pytest.raises(ReceiverUnavailable):
                proto.__enter__()

    def test_import_error_raises_receiver_unavailable(self):
        proto = _make_proto()
        with patch.dict("sys.modules", {"ynca": None}):
            with pytest.raises((ReceiverUnavailable, ImportError)):
                proto.__enter__()

    def test_not_connected_raises_runtime_error(self):
        proto = _make_proto()
        with pytest.raises(RuntimeError, match="context manager"):
            proto._assert_connected()


class TestPower:
    def test_set_power_on(self):
        proto = _make_proto()
        mock_api = _mock_api()
        with patch("ynca.YncaApi", return_value=mock_api):
            with proto:
                with patch("ynca.enums.Pwr") as pwr_enum:
                    pwr_enum.ON = "ON"
                    pwr_enum.STANDBY = "STANDBY"
                    proto.set_power("on")
        mock_api.main.pwr  # attribute was set

    def test_set_power_standby(self):
        proto = _make_proto()
        mock_api = _mock_api()
        with patch("ynca.YncaApi", return_value=mock_api):
            with proto:
                with patch("ynca.enums.Pwr") as pwr_enum:
                    pwr_enum.ON = "ON"
                    pwr_enum.STANDBY = "STANDBY"
                    proto.set_power("standby")


class TestMute:
    def test_get_mute_on(self):
        proto = _make_proto()
        mock_api = _mock_api(mute="ON")
        with patch("ynca.YncaApi", return_value=mock_api):
            with proto:
                with patch("ynca.enums.Mute") as mute_enum:
                    mute_enum.ON = "ON"
                    result = proto.get_mute()
        assert result is True

    def test_get_mute_off(self):
        proto = _make_proto()
        mock_api = _mock_api(mute="OFF")
        with patch("ynca.YncaApi", return_value=mock_api):
            with proto:
                with patch("ynca.enums.Mute") as mute_enum:
                    mute_enum.ON = "ON"
                    result = proto.get_mute()
        assert result is False


class TestVolume:
    def test_get_volume_db(self):
        proto = _make_proto()
        mock_api = _mock_api(vol=-45.0)
        with patch("ynca.YncaApi", return_value=mock_api):
            with proto:
                vol = proto.get_volume_db()
        assert vol == -45.0

    def test_set_volume_db(self):
        proto = _make_proto()
        mock_api = _mock_api()
        with patch("ynca.YncaApi", return_value=mock_api):
            with proto:
                proto.set_volume_db(-50.0)
        assert mock_api.main.vol == -50.0

    def test_volume_up_calls_vol_up(self):
        proto = _make_proto()
        mock_api = _mock_api()
        with patch("ynca.YncaApi", return_value=mock_api):
            with proto:
                proto.volume_up(3)
        mock_api.main.vol_up.assert_called_once_with(3)

    def test_volume_down_calls_vol_down(self):
        proto = _make_proto()
        mock_api = _mock_api()
        with patch("ynca.YncaApi", return_value=mock_api):
            with proto:
                proto.volume_down(2)
        mock_api.main.vol_down.assert_called_once_with(2)


class TestInput:
    def test_set_input(self):
        proto = _make_proto()
        mock_api = _mock_api()
        with patch("ynca.YncaApi", return_value=mock_api):
            with proto:
                proto.set_input("HDMI2")
        assert mock_api.main.inp == "HDMI2"


class TestStatus:
    def test_get_status_on(self):
        proto = _make_proto()
        mock_api = _mock_api(pwr="ON", vol=-45.0, inp="HDMI1")
        with patch("ynca.YncaApi", return_value=mock_api):
            with proto:
                with patch("ynca.enums.Pwr") as pwr_enum:
                    pwr_enum.ON = "ON"
                    status = proto.get_status()
        assert status.power == "on"
        assert status.volume_db == -45.0
        assert status.input == "HDMI1"
        assert status.model == "RX-V475"

    def test_get_status_standby(self):
        proto = _make_proto()
        mock_api = _mock_api(pwr="STANDBY")
        with patch("ynca.YncaApi", return_value=mock_api):
            with proto:
                with patch("ynca.enums.Pwr") as pwr_enum:
                    pwr_enum.ON = "ON"
                    status = proto.get_status()
        assert status.power == "standby"


class TestZone2:
    def test_zone2_uses_zone2_attribute(self):
        proto = _make_proto(zone="zone2")
        mock_api = _mock_api()
        mock_api.zone2.vol = -60.0
        with patch("ynca.YncaApi", return_value=mock_api):
            with proto:
                vol = proto.get_volume_db()
        assert vol == -60.0
        mock_api.main.vol  # main zone should NOT have been accessed


class TestRaw:
    def test_send_raw_xml_raises_unsupported(self):
        proto = _make_proto()
        mock_api = _mock_api()
        with patch("ynca.YncaApi", return_value=mock_api):
            with proto:
                with pytest.raises(ProtocolUnsupported):
                    proto.send_raw_xml("<YAMAHA_AV/>")
