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
