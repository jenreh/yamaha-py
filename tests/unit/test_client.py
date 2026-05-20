"""Tests for YamaCtlClient — SDK wrapper around ReceiverService."""

from __future__ import annotations

from pathlib import Path

import pytest

from yamactl.client import YamaCtlClient
from yamactl.core.errors import CommandTimeout
from yamactl.core.models import (
    NetRadioStatus,
    ReceiverConfig,
    ReceiverStatus,
    TunerStatus,
)


def _make_client(protocol: str = "http_xml") -> YamaCtlClient:
    cfg = ReceiverConfig(
        name="test",
        host="192.168.1.100",
        protocol=protocol,  # type: ignore[arg-type]
        timeout_seconds=1.0,
        retries=1,
    )
    return YamaCtlClient(cfg)


# ── Construction ──────────────────────────────────────────────────────────────


class TestConstruction:
    def test_from_config(self) -> None:
        client = _make_client()
        assert client._service is not None

    def test_context_manager(self) -> None:
        client = _make_client()
        with client as c:
            assert c is client

    def test_from_profile_loads_config(self, sample_config: Path) -> None:
        client = YamaCtlClient.from_profile()
        assert client._service._config.host == "192.168.1.100"

    def test_from_profile_zone_override(self, sample_config: Path) -> None:
        client = YamaCtlClient.from_profile(zone_override="zone2")
        assert client._service._config.zone == "zone2"

    def test_from_profile_named(self, sample_config: Path) -> None:
        client = YamaCtlClient.from_profile("test")
        assert client._service._config.name == "test"


# ── Status ────────────────────────────────────────────────────────────────────


class TestStatus:
    def test_get_status_delegates(self, mocker) -> None:
        client = _make_client()
        expected = ReceiverStatus(host="192.168.1.100", power="on")
        mocker.patch.object(client._service, "get_status", return_value=expected)

        result = client.get_status()

        assert result is expected
        client._service.get_status.assert_called_once()


# ── Power ─────────────────────────────────────────────────────────────────────


class TestPower:
    def test_set_power_on(self, mocker) -> None:
        client = _make_client()
        mocker.patch.object(client._service, "set_power")

        client.set_power("on")

        client._service.set_power.assert_called_once_with("on")

    def test_set_power_standby(self, mocker) -> None:
        client = _make_client()
        mocker.patch.object(client._service, "set_power")

        client.set_power("standby")

        client._service.set_power.assert_called_once_with("standby")


# ── Volume ────────────────────────────────────────────────────────────────────


class TestVolume:
    def test_get_volume(self, mocker) -> None:
        client = _make_client()
        mocker.patch.object(client._service, "get_volume_db", return_value=-35.5)

        assert client.get_volume() == -35.5

    def test_set_volume(self, mocker) -> None:
        client = _make_client()
        mocker.patch.object(client._service, "set_volume_db")

        client.set_volume(-40.0)

        client._service.set_volume_db.assert_called_once_with(-40.0)

    def test_volume_up(self, mocker) -> None:
        client = _make_client()
        mocker.patch.object(client._service, "volume_up")

        client.volume_up(3)

        client._service.volume_up.assert_called_once_with(3)

    def test_volume_down(self, mocker) -> None:
        client = _make_client()
        mocker.patch.object(client._service, "volume_down")

        client.volume_down(2)

        client._service.volume_down.assert_called_once_with(2)

    def test_volume_up_default_steps(self, mocker) -> None:
        client = _make_client()
        mocker.patch.object(client._service, "volume_up")

        client.volume_up()

        client._service.volume_up.assert_called_once_with(1)


# ── Mute ──────────────────────────────────────────────────────────────────────


class TestMute:
    def test_get_mute(self, mocker) -> None:
        client = _make_client()
        mocker.patch.object(client._service, "get_mute", return_value=True)

        assert client.get_mute() is True

    def test_set_mute(self, mocker) -> None:
        client = _make_client()
        mocker.patch.object(client._service, "set_mute")

        client.set_mute(False)

        client._service.set_mute.assert_called_once_with(False)

    def test_toggle_mute(self, mocker) -> None:
        client = _make_client()
        mocker.patch.object(client._service, "toggle_mute", return_value=True)

        result = client.toggle_mute()

        assert result is True
        client._service.toggle_mute.assert_called_once()


# ── Input ─────────────────────────────────────────────────────────────────────


class TestInput:
    def test_list_inputs(self, mocker) -> None:
        client = _make_client()
        mocker.patch.object(client._service, "list_inputs", return_value=["HDMI1", "TUNER"])

        result = client.list_inputs()

        assert result == ["HDMI1", "TUNER"]

    def test_set_input(self, mocker) -> None:
        client = _make_client()
        mocker.patch.object(client._service, "set_input")

        client.set_input("HDMI1")

        client._service.set_input.assert_called_once_with("HDMI1")


# ── Scene ─────────────────────────────────────────────────────────────────────


class TestScene:
    def test_load_scene(self, mocker) -> None:
        client = _make_client()
        mocker.patch.object(client._service, "load_scene")

        client.load_scene(2)

        client._service.load_scene.assert_called_once_with(2)

    def test_load_scene_invalid_raises(self, mocker) -> None:
        client = _make_client()
        mocker.patch.object(client._service, "load_scene", side_effect=ValueError("Scene must be 1–4"))

        with pytest.raises(ValueError, match="1–4"):
            client.load_scene(5)


# ── Sound ─────────────────────────────────────────────────────────────────────


