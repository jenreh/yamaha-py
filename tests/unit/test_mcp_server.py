"""Tests for the FastMCP server tools."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from yamactl.core.models import (
    NetRadioStatus,
    ReceiverStatus,
    TunerStatus,
)
from yamactl.mcp import server as mcp_server


def _mock_client() -> MagicMock:
    """Return a MagicMock that behaves like YamaCtlClient."""
    m = MagicMock()
    m.__enter__ = MagicMock(return_value=m)
    m.__exit__ = MagicMock(return_value=False)
    return m


# ── Status ────────────────────────────────────────────────────────────────────


class TestGetReceiverStatus:
    def test_returns_status_dict(self) -> None:
        client = _mock_client()
        client.get_status.return_value = ReceiverStatus(
            host="192.168.1.1", power="on", volume_db=-35.0
        )
        with patch.object(mcp_server, "_client", return_value=client):
            result = mcp_server.get_receiver_status()

        assert result["power"] == "on"
        assert result["volume_db"] == -35.0


# ── Power ─────────────────────────────────────────────────────────────────────


class TestSetPower:
    def test_on(self) -> None:
        client = _mock_client()
        with patch.object(mcp_server, "_client", return_value=client):
            result = mcp_server.set_power("on")

        client.set_power.assert_called_once_with("on")
        assert "on" in result

    def test_standby(self) -> None:
        client = _mock_client()
        with patch.object(mcp_server, "_client", return_value=client):
            result = mcp_server.set_power("standby")

        client.set_power.assert_called_once_with("standby")
        assert "standby" in result


# ── Volume ────────────────────────────────────────────────────────────────────


class TestGetVolume:
    def test_returns_volume_dict(self) -> None:
        client = _mock_client()
        client.get_volume.return_value = -40.0
        with patch.object(mcp_server, "_client", return_value=client):
            result = mcp_server.get_volume()

        assert result == {"volume_db": -40.0}


class TestSetVolume:
    def test_sets_volume(self) -> None:
        client = _mock_client()
        with patch.object(mcp_server, "_client", return_value=client):
            result = mcp_server.set_volume(-35.0)

        client.set_volume.assert_called_once_with(-35.0)
        assert "-35.0" in result

    def test_formats_db_in_confirmation(self) -> None:
        client = _mock_client()
        with patch.object(mcp_server, "_client", return_value=client):
            result = mcp_server.set_volume(0.0)

        assert "+0.0" in result


class TestVolumeStep:
    def test_volume_up(self) -> None:
        client = _mock_client()
        with patch.object(mcp_server, "_client", return_value=client):
            result = mcp_server.volume_up(2)

        client.volume_up.assert_called_once_with(2)
        assert "2" in result

    def test_volume_up_default(self) -> None:
        client = _mock_client()
        with patch.object(mcp_server, "_client", return_value=client):
            mcp_server.volume_up()

        client.volume_up.assert_called_once_with(1)

    def test_volume_down(self) -> None:
        client = _mock_client()
        with patch.object(mcp_server, "_client", return_value=client):
            result = mcp_server.volume_down(3)

        client.volume_down.assert_called_once_with(3)
        assert "3" in result


# ── Mute ──────────────────────────────────────────────────────────────────────


class TestGetMute:
    def test_returns_mute_dict(self) -> None:
        client = _mock_client()
        client.get_mute.return_value = True
        with patch.object(mcp_server, "_client", return_value=client):
            result = mcp_server.get_mute()

        assert result == {"mute": True}


class TestSetMute:
    def test_enable(self) -> None:
        client = _mock_client()
        with patch.object(mcp_server, "_client", return_value=client):
            result = mcp_server.set_mute(True)

        client.set_mute.assert_called_once_with(True)
        assert "on" in result

    def test_disable(self) -> None:
        client = _mock_client()
        with patch.object(mcp_server, "_client", return_value=client):
            result = mcp_server.set_mute(False)

        assert "off" in result


class TestToggleMute:
    def test_returns_new_state(self) -> None:
        client = _mock_client()
        client.toggle_mute.return_value = False
        with patch.object(mcp_server, "_client", return_value=client):
            result = mcp_server.toggle_mute()

        assert result == {"mute": False}


# ── Input ─────────────────────────────────────────────────────────────────────


class TestListInputs:
    def test_returns_inputs_dict(self) -> None:
        client = _mock_client()
        client.list_inputs.return_value = ["HDMI1", "TUNER", "USB"]
        with patch.object(mcp_server, "_client", return_value=client):
            result = mcp_server.list_inputs()

        assert result == {"inputs": ["HDMI1", "TUNER", "USB"]}


class TestSetInput:
    def test_sets_input(self) -> None:
        client = _mock_client()
        with patch.object(mcp_server, "_client", return_value=client):
            result = mcp_server.set_input("HDMI1")

        client.set_input.assert_called_once_with("HDMI1")
        assert "HDMI1" in result


# ── Scene ─────────────────────────────────────────────────────────────────────


class TestLoadScene:
    def test_loads_scene(self) -> None:
        client = _mock_client()
        with patch.object(mcp_server, "_client", return_value=client):
            result = mcp_server.load_scene(3)

        client.load_scene.assert_called_once_with(3)
        assert "3" in result


# ── Tuner ─────────────────────────────────────────────────────────────────────


class TestGetTunerStatus:
    def test_returns_tuner_dict(self) -> None:
        client = _mock_client()
        client.get_tuner_status.return_value = TunerStatus(
            band="FM", fm_freq_mhz=89.5, tuned=True
        )
        with patch.object(mcp_server, "_client", return_value=client):
            result = mcp_server.get_tuner_status()

        assert result["band"] == "FM"
        assert result["fm_freq_mhz"] == 89.5


class TestSetTunerBand:
    def test_fm(self) -> None:
        client = _mock_client()
        with patch.object(mcp_server, "_client", return_value=client):
            result = mcp_server.set_tuner_band("FM")

        client.set_tuner_band.assert_called_once_with("FM")
        assert "FM" in result

    def test_am(self) -> None:
        client = _mock_client()
        with patch.object(mcp_server, "_client", return_value=client):
            mcp_server.set_tuner_band("AM")

        client.set_tuner_band.assert_called_once_with("AM")


class TestSetTunerFreq:
    def test_fm_freq(self) -> None:
        client = _mock_client()
        with patch.object(mcp_server, "_client", return_value=client):
            result = mcp_server.set_tuner_fm_freq(104.6)

        client.set_tuner_fm_freq.assert_called_once_with(104.6)
        assert "104.60" in result

    def test_am_freq(self) -> None:
        client = _mock_client()
        with patch.object(mcp_server, "_client", return_value=client):
            result = mcp_server.set_tuner_am_freq(810)

        client.set_tuner_am_freq.assert_called_once_with(810)
        assert "810" in result

    def test_tuner_preset(self) -> None:
        client = _mock_client()
        with patch.object(mcp_server, "_client", return_value=client):
            result = mcp_server.set_tuner_preset(5)

        client.set_tuner_preset.assert_called_once_with(5)
        assert "5" in result


# ── Net Radio ─────────────────────────────────────────────────────────────────


class TestGetNetradioStatus:
    def test_returns_netradio_dict(self) -> None:
        client = _mock_client()
        client.get_netradio_status.return_value = NetRadioStatus(
            playback="Play", station="1LIVE"
        )
        with patch.object(mcp_server, "_client", return_value=client):
            result = mcp_server.get_netradio_status()

        assert result["playback"] == "Play"
        assert result["station"] == "1LIVE"


class TestPlayNetradioUrl:
    def test_with_title(self) -> None:
        client = _mock_client()
        with patch.object(mcp_server, "_client", return_value=client):
            result = mcp_server.play_netradio_url("http://stream.example.com/live", "1LIVE")

        client.play_netradio_url.assert_called_once_with(
            "http://stream.example.com/live", "1LIVE"
        )
        assert "1LIVE" in result

    def test_without_title_uses_url(self) -> None:
        client = _mock_client()
        url = "http://stream.example.com/live"
        with patch.object(mcp_server, "_client", return_value=client):
            result = mcp_server.play_netradio_url(url)

        assert url in result


class TestNetradioControl:
    def test_pause(self) -> None:
        client = _mock_client()
        with patch.object(mcp_server, "_client", return_value=client):
            result = mcp_server.pause_netradio()

        client.pause_netradio_url.assert_called_once()
        assert "pause" in result.lower()

    def test_stop(self) -> None:
        client = _mock_client()
        with patch.object(mcp_server, "_client", return_value=client):
            result = mcp_server.stop_netradio()

        client.stop_netradio_url.assert_called_once()
        assert "stop" in result.lower()


# ── Server structure ──────────────────────────────────────────────────────────


class TestServerStructure:
    def test_mcp_instance_exists(self) -> None:
        from fastmcp import FastMCP

        assert isinstance(mcp_server.mcp, FastMCP)

    async def test_tool_names_registered(self) -> None:
        tools = await mcp_server.mcp.list_tools()
        tool_names = {t.name for t in tools}
        expected = {
            "get_receiver_status",
            "set_power",
            "get_volume",
            "set_volume",
            "volume_up",
            "volume_down",
            "get_mute",
            "set_mute",
            "toggle_mute",
            "list_inputs",
            "set_input",
            "load_scene",
            "get_tuner_status",
            "set_tuner_band",
            "set_tuner_fm_freq",
            "set_tuner_am_freq",
            "set_tuner_preset",
            "get_netradio_status",
            "play_netradio_url",
            "pause_netradio",
            "stop_netradio",
        }
        assert expected.issubset(tool_names)
