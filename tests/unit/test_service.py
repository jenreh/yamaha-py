"""Tests for the service layer — adapter selection, validation, retry."""

from __future__ import annotations

import pytest

from yamactl.core.errors import CommandTimeout
from yamactl.core.models import ReceiverConfig, ReceiverStatus
from yamactl.core.service import ReceiverService


def _make_service(protocol: str = "http_xml", retries: int = 1) -> ReceiverService:
    cfg = ReceiverConfig(
        name="test",
        host="192.168.1.100",
        protocol=protocol,  # type: ignore[arg-type]
        timeout_seconds=1.0,
        retries=retries,
    )
    return ReceiverService(cfg)


class TestProtocolSelection:
    def test_selects_http_xml_adapter(self) -> None:
        svc = _make_service("http_xml")
        proto = svc._make_protocol()
        from yamactl.protocols.ync_http import YncHttpProtocol  # noqa: PLC0415

        assert isinstance(proto, YncHttpProtocol)

    def test_selects_ynca_adapter(self) -> None:
        svc = _make_service("ynca")
        proto = svc._make_protocol()
        from yamactl.protocols.ynca_tcp import YncaTcpProtocol  # noqa: PLC0415

        assert isinstance(proto, YncaTcpProtocol)


class TestVolumeValidation:
    def test_rejects_too_low(self) -> None:
        svc = _make_service()
        with pytest.raises(ValueError, match="out of range"):
            svc._clamp_volume(-100.0)

    def test_rejects_too_high(self) -> None:
        svc = _make_service()
        with pytest.raises(ValueError, match="out of range"):
            svc._clamp_volume(20.0)

    def test_rounds_to_half_step(self) -> None:
        svc = _make_service()
        assert svc._clamp_volume(-45.3) == -45.5

    def test_accepts_boundary_min(self) -> None:
        svc = _make_service()
        assert svc._clamp_volume(-80.5) == -80.5

    def test_accepts_boundary_max(self) -> None:
        svc = _make_service()
        assert svc._clamp_volume(16.5) == 16.5


class TestRetryLogic:
    def test_retries_on_timeout(self, mocker) -> None:
        svc = _make_service(retries=3)
        call_count = 0

        class FakeProto:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def get_status(self):
                nonlocal call_count
                call_count += 1
                if call_count < 3:
                    raise CommandTimeout("timeout")
                return ReceiverStatus(host="192.168.1.100", power="on")

        mocker.patch.object(svc, "_make_protocol", return_value=FakeProto())
        status = svc.get_status()
        assert call_count == 3
        assert status.power == "on"

    def test_raises_after_all_retries_exhausted(self, mocker) -> None:
        svc = _make_service(retries=2)

        class AlwaysTimeout:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def get_status(self):
                raise CommandTimeout("always times out")

        mocker.patch.object(svc, "_make_protocol", return_value=AlwaysTimeout())
        with pytest.raises(CommandTimeout):
            svc.get_status()

    def test_no_retry_on_unexpected_response(self, mocker) -> None:
        from yamactl.core.errors import UnexpectedResponse  # noqa: PLC0415

        svc = _make_service(retries=3)
        call_count = 0

        class BadResponse:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def get_status(self):
                nonlocal call_count
                call_count += 1
                raise UnexpectedResponse("bad")

        mocker.patch.object(svc, "_make_protocol", return_value=BadResponse())
        with pytest.raises(UnexpectedResponse):
            svc.get_status()
        assert call_count == 1


class TestZoneOverride:
    def test_zone_override_applied(self, tmp_path) -> None:
        from unittest.mock import patch  # noqa: PLC0415

        import yaml  # noqa: PLC0415

        import yamactl.core.config as cfg_mod  # noqa: PLC0415

        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            yaml.dump(
                {
                    "default_profile": "test",
                    "profiles": {
                        "test": {
                            "host": "192.168.1.1",
                            "protocol": "http_xml",
                            "zone": "main",
                        }
                    },
                }
            )
        )
        with patch.object(cfg_mod, "config_path", return_value=config_file):
            svc = ReceiverService.from_profile("test", zone_override="zone2")
            assert svc._config.zone == "zone2"


