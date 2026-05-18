"""Real-device integration tests.

Run with: YAMACTL_TEST_HOST=192.168.178.42 pytest -m rxv475
"""

from __future__ import annotations

import os

import pytest

from yamactl.protocols.ync_http import YncHttpProtocol
from yamactl.protocols.ynca_tcp import YncaTcpProtocol

HOST = os.environ.get("YAMACTL_TEST_HOST", "")


@pytest.fixture
def proto_http() -> YncHttpProtocol:
    return YncHttpProtocol(host=HOST, timeout=5.0)


@pytest.fixture
def proto_ynca() -> YncaTcpProtocol:
    return YncaTcpProtocol(host=HOST, timeout=5.0)


@pytest.mark.rxv475
class TestHttpStatus:
    def test_get_status_returns_data(self, proto_http) -> None:
        with proto_http as p:
            status = p.get_status()
        assert status.host == HOST
        assert status.power in ("on", "standby")

    def test_get_mute_returns_bool(self, proto_http) -> None:
        with proto_http as p:
            mute = p.get_mute()
        assert isinstance(mute, bool)

    def test_get_volume_in_range(self, proto_http) -> None:
        from yamactl.core.models import VOLUME_MAX, VOLUME_MIN  # noqa: PLC0415

        with proto_http as p:
            vol = p.get_volume_db()
        assert VOLUME_MIN <= vol <= VOLUME_MAX

    def test_list_inputs_nonempty(self, proto_http) -> None:
        with proto_http as p:
            inputs = p.list_inputs()
        assert len(inputs) > 0


@pytest.mark.rxv475
class TestYncaStatus:
    def test_get_status_returns_data(self, proto_ynca) -> None:
        with proto_ynca as p:
            status = p.get_status()
        assert status.power in ("on", "standby")

    def test_get_volume_in_range(self, proto_ynca) -> None:
        from yamactl.core.models import VOLUME_MAX, VOLUME_MIN  # noqa: PLC0415

        with proto_ynca as p:
            vol = p.get_volume_db()
        assert VOLUME_MIN <= vol <= VOLUME_MAX


@pytest.mark.rxv475
@pytest.mark.rxv475_destructive
class TestHttpDestructive:
    def test_mute_toggle_and_restore(self, proto_http) -> None:
        with proto_http as p:
            original = p.get_mute()
            p.set_mute(not original)
            changed = p.get_mute()
            p.set_mute(original)
            restored = p.get_mute()
        assert changed == (not original)
        assert restored == original
