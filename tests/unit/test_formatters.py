"""Tests for output formatters."""

from __future__ import annotations

import json

from yamactl.core.models import ReceiverStatus
from yamactl.output.formatters import status_to_dict, status_to_plain


class TestStatusToPlain:
    def test_shows_volume_db(self):
        s = ReceiverStatus(host="192.168.1.1", power="on", volume_db=-45.0)
        result = status_to_plain(s)
        assert "-45.0 dB" in result

    def test_shows_muted(self):
        s = ReceiverStatus(host="192.168.1.1", mute=True)
        assert "muted" in status_to_plain(s)

    def test_shows_unmuted(self):
        s = ReceiverStatus(host="192.168.1.1", mute=False)
        assert "unmuted" in status_to_plain(s)

    def test_shows_dsp_mode(self):
        s = ReceiverStatus(host="192.168.1.1", dsp_mode="Hall in Munich")
        assert "Hall in Munich" in status_to_plain(s)

    def test_unknown_volume(self):
        s = ReceiverStatus(host="192.168.1.1")
        assert "unknown" in status_to_plain(s)


class TestStatusToDict:
    def test_serializable(self):
        s = ReceiverStatus(host="192.168.1.1", power="on", volume_db=-45.0)
        d = status_to_dict(s)
        json.dumps(d)  # should not raise

    def test_excludes_raw(self):
        s = ReceiverStatus(host="192.168.1.1", raw={"key": "val"})
        d = status_to_dict(s)
        assert "raw" not in d

    def test_includes_all_fields(self):
        s = ReceiverStatus(host="192.168.1.1", power="on", input="HDMI1")
        d = status_to_dict(s)
        assert d["power"] == "on"
        assert d["input"] == "HDMI1"
