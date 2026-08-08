from __future__

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml


class ConfigError(ValueError):
    """Raised when the workflow configuration violates the baseline schema."""


def _canonical(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _canonical(value[k]) for k in sorted(value)}
    if isinstance(value, list):
        return [_canonical(item) for item in value]
    return value


def config_fingerprint(config: dict[str, Any]) -> str:
    payload = json.dumps(_canonical(config), ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_config(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    try:
        value = yaml.safe_load(source.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(f"Cannot read configuration: {source}") from exc
    if not isinstance(value, dict):
        raise ConfigError("Configuration root must be a mapping")
    validate_config(value)
    return value


def validate_config(config: dict[str, Any]) -> None:
    required = {"paths", "safety"}
    missing = sorted(required - config.keys())
    if missing:
        raise ConfigError(f"Missing top-level sections: {', '.join(missing)}")
    paths = config["paths"]
    safety = config["safety"]
    if not isinstance(paths, dict) or not isinstance(safety, dict):
        raise ConfigError("paths and safety must be mappings")
    base = paths.get("basedir", paths.get("base_dir"))
    if not base:
        raise ConfigError("paths.basedir or paths.base_dir is required")
    if not isinstance(base, str):
        raise ConfigError("paths.basedir must be a string")
    for key in ("require_paths_within_base_dir", "follow_symlinks"):
        if key in safety and not isinstance(safety[key], bool):
            raise ConfigError(f"safety.{key} must be boolean")
    if "extensions" in config and not isinstance(config["extensions"], dict):
        raise ConfigError("extensions must be a mapping")


def effective_base_dir(config: dict[str, Any]) -> Path:
    validate_config(config)
    return Path(config["paths"].get("basedir", config["paths"].get("base_dir"))).expanduser()