class TestSound:
    def test_set_dsp_mode(self, mocker) -> None:
        client = _make_client()
        mocker.patch.object(client._service, "set_dsp_mode")

        client.set_dsp_mode("Hall in Munich")

        client._service.set_dsp_mode.assert_called_once_with("Hall in Munich")

    def test_set_straight(self, mocker) -> None:
        client = _make_client()
        mocker.patch.object(client._service, "set_straight")

        client.set_straight(True)

        client._service.set_straight.assert_called_once_with(True)

    def test_set_direct(self, mocker) -> None:
        client = _make_client()
        mocker.patch.object(client._service, "set_direct")

        client.set_direct(False)

        client._service.set_direct.assert_called_once_with(False)

    def test_set_sleep(self, mocker) -> None:
        client = _make_client()
        mocker.patch.object(client._service, "set_sleep")

        client.set_sleep(60)

        client._service.set_sleep.assert_called_once_with(60)

    def test_set_sleep_none(self, mocker) -> None:
        client = _make_client()
        mocker.patch.object(client._service, "set_sleep")

        client.set_sleep(None)

        client._service.set_sleep.assert_called_once_with(None)


# ── Tuner ─────────────────────────────────────────────────────────────────────


class TestTuner:
    def test_get_tuner_status(self, mocker) -> None:
        client = _make_client()
        expected = TunerStatus(band="FM", fm_freq_mhz=89.5)
        mocker.patch.object(client._service, "get_tuner_status", return_value=expected)

        result = client.get_tuner_status()

        assert result is expected

    def test_set_tuner_band(self, mocker) -> None:
        client = _make_client()
        mocker.patch.object(client._service, "set_tuner_band")

        client.set_tuner_band("AM")

        client._service.set_tuner_band.assert_called_once_with("AM")

    def test_set_tuner_fm_freq(self, mocker) -> None:
        client = _make_client()
        mocker.patch.object(client._service, "set_tuner_fm_freq")

        client.set_tuner_fm_freq(104.6)

        client._service.set_tuner_fm_freq.assert_called_once_with(104.6)

    def test_set_tuner_am_freq(self, mocker) -> None:
        client = _make_client()
        mocker.patch.object(client._service, "set_tuner_am_freq")

        client.set_tuner_am_freq(810)

        client._service.set_tuner_am_freq.assert_called_once_with(810)

    def test_set_tuner_preset(self, mocker) -> None:
        client = _make_client()
        mocker.patch.object(client._service, "set_tuner_preset")

        client.set_tuner_preset(3)

        client._service.set_tuner_preset.assert_called_once_with(3)


# ── Net Radio ─────────────────────────────────────────────────────────────────


class TestNetRadio:
    def test_get_netradio_status(self, mocker) -> None:
        client = _make_client()
        expected = NetRadioStatus(playback="Play", station="1LIVE")
        mocker.patch.object(client._service, "get_netradio_status", return_value=expected)

        result = client.get_netradio_status()

        assert result is expected

    def test_play_netradio_url(self, mocker) -> None:
        client = _make_client()
        mocker.patch.object(client._service, "play_netradio_url")

        client.play_netradio_url("http://stream.example.com/live", "My Radio")

        client._service.play_netradio_url.assert_called_once_with(
            "http://stream.example.com/live", "My Radio"
        )

    def test_play_netradio_url_default_title(self, mocker) -> None:
        client = _make_client()
        mocker.patch.object(client._service, "play_netradio_url")

        client.play_netradio_url("http://stream.example.com/live")

        client._service.play_netradio_url.assert_called_once_with(
            "http://stream.example.com/live", ""
        )

    def test_pause_netradio_url(self, mocker) -> None:
        client = _make_client()
        mocker.patch.object(client._service, "pause_netradio_url")

        client.pause_netradio_url()

        client._service.pause_netradio_url.assert_called_once()

    def test_stop_netradio_url(self, mocker) -> None:
        client = _make_client()
        mocker.patch.object(client._service, "stop_netradio_url")

        client.stop_netradio_url()

        client._service.stop_netradio_url.assert_called_once()

    def test_set_netradio_playback(self, mocker) -> None:
        client = _make_client()
        mocker.patch.object(client._service, "set_netradio_playback")

        client.set_netradio_playback("Stop")

        client._service.set_netradio_playback.assert_called_once_with("Stop")

    def test_set_netradio_preset(self, mocker) -> None:
        client = _make_client()
        mocker.patch.object(client._service, "set_netradio_preset")

        client.set_netradio_preset(5)

        client._service.set_netradio_preset.assert_called_once_with(5)


# ── Raw ───────────────────────────────────────────────────────────────────────


class TestRaw:
    def test_send_raw_ynca(self, mocker) -> None:
        client = _make_client()
        mocker.patch.object(client._service, "send_raw_ynca", return_value="@MAIN:VOL=-35.5")

        result = client.send_raw_ynca("@MAIN:VOL=?")

        assert result == "@MAIN:VOL=-35.5"

    def test_send_raw_xml(self, mocker) -> None:
        client = _make_client()
        mocker.patch.object(client._service, "send_raw_xml", return_value="<response/>")

        result = client.send_raw_xml("<YAMAHA_AV>...</YAMAHA_AV>")

        assert result == "<response/>"


# ── Error propagation ─────────────────────────────────────────────────────────


class TestErrorPropagation:
    def test_yamactl_errors_propagate(self, mocker) -> None:
        client = _make_client()
        mocker.patch.object(
            client._service, "get_status", side_effect=CommandTimeout("no reply")
        )

        with pytest.raises(CommandTimeout):
            client.get_status()
