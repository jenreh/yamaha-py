"""Tests for output formatters."""

from __future__ import annotations

import json

from yamactl.core.models import DiscoveryCandidate, ReceiverStatus
from yamactl.output.formatters import (
    candidates_to_plain,
    direct_confirmation,
    dsp_mode_confirmation,
    input_confirmation,
    mute_confirmation,
    power_confirmation,
    scene_confirmation,
    sleep_confirmation,
    status_to_dict,
    status_to_plain,
    straight_confirmation,
    volume_confirmation,
    volume_step_confirmation,
)


class TestStatusToPlain:
    def test_shows_volume_db(self) -> None:
        s = ReceiverStatus(host="192.168.1.1", power="on", volume_db=-45.0)
        result = status_to_plain(s)
        assert "-45.0 dB" in result

    def test_shows_muted(self) -> None:
        s = ReceiverStatus(host="192.168.1.1", mute=True)
        assert "muted" in status_to_plain(s)

    def test_shows_unmuted(self) -> None:
        s = ReceiverStatus(host="192.168.1.1", mute=False)
        assert "unmuted" in status_to_plain(s)

    def test_shows_dsp_mode(self) -> None:
        s = ReceiverStatus(host="192.168.1.1", dsp_mode="Hall in Munich")
        assert "Hall in Munich" in status_to_plain(s)

    def test_unknown_volume(self) -> None:
        s = ReceiverStatus(host="192.168.1.1")
        assert "unknown" in status_to_plain(s)


class TestStatusToDict:
    def test_serializable(self) -> None:
        s = ReceiverStatus(host="192.168.1.1", power="on", volume_db=-45.0)
        d = status_to_dict(s)
        json.dumps(d)  # should not raise

    def test_excludes_raw(self) -> None:
        s = ReceiverStatus(host="192.168.1.1", raw={"key": "val"})
        d = status_to_dict(s)
        assert "raw" not in d

    def test_includes_all_fields(self) -> None:
        s = ReceiverStatus(host="192.168.1.1", power="on", input="HDMI1")
        d = status_to_dict(s)
        assert d["power"] == "on"
        assert d["input"] == "HDMI1"


class TestConfirmationStrings:
    def test_power_confirmation_on(self) -> None:
        assert power_confirmation("on") == "Power: on"

    def test_power_confirmation_standby(self) -> None:
        assert power_confirmation("standby") == "Power: standby"

    def test_mute_confirmation_true(self) -> None:
        assert mute_confirmation(True) == "Mute: on"

    def test_mute_confirmation_false(self) -> None:
        assert mute_confirmation(False) == "Mute: off"

    def test_volume_confirmation(self) -> None:
        assert volume_confirmation(-35.0) == "Volume: -35.0 dB"

    def test_volume_confirmation_positive(self) -> None:
        assert volume_confirmation(0.0) == "Volume: +0.0 dB"

    def test_volume_step_up_one(self) -> None:
        result = volume_step_confirmation("up", 1)
        assert "up" in result
        assert "step" in result

    def test_volume_step_up_plural(self) -> None:
        result = volume_step_confirmation("up", 3)
        assert "steps" in result

    def test_input_confirmation(self) -> None:
        assert input_confirmation("HDMI1") == "Input: HDMI1"

    def test_dsp_mode_confirmation(self) -> None:
        assert dsp_mode_confirmation("Hall in Munich") == "DSP mode: Hall in Munich"

    def test_straight_on(self) -> None:
        assert straight_confirmation(True) == "Straight: on"

    def test_straight_off(self) -> None:
        assert straight_confirmation(False) == "Straight: off"

    def test_direct_on(self) -> None:
        assert direct_confirmation(True) == "Direct: on"

    def test_direct_off(self) -> None:
        assert direct_confirmation(False) == "Direct: off"

    def test_sleep_confirmation(self) -> None:
        assert sleep_confirmation("60") == "Sleep: 60"

    def test_scene_confirmation(self) -> None:
        assert scene_confirmation(2) == "Scene: loaded 2"


class TestCandidatesPlain:
    def test_shows_host(self) -> None:
        c = DiscoveryCandidate(host="192.168.1.100", ynca_available=True)
        result = candidates_to_plain([c])
        assert "192.168.1.100" in result

    def test_shows_ynca(self) -> None:
        c = DiscoveryCandidate(host="192.168.1.100", ynca_available=True)
        result = candidates_to_plain([c])
        assert "YNCA" in result

    def test_shows_http(self) -> None:
        c = DiscoveryCandidate(host="192.168.1.100", http_available=True)
        result = candidates_to_plain([c])
        assert "HTTP" in result

    def test_multiple_candidates(self) -> None:
        candidates = [
            DiscoveryCandidate(host="192.168.1.1", ynca_available=True),
            DiscoveryCandidate(host="192.168.1.2", http_available=True),
        ]
        result = candidates_to_plain(candidates)
        assert "192.168.1.1" in result
        assert "192.168.1.2" in result

    def test_status_plain_with_sleep(self) -> None:
        s = ReceiverStatus(host="192.168.1.1", sleep_minutes=60)
        result = status_to_plain(s)
        assert "sleep=60min" in result
