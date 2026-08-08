from __future__ import annotations

from pathlib import Path

from .archive_verification import verify_zip_against_source
from .state_validation import validate_current_state


class Phase2GateError(RuntimeError):
    """Raised when ARW cleanup has not been safely authorized."""


def verify_phase2_manifest(manifest: dict) -> None:
    required = {"batch_id", "archive_path", "entry_count", "total_size", "entries",
                "config_fingerprint", "producer_version"}
    missing = required - manifest.keys()
    if missing:
        raise Phase2GateError(f"Missing archive manifest fields: {sorted(missing)}")
    if manifest["entry_count"] != len(manifest["entries"]):
        raise Phase2GateError("Archive entry count mismatch")
    if manifest["total_size"] != sum(int(entry["size"]) for entry in manifest["entries"]):
        raise Phase2GateError("Archive total size mismatch")


def authorize_arw_cleanup(state_store, batch_id: str, manifest: dict,
                          source_root: str | Path) -> list[Path]:
    state = validate_current_state(state_store, batch_id)
    if state.get("state") != "phase1_completed":
        raise Phase2GateError("ARW cleanup requires phase1_completed")
    verify_phase2_manifest(manifest)
    verify_zip_against_source(manifest["archive_path"], source_root, manifest["entries"])
    return [Path(source_root) / entry["relative_path"] for entry in manifest["entries"]
            if Path(entry["relative_path"]).suffix.lower() == ".arw"]
