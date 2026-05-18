"""Tests for domain models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from yamactl.core.models import (
    VOLUME_MAX,
    VOLUME_MIN,
    VOLUME_STEP,
    DiscoveryCandidate,
    ReceiverConfig,
    ReceiverStatus,
)


class TestReceiverConfig:
    def test_defaults(self) -> None:
        cfg = ReceiverConfig(name="test", host="192.168.1.1")
        assert cfg.protocol == "ynca"
        assert cfg.zone == "main"
        assert cfg.timeout_seconds == 3.0
        assert cfg.retries == 1
        assert cfg.port is None

    def test_invalid_protocol(self) -> None:
        with pytest.raises(ValidationError):
            ReceiverConfig(name="test", host="192.168.1.1", protocol="invalid")

    def test_invalid_zone(self) -> None:
        with pytest.raises(ValidationError):
            ReceiverConfig(name="test", host="192.168.1.1", zone="zone3")

    def test_zone2(self) -> None:
        cfg = ReceiverConfig(name="test", host="192.168.1.1", zone="zone2")
        assert cfg.zone == "zone2"

    def test_model_copy_update(self) -> None:
        cfg = ReceiverConfig(name="test", host="192.168.1.1")
        updated = cfg.model_copy(update={"host": "10.0.0.1"})
        assert updated.host == "10.0.0.1"
        assert cfg.host == "192.168.1.1"


class TestReceiverStatus:
    def test_minimal(self) -> None:
        s = ReceiverStatus(host="192.168.1.1")
        assert s.power is None
        assert s.mute is None
        assert s.raw == {}

    def test_full(self) -> None:
        s = ReceiverStatus(
            host="192.168.1.1",
            model="RX-V475",
            power="on",
            input="HDMI1",
            mute=False,
            volume_db=-45.0,
            dsp_mode="7ch Surround",
        )
        assert s.power == "on"
        assert s.volume_db == -45.0

    def test_json_roundtrip(self) -> None:
        s = ReceiverStatus(host="192.168.1.1", power="standby", volume_db=-50.0)
        dumped = s.model_dump_json()
        restored = ReceiverStatus.model_validate_json(dumped)
        assert restored.volume_db == -50.0


class TestDiscoveryCandidate:
    def test_confidence_high(self) -> None:
        c = DiscoveryCandidate(
            host="192.168.1.1", ynca_available=True, http_available=True
        )
        assert c.confidence == "high"

    def test_confidence_medium_ynca(self) -> None:
        c = DiscoveryCandidate(host="192.168.1.1", ynca_available=True)
        assert c.confidence == "medium"

    def test_confidence_medium_http(self) -> None:
        c = DiscoveryCandidate(host="192.168.1.1", http_available=True)
        assert c.confidence == "medium"

    def test_confidence_low(self) -> None:
        c = DiscoveryCandidate(host="192.168.1.1")
        assert c.confidence == "low"

    def test_protocol_prefers_ynca(self) -> None:
        c = DiscoveryCandidate(
            host="192.168.1.1", ynca_available=True, http_available=True
        )
        assert c.protocol == "ynca"

    def test_protocol_fallback_http(self) -> None:
        c = DiscoveryCandidate(host="192.168.1.1", http_available=True)
        assert c.protocol == "http_xml"


class TestVolumeConstants:
    def test_range(self) -> None:
        assert VOLUME_MIN == -80.5
        assert VOLUME_MAX == 16.5
        assert VOLUME_STEP == 0.5
