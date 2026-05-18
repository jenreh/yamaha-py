"""Shared pytest fixtures."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def tmp_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect config to a temp directory and return the config path."""
    config_file = tmp_path / "config.yaml"
    import yamactl.core.config as cfg_mod  # noqa: PLC0415

    monkeypatch.setattr(cfg_mod, "config_path", lambda: config_file)
    return config_file


@pytest.fixture
def sample_config(tmp_config: Path) -> Path:
    """Write a sample config with a 'test' profile."""
    data = {
        "default_profile": "test",
        "profiles": {
            "test": {
                "host": "192.168.1.100",
                "protocol": "http_xml",
                "zone": "main",
                "timeout_seconds": 1.0,
                "retries": 1,
            }
        },
    }
    tmp_config.write_text(yaml.dump(data))
    return tmp_config


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Skip rxv475 tests unless YAMACTL_TEST_HOST is set."""
    host = os.environ.get("YAMACTL_TEST_HOST")
    skip_real = pytest.mark.skip(
        reason="Set YAMACTL_TEST_HOST to run real-device tests"
    )
    for item in items:
        if "rxv475" in item.keywords and not host:
            item.add_marker(skip_real)
