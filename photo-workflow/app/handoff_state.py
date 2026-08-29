# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/handoff_state.py
# PURPOSE:     Atomarer Transition-State für automatic_handoff (Vertrag Abschnitt 6).
# AUTHOR:      Matzethias
# DATE:        2026-08-29
# VERSION:     1.0.0
# REQUIRES:    Python 3.11
# CHANGES:
#   2026-08-26 | 1.0.0 | Initial: Atomarer State-Write für Handoff.
# =============================================================================


import json
import hashlib
from pathlib import Path
from typing import Any, Mapping


def build_handoff_state(
    batch_id: str,
    config_fingerprint: str,
    producer_version: str,
    handoff_ok: bool,
    gate_reason: str | None = None,
) -> dict[str, Any]:
    """Build a deterministic handoff state record."""
    record = {
        "schema_version": "1.0",
        "producer_version": producer_version,
        "batch_id": batch_id,
        "config_fingerprint": config_fingerprint,
        "handoff_ok": handoff_ok,
        "gate_reason": gate_reason,
    }
    # Deterministischer Hash für Integritätsprüfung
    payload = json.dumps(record, sort_keys=True, separators=(",", ":"))
    record["hash"] = "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return record


def write_handoff_state_atomically(
    state_dir: Path,
    batch_id: str,
    config_fingerprint: str,
    producer_version: str,
    handoff_ok: bool,
    gate_reason: str | None = None,
) -> Path:
    """Schreibe den Handoff-State atomar (temp → final)."""
    state_dir.mkdir(parents=True, exist_ok=True)
    final_path = state_dir / f"{batch_id}.handoff.json"
    tmp_path = final_path.with_suffix(".json.tmp")

    record = build_handoff_state(batch_id, config_fingerprint, producer_version, handoff_ok, gate_reason)
    tmp_path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp_path.replace(final_path)  # atomar auf POSIX-Systemen
    return final_path