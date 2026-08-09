from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class CapabilityReport:
    status: str
    authenticated: bool
    space: str
    write_rating: bool
    write_tags: bool
    write_known_persons: bool
    reason: str | None = None


class SynologyPhotosAdapter:
    """Capability-gated adapter; no private endpoint is guessed or called."""

    def __init__(self, config: dict):
        settings = config.get("synology_api", {})
        self.enabled = bool(settings.get("enabled", False))
        self.dry_run = bool(settings.get("dry_run", True))
        self.space = settings.get("space", "shared")
        self.write_rating = bool(settings.get("write_rating", True))
        self.write_tags = bool(settings.get("write_tags", True))
        self.write_known_persons = bool(settings.get("write_known_persons", False))

    def healthcheck(self) -> CapabilityReport:
        if self.space not in {"shared", "personal"}:
            return CapabilityReport("configuration_invalid", False, self.space,
                                    False, False, False, "invalid_space")
        if not self.enabled or self.dry_run:
            return CapabilityReport("dry_run", False, self.space,
                                    self.write_rating, self.write_tags, False)
        credentials = bool(os.getenv("SYNOLOGY_USER") and os.getenv("SYNOLOGY_PASSWORD"))
        return CapabilityReport("capability_probe_required", credentials, self.space,
                                False, False, False, "no_official_write_contract")

    def apply_metadata(self, *, relative_path: str, rating: int | None,
                       tags: list[str], person_slug: str | None = None) -> dict:
        report = self.healthcheck()
        if report.status != "ready":
            return {"status": "capability_unsupported", "relative_path": relative_path,
                    "reason": report.reason or report.status}
        if person_slug and not report.write_known_persons:
            return {"status": "capability_unsupported", "reason": "known_persons_disabled"}
        return {"status": "capability_unsupported", "reason": "adapter_not_implemented"}
