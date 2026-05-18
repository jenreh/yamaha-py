"""Tests for config loading and saving."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from yamactl.core.config import (
    get_default_profile,
    list_profiles,
    load_profile,
    save_profile,
    set_default_profile,
)
from yamactl.core.errors import ConfigError
from yamactl.core.models import ReceiverConfig


class TestLoadProfile:
    def test_loads_default(self, sample_config):
        cfg = load_profile()
        assert cfg.name == "test"
        assert cfg.host == "192.168.1.100"
        assert cfg.protocol == "http_xml"

    def test_loads_named(self, sample_config):
        cfg = load_profile("test")
        assert cfg.host == "192.168.1.100"

    def test_missing_config_file(self, tmp_config):
        with pytest.raises(ConfigError, match="No config found"):
            load_profile()

    def test_missing_profile(self, sample_config):
        with pytest.raises(ConfigError, match="not found"):
            load_profile("nonexistent")

    def test_no_default_profile(self, tmp_config):
        tmp_config.write_text(yaml.dump({"profiles": {"test": {"host": "1.2.3.4"}}}))
        with pytest.raises(ConfigError, match="No default_profile"):
            load_profile()

    def test_malformed_config(self, tmp_config):
        tmp_config.write_text("not: valid: yaml: [[[")
        with pytest.raises(ConfigError):
            load_profile()


class TestSaveProfile:
    def test_creates_new_profile(self, tmp_config):
        cfg = ReceiverConfig(name="living", host="192.168.0.1")
        save_profile(cfg, set_default=True)
        data = yaml.safe_load(tmp_config.read_text())
        assert data["profiles"]["living"]["host"] == "192.168.0.1"
        assert data["default_profile"] == "living"

    def test_updates_existing(self, sample_config):
        cfg = ReceiverConfig(name="test", host="10.0.0.1", protocol="ynca")
        save_profile(cfg)
        data = yaml.safe_load(sample_config.read_text())
        assert data["profiles"]["test"]["host"] == "10.0.0.1"
        assert data["profiles"]["test"]["protocol"] == "ynca"

    def test_preserves_other_profiles(self, sample_config):
        cfg = ReceiverConfig(name="office", host="10.0.0.2")
        save_profile(cfg)
        data = yaml.safe_load(sample_config.read_text())
        assert "test" in data["profiles"]
        assert "office" in data["profiles"]

    def test_creates_config_dir(self, tmp_config):
        cfg = ReceiverConfig(name="x", host="1.2.3.4")
        save_profile(cfg)
        assert tmp_config.exists()


class TestListProfiles:
    def test_returns_profile_names(self, sample_config):
        profiles = list_profiles()
        assert "test" in profiles

    def test_empty_when_no_config(self, tmp_config):
        profiles = list_profiles()
        assert profiles == {}


class TestSetDefaultProfile:
    def test_sets_default(self, sample_config):
        cfg = ReceiverConfig(name="other", host="10.0.0.1")
        save_profile(cfg)
        set_default_profile("other")
        assert get_default_profile() == "other"

    def test_missing_profile_raises(self, sample_config):
        with pytest.raises(ConfigError, match="not found"):
            set_default_profile("ghost")
