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

# -----------------------------------------------------------------------------
# read_handoff_state
# Zweck: Liest den Handoff-State fuer einen Batch atomar mit Integritaetspruefung.
# -----------------------------------------------------------------------------
def read_handoff_state(batch_id: str, runtime_path: str | Path) -> dict[str, Any] | None:
    """Liest den Handoff-State fuer einen Batch.

    Returns den State als dict oder None, wenn die Datei nicht existiert
    oder die Integritaetspruefung (Hash) fehlschlaegt.
    """
    runtime_path = Path(runtime_path)
    state_dir = runtime_path / "handoff_states"
    final_path = state_dir / f"{batch_id}.handoff.json"

    if not final_path.exists():
        return None

    try:
        record = json.loads(final_path.read_text(encoding="utf-8"))
    except Exception:
        return None

    stored_hash = record.get("hash")
    record_for_hash = {k: v for k, v in record.items() if k != "hash"}
    payload = json.dumps(record_for_hash, sort_keys=True, separators=(",", ":"))
    expected_hash = "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()

    if stored_hash != expected_hash:
        return None

    return record
