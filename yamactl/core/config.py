"""YAML config management with named profiles."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml

from yamactl.core.errors import ConfigError
from yamactl.core.models import ReceiverConfig


def config_path() -> Path:
    return Path.home() / ".config" / "yamaha-local" / "config.yaml"


def _load_raw() -> dict[str, Any]:
    path = config_path()
    if not path.exists():
        raise ConfigError(
            f"No config found at {path}. Run: yamactl config init --name NAME --host IP"
        )
    try:
        with path.open() as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise ConfigError(f"Config at {path} is malformed: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(
            f"Config at {path} is malformed (expected mapping, got {type(data).__name__})"
        )
    return data


def load_profile(profile: str | None = None) -> ReceiverConfig:
    data = _load_raw()
    name = profile or data.get("default_profile")
    if not name:
        raise ConfigError(
            "No default_profile set. Pass --profile NAME or run: yamactl config init"
        )
    profiles = data.get("profiles", {})
    if name not in profiles:
        available = ", ".join(profiles.keys()) or "(none)"
        raise ConfigError(
            f"Profile '{name}' not found. Available profiles: {available}"
        )
    try:
        return ReceiverConfig(name=name, **profiles[name])
    except Exception as exc:
        raise ConfigError(f"Profile '{name}' is malformed: {exc}") from exc


def save_profile(cfg: ReceiverConfig, set_default: bool = False) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data: dict[str, Any] = {}
    if path.exists():
        with path.open() as f:
            data = yaml.safe_load(f) or {}
    if "profiles" not in data:
        data["profiles"] = {}
    data["profiles"][cfg.name] = cfg.model_dump(exclude={"name"})
    if set_default or "default_profile" not in data:
        data["default_profile"] = cfg.name
    with path.open("w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)


def list_profiles() -> dict[str, Any]:
    try:
        data = _load_raw()
    except ConfigError:
        return {}
    return cast(dict[str, Any], data.get("profiles", {}))


def get_default_profile() -> str | None:
    try:
        data = _load_raw()
    except ConfigError:
        return None
    return cast("str | None", data.get("default_profile"))


def set_default_profile(name: str) -> None:
    data = _load_raw()
    profiles = data.get("profiles", {})
    if name not in profiles:
        available = ", ".join(profiles.keys()) or "(none)"
        raise ConfigError(f"Profile '{name}' not found. Available: {available}")
    data["default_profile"] = name
    path = config_path()
    with path.open("w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