class TestSceneValidation:
    def test_invalid_scene_raises(self, mocker) -> None:
        svc = _make_service()
        with pytest.raises(ValueError, match="Scene must be 1"):
            svc.load_scene(5)

    def test_valid_scenes(self, mocker) -> None:
        svc = _make_service()
        mock_run = mocker.patch.object(svc, "_run")
        for i in (1, 2, 3, 4):
            svc.load_scene(i)
        assert mock_run.call_count == 4


class TestServiceMethods:
    """Exercise the thin _run wrappers to get line coverage."""

    def setup_method(self) -> None:
        from unittest.mock import MagicMock  # noqa: PLC0415

        from yamactl.core.models import (  # noqa: PLC0415
            NetRadioStatus,
            ReceiverStatus,
            TunerStatus,
        )

        self.svc = _make_service()
        self.proto = MagicMock()
        self.proto.get_status.return_value = ReceiverStatus(host="h", power="on")
        self.proto.get_mute.return_value = False
        self.proto.get_volume_db.return_value = -40.0
        self.proto.list_inputs.return_value = ["HDMI1", "AV1"]
        self.proto.send_raw_ynca.return_value = "@MAIN:VOL=-40.0"
        self.proto.send_raw_xml.return_value = "<OK/>"
        self.proto.get_tuner_status.return_value = TunerStatus()
        self.proto.get_netradio_status.return_value = NetRadioStatus()
        self.proto.get_server_status.return_value = NetRadioStatus()
        self.proto.__enter__ = lambda self_: self_
        self.proto.__exit__ = MagicMock(return_value=False)

    def _patch_proto(self, mocker) -> None:
        mocker.patch.object(self.svc, "_make_protocol", return_value=self.proto)

    def test_get_status(self, mocker) -> None:
        self._patch_proto(mocker)
        result = self.svc.get_status()
        assert result.power == "on"

    def test_set_power(self, mocker) -> None:
        self._patch_proto(mocker)
        self.svc.set_power("standby")
        self.proto.set_power.assert_called_once_with("standby")

    def test_get_mute(self, mocker) -> None:
        self._patch_proto(mocker)
        assert self.svc.get_mute() is False

    def test_set_mute(self, mocker) -> None:
        self._patch_proto(mocker)
        self.svc.set_mute(True)
        self.proto.set_mute.assert_called_once_with(True)

    def test_toggle_mute_returns_new_state(self, mocker) -> None:
        self._patch_proto(mocker)
        result = self.svc.toggle_mute()
        assert result is True  # was False, toggled to True

    def test_get_volume_db(self, mocker) -> None:
        self._patch_proto(mocker)
        assert self.svc.get_volume_db() == -40.0

    def test_set_volume_db(self, mocker) -> None:
        self._patch_proto(mocker)
        self.svc.set_volume_db(-35.0)
        self.proto.set_volume_db.assert_called_once()

    def test_volume_up(self, mocker) -> None:
        self._patch_proto(mocker)
        self.svc.volume_up(2)
        self.proto.volume_up.assert_called_once_with(2)

    def test_volume_down(self, mocker) -> None:
        self._patch_proto(mocker)
        self.svc.volume_down(1)
        self.proto.volume_down.assert_called_once_with(1)

    def test_set_input(self, mocker) -> None:
        self._patch_proto(mocker)
        self.svc.set_input("HDMI1")
        self.proto.set_input.assert_called_once_with("HDMI1")

    def test_list_inputs(self, mocker) -> None:
        self._patch_proto(mocker)
        assert self.svc.list_inputs() == ["HDMI1", "AV1"]

    def test_set_dsp_mode(self, mocker) -> None:
        self._patch_proto(mocker)
        self.svc.set_dsp_mode("Hall in Munich")
        self.proto.set_dsp_mode.assert_called_once_with("Hall in Munich")

    def test_set_straight(self, mocker) -> None:
        self._patch_proto(mocker)
        self.svc.set_straight(True)
        self.proto.set_straight.assert_called_once_with(True)

    def test_set_direct(self, mocker) -> None:
        self._patch_proto(mocker)
        self.svc.set_direct(False)
        self.proto.set_direct.assert_called_once_with(False)

    def test_set_sleep(self, mocker) -> None:
        self._patch_proto(mocker)
        self.svc.set_sleep(60)
        self.proto.set_sleep.assert_called_once_with(60)

    def test_send_raw_ynca(self, mocker) -> None:
        self._patch_proto(mocker)
        result = self.svc.send_raw_ynca("@MAIN:VOL=?")
        assert "VOL" in result

    def test_send_raw_xml(self, mocker) -> None:
        self._patch_proto(mocker)
        result = self.svc.send_raw_xml("<GetParam/>")
        assert result == "<OK/>"

    def test_get_tuner_status(self, mocker) -> None:
        self._patch_proto(mocker)
        from yamactl.core.models import TunerStatus  # noqa: PLC0415

        result = self.svc.get_tuner_status()
        assert isinstance(result, TunerStatus)

    def test_set_tuner_band(self, mocker) -> None:
        self._patch_proto(mocker)
        self.svc.set_tuner_band("FM")
        self.proto.set_tuner_band.assert_called_once_with("FM")

    def test_set_tuner_fm_freq(self, mocker) -> None:
        self._patch_proto(mocker)
        self.svc.set_tuner_fm_freq(101.5)
        self.proto.set_tuner_fm_freq.assert_called_once_with(101.5)

    def test_set_tuner_am_freq(self, mocker) -> None:
        self._patch_proto(mocker)
        self.svc.set_tuner_am_freq(1008)
        self.proto.set_tuner_am_freq.assert_called_once_with(1008)

    def test_set_tuner_preset(self, mocker) -> None:
        self._patch_proto(mocker)
        self.svc.set_tuner_preset(3)
        self.proto.set_tuner_preset.assert_called_once_with(3)

    def test_get_netradio_status(self, mocker) -> None:
        self._patch_proto(mocker)
        from yamactl.core.models import NetRadioStatus  # noqa: PLC0415

        result = self.svc.get_netradio_status()
        assert isinstance(result, NetRadioStatus)

    def test_set_netradio_playback(self, mocker) -> None:
        self._patch_proto(mocker)
        self.svc.set_netradio_playback("play")
        self.proto.set_netradio_playback.assert_called_once_with("play")

    def test_set_netradio_preset(self, mocker) -> None:
        self._patch_proto(mocker)
        self.svc.set_netradio_preset(2)
        self.proto.set_netradio_preset.assert_called_once_with(2)

    def test_play_netradio_url(self, mocker) -> None:
        self._patch_proto(mocker)
        self.svc.play_netradio_url("http://stream.example.com/live", "Test Radio")
        self.proto.play_netradio_url.assert_called_once()

    def test_pause_netradio_url(self, mocker) -> None:
        self._patch_proto(mocker)
        self.svc.pause_netradio_url()
        self.proto.pause_netradio_url.assert_called_once()

    def test_stop_netradio_url(self, mocker) -> None:
        self._patch_proto(mocker)
        self.svc.stop_netradio_url()
        self.proto.stop_netradio_url.assert_called_once()

    def test_get_server_status(self, mocker) -> None:
        self._patch_proto(mocker)
        from yamactl.core.models import NetRadioStatus  # noqa: PLC0415

        result = self.svc.get_server_status()
        assert isinstance(result, NetRadioStatus)
