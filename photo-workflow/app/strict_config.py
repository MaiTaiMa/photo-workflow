from __future__ import annotations

import os

from .config_schema import ConfigError, validate_config


class StrictConfigError(ConfigError):
    """Raised when operational configuration violates a safety gate."""


def validate_strict_config(config: dict) -> None:
    validate_config(config)
    paths = config["paths"]
    if config.get("finalization", {}).get("enabled", False):
        publish = config.get("finalization", {}).get("publish_to_synology_photos", {})
        if not paths.get("publish_root") or not publish.get("target_folder"):
            raise StrictConfigError("finalization requires publish_root and target_folder")
    api = config.get("synology_api", config.get("finalization", {}).get("synology_api", {}))
    if api.get("space", "shared") not in {"shared", "personal"}:
        raise StrictConfigError("synology_api.space must be shared or personal")
    if api.get("write_known_persons", False) and not api.get("pilot_approved", False):
        raise StrictConfigError("known-person writes require explicit pilot_approved")
    if api.get("enabled", False) and not api.get("dry_run", True):
        if not os.getenv("SYNOLOGY_USER") or not os.getenv("SYNOLOGY_PASSWORD"):
            raise StrictConfigError("active Synology API requires environment credentials")


def assert_no_secret_values(config: dict) -> None:
    text = repr(config).lower()
    for marker in ("password", "token", "session", "secret", "api_key"):
        if marker in text and marker not in {"password"}:
            raise StrictConfigError(f"Possible secret in configuration: {marker}")
