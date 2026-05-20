"""CLI handler tests using Typer's CliRunner + mocked YamaCtlClient."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from yamactl.cli.app import app
from yamactl.core.models import (
    NetRadioStatus,
    ReceiverStatus,
    TunerStatus,
)

runner = CliRunner()


def _mock_client(**overrides: object) -> MagicMock:
    """Return a MagicMock configured with sensible defaults for all client methods."""
    m = MagicMock()
    m.get_volume.return_value = -35.0
    m.get_mute.return_value = False
    m.toggle_mute.return_value = True
    m.list_inputs.return_value = ["HDMI1", "HDMI2", "TUNER"]
    m.get_status.return_value = ReceiverStatus(
        host="192.168.1.1", power="on", volume_db=-35.0, input="HDMI1", mute=False
    )
    m.get_tuner_status.return_value = TunerStatus(band="FM", fm_freq_mhz=89.5, tuned=True)
    m.get_netradio_status.return_value = NetRadioStatus(
        playback="Play", station="1LIVE"
    )
    for k, v in overrides.items():
        getattr(m, k).return_value = v
    return m


# ── Power ─────────────────────────────────────────────────────────────────────


class TestPowerCLI:
    def test_power_on(self) -> None:
        client = _mock_client()
        with patch("yamactl.cli.power.make_client", return_value=client):
            result = runner.invoke(app, ["power", "on"])
        assert result.exit_code == 0
        assert "on" in result.output.lower()

    def test_power_standby(self) -> None:
        client = _mock_client()
        with patch("yamactl.cli.power.make_client", return_value=client):
            result = runner.invoke(app, ["power", "standby"])
        assert result.exit_code == 0
        assert "standby" in result.output.lower()


# ── Volume ────────────────────────────────────────────────────────────────────


class TestVolumeCLI:
    def test_volume_get(self) -> None:
        client = _mock_client()
        with patch("yamactl.cli.volume.make_client", return_value=client):
            result = runner.invoke(app, ["volume", "get"])
        assert result.exit_code == 0
        assert "35" in result.output

    def test_volume_get_json(self) -> None:
        client = _mock_client()
        with patch("yamactl.cli.volume.make_client", return_value=client):
            result = runner.invoke(app, ["volume", "get", "--json"])
        assert result.exit_code == 0
        assert "volume_db" in result.output

    def test_volume_set(self) -> None:
        client = _mock_client()
        with patch("yamactl.cli.volume.make_client", return_value=client):
            result = runner.invoke(app, ["volume", "set", "--", "-40.0"])
        assert result.exit_code == 0
        client.set_volume.assert_called_once_with(-40.0)

    def test_volume_up(self) -> None:
        client = _mock_client()
        with patch("yamactl.cli.volume.make_client", return_value=client):
            result = runner.invoke(app, ["volume", "up"])
        assert result.exit_code == 0
        client.volume_up.assert_called_once_with(1)

    def test_volume_up_steps(self) -> None:
        client = _mock_client()
        with patch("yamactl.cli.volume.make_client", return_value=client):
            result = runner.invoke(app, ["volume", "up", "--steps", "3"])
        assert result.exit_code == 0
        client.volume_up.assert_called_once_with(3)

    def test_volume_down(self) -> None:
        client = _mock_client()
        with patch("yamactl.cli.volume.make_client", return_value=client):
            result = runner.invoke(app, ["volume", "down"])
        assert result.exit_code == 0
        client.volume_down.assert_called_once_with(1)


# ── Mute ──────────────────────────────────────────────────────────────────────


class TestMuteCLI:
    def test_mute_on(self) -> None:
        client = _mock_client()
        with patch("yamactl.cli.mute.make_client", return_value=client):
            result = runner.invoke(app, ["mute", "on"])
        assert result.exit_code == 0
        client.set_mute.assert_called_once_with(True)

    def test_mute_off(self) -> None:
        client = _mock_client()
        with patch("yamactl.cli.mute.make_client", return_value=client):
            result = runner.invoke(app, ["mute", "off"])
        assert result.exit_code == 0
        client.set_mute.assert_called_once_with(False)

    def test_mute_toggle(self) -> None:
        client = _mock_client()
        with patch("yamactl.cli.mute.make_client", return_value=client):
            result = runner.invoke(app, ["mute", "toggle"])
        assert result.exit_code == 0
        client.toggle_mute.assert_called_once()


# ── Input ─────────────────────────────────────────────────────────────────────


class TestInputCLI:
    def test_input_list(self) -> None:
        client = _mock_client()
        with patch("yamactl.cli.input_.make_client", return_value=client):
            result = runner.invoke(app, ["input", "list"])
        assert result.exit_code == 0

    def test_input_list_json(self) -> None:
        client = _mock_client()
        with patch("yamactl.cli.input_.make_client", return_value=client):
            result = runner.invoke(app, ["input", "list", "--json"])
        assert result.exit_code == 0
        assert "inputs" in result.output

    def test_input_set(self) -> None:
        client = _mock_client()
        with patch("yamactl.cli.input_.make_client", return_value=client):
            result = runner.invoke(app, ["input", "set", "HDMI1"])
        assert result.exit_code == 0
        client.set_input.assert_called_once_with("HDMI1")


# ── Scene ─────────────────────────────────────────────────────────────────────


class TestSceneCLI:
    def test_scene_load(self) -> None:
        client = _mock_client()
        with patch("yamactl.cli.scene.make_client", return_value=client):
            result = runner.invoke(app, ["scene", "load", "2"])
        assert result.exit_code == 0
        client.load_scene.assert_called_once_with(2)

    def test_scene_load_invalid(self) -> None:
        client = _mock_client()
        with patch("yamactl.cli.scene.make_client", return_value=client):
            result = runner.invoke(app, ["scene", "load", "5"])
        assert result.exit_code == 2


# ── Sound ─────────────────────────────────────────────────────────────────────


class TestSoundCLI:
    def test_sound_mode_set(self) -> None:
        client = _mock_client()
        with patch("yamactl.cli.sound.make_client", return_value=client):
            result = runner.invoke(app, ["sound", "mode", "Hall in Munich"])
        assert result.exit_code == 0
        client.set_dsp_mode.assert_called_once_with("Hall in Munich")

    def test_sound_mode_list(self) -> None:
        result = runner.invoke(app, ["sound", "mode", "--list"])
        assert result.exit_code == 0
        assert "Hall in Munich" in result.output

    def test_sound_mode_no_arg(self) -> None:
        result = runner.invoke(app, ["sound", "mode"])
        assert result.exit_code == 2

    def test_sound_straight_on(self) -> None:
        client = _mock_client()
        with patch("yamactl.cli.sound.make_client", return_value=client):
            result = runner.invoke(app, ["sound", "straight", "on"])
        assert result.exit_code == 0
        client.set_straight.assert_called_once_with(True)

    def test_sound_straight_off(self) -> None:
        client = _mock_client()
        with patch("yamactl.cli.sound.make_client", return_value=client):
            result = runner.invoke(app, ["sound", "straight", "off"])
        assert result.exit_code == 0
        client.set_straight.assert_called_once_with(False)

    def test_sound_straight_invalid(self) -> None:
        client = _mock_client()
        with patch("yamactl.cli.sound.make_client", return_value=client):
            result = runner.invoke(app, ["sound", "straight", "maybe"])
        assert result.exit_code == 2

    def test_sound_direct_on(self) -> None:
        client = _mock_client()
        with patch("yamactl.cli.sound.make_client", return_value=client):
            result = runner.invoke(app, ["sound", "direct", "on"])
        assert result.exit_code == 0
        client.set_direct.assert_called_once_with(True)

    def test_sound_sleep_minutes(self) -> None:
        client = _mock_client()
        with patch("yamactl.cli.sound.make_client", return_value=client):
            result = runner.invoke(app, ["sound", "sleep", "60"])
        assert result.exit_code == 0
        client.set_sleep.assert_called_once_with(60)

    def test_sound_sleep_off(self) -> None:
        client = _mock_client()
        with patch("yamactl.cli.sound.make_client", return_value=client):
            result = runner.invoke(app, ["sound", "sleep", "off"])
        assert result.exit_code == 0
        client.set_sleep.assert_called_once_with(None)

    def test_sound_sleep_invalid(self) -> None:
        client = _mock_client()
        with patch("yamactl.cli.sound.make_client", return_value=client):
            result = runner.invoke(app, ["sound", "sleep", "abc"])
        assert result.exit_code == 2


# ── Tuner ─────────────────────────────────────────────────────────────────────


class TestTunerCLI:
    def test_tuner_status(self) -> None:
        client = _mock_client()
        with patch("yamactl.cli.tuner.make_client", return_value=client):
            result = runner.invoke(app, ["tuner", "status"])
        assert result.exit_code == 0

    def test_tuner_status_json(self) -> None:
        client = _mock_client()
        with patch("yamactl.cli.tuner.make_client", return_value=client):
            result = runner.invoke(app, ["tuner", "status", "--json"])
        assert result.exit_code == 0
        assert "band" in result.output

    def test_tuner_band_fm(self) -> None:
        client = _mock_client()
        with patch("yamactl.cli.tuner.make_client", return_value=client):
            result = runner.invoke(app, ["tuner", "band", "FM"])
        assert result.exit_code == 0
        client.set_tuner_band.assert_called_once_with("FM")

    def test_tuner_band_lowercase(self) -> None:
        client = _mock_client()
        with patch("yamactl.cli.tuner.make_client", return_value=client):
            result = runner.invoke(app, ["tuner", "band", "am"])
        assert result.exit_code == 0
        client.set_tuner_band.assert_called_once_with("AM")

    def test_tuner_band_invalid(self) -> None:
        client = _mock_client()
        with patch("yamactl.cli.tuner.make_client", return_value=client):
            result = runner.invoke(app, ["tuner", "band", "DAB"])
        assert result.exit_code == 2

    def test_tuner_fm(self) -> None:
        client = _mock_client()
        with patch("yamactl.cli.tuner.make_client", return_value=client):
            result = runner.invoke(app, ["tuner", "fm", "89.5"])
        assert result.exit_code == 0
        client.set_tuner_fm_freq.assert_called_once_with(89.5)

    def test_tuner_am(self) -> None:
        client = _mock_client()
        with patch("yamactl.cli.tuner.make_client", return_value=client):
            result = runner.invoke(app, ["tuner", "am", "810"])
        assert result.exit_code == 0
        client.set_tuner_am_freq.assert_called_once_with(810)

    def test_tuner_preset(self) -> None:
        client = _mock_client()
        with patch("yamactl.cli.tuner.make_client", return_value=client):
            result = runner.invoke(app, ["tuner", "preset", "3"])
        assert result.exit_code == 0
        client.set_tuner_preset.assert_called_once_with(3)

    def test_tuner_preset_invalid(self) -> None:
        client = _mock_client()
        with patch("yamactl.cli.tuner.make_client", return_value=client):
            result = runner.invoke(app, ["tuner", "preset", "0"])
        assert result.exit_code == 2


# ── Net Radio ─────────────────────────────────────────────────────────────────


class TestNetRadioCLI:
    def test_netradio_status(self, sample_config) -> None:
        client = _mock_client()
        client.get_status.return_value = ReceiverStatus(
            host="192.168.1.1", power="on", input="NET RADIO"
        )
        with patch("yamactl.cli.netradio.make_client", return_value=client):
            result = runner.invoke(app, ["netradio", "status"])
        assert result.exit_code == 0

    def test_netradio_status_server_input(self, sample_config) -> None:
        client = _mock_client()
        client.get_status.return_value = ReceiverStatus(
            host="192.168.1.1", power="on", input="SERVER"
        )
        client.get_server_status.return_value = NetRadioStatus(playback="Play")
        with patch("yamactl.cli.netradio.make_client", return_value=client):
            result = runner.invoke(app, ["netradio", "status"])
        assert result.exit_code == 0
        client.get_server_status.assert_called_once()

    def test_netradio_pause(self) -> None:
        client = _mock_client()
        with patch("yamactl.cli.netradio.make_client", return_value=client):
            result = runner.invoke(app, ["netradio", "pause"])
        assert result.exit_code == 0
        client.pause_netradio_url.assert_called_once()

    def test_netradio_stop(self) -> None:
        client = _mock_client()
        with patch("yamactl.cli.netradio.make_client", return_value=client):
            result = runner.invoke(app, ["netradio", "stop"])
        assert result.exit_code == 0
        client.stop_netradio_url.assert_called_once()

    def test_netradio_list(self, sample_config) -> None:
        result = runner.invoke(app, ["netradio", "list"])
        assert result.exit_code == 0

    def test_netradio_play_no_presets(self, sample_config) -> None:
        result = runner.invoke(app, ["netradio", "play"])
        assert result.exit_code == 2

    def test_netradio_play_unknown_preset(self, sample_config) -> None:
        result = runner.invoke(app, ["netradio", "play", "unknown"])
        assert result.exit_code == 2

    def test_netradio_url_list(self, sample_config) -> None:
        result = runner.invoke(app, ["netradio", "url", "list"])
        assert result.exit_code == 0

    def test_netradio_url_add(self, sample_config) -> None:
        result = runner.invoke(
            app, ["netradio", "url", "add", "myradio", "http://example.com/stream"]
        )
        assert result.exit_code == 0

    def test_netradio_url_remove(self, sample_config) -> None:
        # First add a preset
        runner.invoke(
            app, ["netradio", "url", "add", "myradio", "http://example.com/stream"]
        )
        result = runner.invoke(app, ["netradio", "url", "remove", "myradio"])
        assert result.exit_code == 0

    def test_netradio_url_remove_not_found(self, sample_config) -> None:
        result = runner.invoke(app, ["netradio", "url", "remove", "nonexistent"])
        assert result.exit_code == 2


# ── Status ────────────────────────────────────────────────────────────────────


class TestStatusCLI:
    def test_status(self) -> None:
        client = _mock_client()
        with patch("yamactl.cli.status.make_client", return_value=client):
            result = runner.invoke(app, ["status"])
        assert result.exit_code == 0

    def test_status_json(self) -> None:
        client = _mock_client()
        with patch("yamactl.cli.status.make_client", return_value=client):
            result = runner.invoke(app, ["status", "--json"])
        assert result.exit_code == 0
        assert "power" in result.output


# ── Raw ───────────────────────────────────────────────────────────────────────


class TestRawCLI:
    def test_raw_ynca(self) -> None:
        client = _mock_client()
        client.send_raw_ynca.return_value = "@MAIN:VOL=-35.5"
        with patch("yamactl.cli.raw.make_client", return_value=client):
            result = runner.invoke(app, ["raw", "ynca", "@MAIN:VOL=?"])
        assert result.exit_code == 0
        assert "@MAIN:VOL=-35.5" in result.output

    def test_raw_xml(self) -> None:
        client = _mock_client()
        client.send_raw_xml.return_value = "<YAMAHA_AV>...</YAMAHA_AV>"
        with patch("yamactl.cli.raw.make_client", return_value=client):
            result = runner.invoke(app, ["raw", "xml", "<test/>"])
        assert result.exit_code == 0


# ── Common option validation ──────────────────────────────────────────────────


class TestCommonOptions:
    def test_invalid_zone_exits_with_2(self) -> None:
        import click

        from yamactl.cli._common import make_client

        with pytest.raises(click.exceptions.Exit):
            make_client(None, "invalid_zone")


# ── Error handling ────────────────────────────────────────────────────────────


class TestErrorHandling:
    def test_yamactl_error_propagates_from_cli(self) -> None:
        from yamactl.core.errors import ReceiverUnavailable

        client = _mock_client()
        client.get_volume.side_effect = ReceiverUnavailable("no connection")
        with patch("yamactl.cli.volume.make_client", return_value=client):
            result = runner.invoke(app, ["volume", "get"])
        # The exception propagates through Typer — exit_code != 0
        assert result.exit_code != 0


# ── Config commands ───────────────────────────────────────────────────────────


class TestConfigCLI:
    def test_config_init_saves_profile(self, sample_config) -> None:
        result = runner.invoke(
            app,
            [
                "config",
                "init",
                "--name",
                "myhome",
                "--host",
                "192.168.1.10",
                "--protocol",
                "ynca",
                "--zone",
                "main",
            ],
        )
        assert result.exit_code == 0
        assert "myhome" in result.output

    def test_config_init_invalid_protocol(self, sample_config) -> None:
        result = runner.invoke(
            app,
            ["config", "init", "--name", "x", "--host", "1.2.3.4", "--protocol", "bad"],
        )
        assert result.exit_code != 0

    def test_config_init_invalid_zone(self, sample_config) -> None:
        result = runner.invoke(
            app,
            [
                "config",
                "init",
                "--name",
                "x",
                "--host",
                "1.2.3.4",
                "--zone",
                "zone99",
            ],
        )
        assert result.exit_code != 0

    def test_config_show_plain(self, sample_config) -> None:
        result = runner.invoke(app, ["config", "show"])
        assert result.exit_code == 0
        assert "Config file:" in result.output

    def test_config_show_json(self, sample_config) -> None:
        import json

        result = runner.invoke(app, ["config", "show", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "profiles" in data

    def test_config_show_with_profile(self, sample_config) -> None:
        result = runner.invoke(app, ["config", "show", "--profile", "test"])
        assert result.exit_code == 0
        assert "192.168.1.100" in result.output

    def test_config_set_host(self, sample_config) -> None:
        result = runner.invoke(
            app, ["config", "set-host", "10.0.0.5", "--profile", "test"]
        )
        assert result.exit_code == 0
        assert "10.0.0.5" in result.output

    def test_config_set_protocol_valid(self, sample_config) -> None:
        result = runner.invoke(
            app, ["config", "set-protocol", "http_xml", "--profile", "test"]
        )
        assert result.exit_code == 0

    def test_config_set_protocol_invalid(self, sample_config) -> None:
        result = runner.invoke(
            app, ["config", "set-protocol", "bad_proto", "--profile", "test"]
        )
        assert result.exit_code != 0

    def test_config_set_default(self, sample_config) -> None:
        result = runner.invoke(app, ["config", "set-default", "test"])
        assert result.exit_code == 0
        assert "test" in result.output


# ── Status discover command ───────────────────────────────────────────────────


class TestDiscoverCLI:
    def test_status_get_json(self) -> None:
        import json

        client = _mock_client()
        with patch("yamactl.cli.status.make_client", return_value=client):
            result = runner.invoke(app, ["status", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "power" in data

    def test_discover_no_subnet_exits(self) -> None:
        result = runner.invoke(app, ["discover"])
        assert result.exit_code != 0
        assert "--subnet" in result.output or "subnet" in result.output.lower()

    def test_discover_with_subnet_json(self) -> None:
        import json

        from yamactl.core.models import DiscoveryCandidate

        candidates = [DiscoveryCandidate(host="192.168.1.50", ynca_available=True)]
        with patch("yamactl.discovery.network.scan_subnet", return_value=candidates):
            result = runner.invoke(app, ["discover", "--subnet", "192.168.1.0/24", "--json"])
        assert result.exit_code == 0
        # Output starts with "Scanning …\n" then JSON
        json_part = result.output.split("\n", 1)[1]
        data = json.loads(json_part)
        assert data[0]["host"] == "192.168.1.50"

    def test_discover_no_candidates(self) -> None:
        with patch("yamactl.discovery.network.scan_subnet", return_value=[]):
            result = runner.invoke(
                app, ["discover", "--subnet", "192.168.1.0/24"], catch_exceptions=False
            )
        assert result.exit_code == 0


# ── App run() error handling ──────────────────────────────────────────────────


class TestAppRun:
    def test_run_receiver_unavailable_exits_nonzero(self) -> None:
        from yamactl.cli.app import run
        from yamactl.core.errors import ReceiverUnavailable

        with patch("yamactl.cli.app.app", side_effect=ReceiverUnavailable("gone")), pytest.raises(SystemExit) as exc_info:
            run()
        assert exc_info.value.code != 0

    def test_run_keyboard_interrupt_exits_130(self) -> None:
        from yamactl.cli.app import run

        with patch("yamactl.cli.app.app", side_effect=KeyboardInterrupt), pytest.raises(SystemExit) as exc_info:
            run()
        assert exc_info.value.code == 130
