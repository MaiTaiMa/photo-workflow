"""
Skript: app/pause_checkpoint.py
Zweck: Persistiert atomare und hashvalidierte Pause-Checkpoints je Batch.
Autor: MaiTaiMa
Erstellt: 2026-08-14
Version: 1.0.0
Requires: Python 3.11

Änderungsprotokoll:
  2026-08-14 | 1.0.0 | V12-02: Atomare Pause-Checkpoints ergänzt.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class PauseCheckpointError(ValueError):
    """Beschreibt einen ungültigen oder nicht integeren Pause-Checkpoint."""


def _utc_now() -> str:
    """Liefert einen UTC-Zeitstempel im ISO-8601-Format."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _digest(payload: dict[str, Any]) -> str:
    """Berechnet den SHA256 über den kanonischen Record ohne dessen eigenes Hash-Feld."""
    unsigned = dict(payload)
    unsigned.pop("hash", None)
    text = json.dumps(
        unsigned,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class PauseCheckpointStore:
    """Speichert pro Batch einen atomar ersetzten und hashvalidierten Pause-Checkpoint."""

    def __init__(self, state_dir: str | Path, producer_version: str) -> None:
        """Initialisiert State-Verzeichnis und Produzentenversion."""
        self.state_dir = Path(state_dir)
        self.producer_version = producer_version

    def path_for(self, batch_id: str) -> Path:
        """Erzeugt den sicheren Checkpoint-Pfad für eine unveränderliche Batch-ID."""
        if not batch_id or Path(batch_id).name != batch_id:
            raise PauseCheckpointError("unsafe batch_id")
        return self.state_dir / f"{batch_id}.pause.json"

    def write(
        self,
        *,
        batch_id: str,
        pause_reason: str,
        checkpoint: str,
        config_fingerprint: str,
        previous_state_hash: str,
        workunit_id: str | None = None,
    ) -> dict[str, Any]:
        """Schreibt einen vollständigen Pause-Checkpoint atomar auf demselben Dateisystem."""
        if not pause_reason or not checkpoint or not config_fingerprint:
            raise PauseCheckpointError("pause fields must be non-empty")
        record: dict[str, Any] = {
            "schema_version": "1.0",
            "producer_version": self.producer_version,
            "batch_id": batch_id,
            "state": "paused",
            "pause_reason": pause_reason,
            "checkpoint": checkpoint,
            "created_at": _utc_now(),
            "config_fingerprint": config_fingerprint,
            "previous_state_hash": previous_state_hash,
        }
        if workunit_id is not None:
            record["workunit_id"] = workunit_id
        record["hash"] = _digest(record)
        self._atomic_write(self.path_for(batch_id), record)
        return record

    def load(self, batch_id: str) -> dict[str, Any] | None:
        """Lädt und validiert einen Pause-Checkpoint oder liefert None, wenn keiner existiert."""
        path = self.path_for(batch_id)
        if not path.exists():
            return None
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise PauseCheckpointError(f"invalid pause checkpoint: {path}") from exc
        self.validate(record)
        return record

    @staticmethod
    def validate(record: dict[str, Any]) -> None:
        """Validiert Pflichtfelder, den Pause-State und die Hash-Integrität."""
        required = {
            "schema_version",
            "producer_version",
            "batch_id",
            "state",
            "pause_reason",
            "checkpoint",
            "created_at",
            "config_fingerprint",
            "previous_state_hash",
            "hash",
        }
        if not isinstance(record, dict) or required - record.keys():
            raise PauseCheckpointError("pause checkpoint is incomplete")
        if record["state"] != "paused":
            raise PauseCheckpointError("pause checkpoint state must be paused")
        if record["hash"] != _digest(record):
            raise PauseCheckpointError("pause checkpoint hash mismatch")

    @staticmethod
    def _atomic_write(path: Path, value: dict[str, Any]) -> None:
        """Schreibt erst temporär, synchronisiert und aktiviert dann per os.replace atomar."""
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)