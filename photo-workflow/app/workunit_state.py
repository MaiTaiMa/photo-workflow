"""
Skript: app/workunit_state.py
Zweck: Speichert atomare und hashvalidierte WorkUnit-Zustände je Batch.
Autor: MaiTaiMa
Erstellt: 2026-08-17
Version: 1.0.0
Requires: Python 3.11

Änderungsprotokoll:
  2026-08-17 | 1.0.0 | V12-04A: Persistente WorkUnit-Zustände ergänzt.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class WorkUnitStateError(ValueError):
    """Beschreibt einen ungültigen WorkUnit-Zustand oder Zustandsübergang."""


_ALLOWED_TRANSITIONS = {
    "pending": {"in_progress", "paused", "failed"},
    "in_progress": {"completed", "paused", "failed"},
    "paused": {"in_progress", "failed"},
    "completed": set(),
    "failed": {"pending", "in_progress"},
}


def _utc_now() -> str:
    """Liefert einen UTC-Zeitstempel im ISO-8601-Format."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _safe_identifier(value: str, field_name: str) -> str:
    """Blockiert leere Werte, Traversal und Pfadseparatoren in Artefakt-IDs."""
    if not value or Path(value).name != value or value in {".", ".."}:
        raise WorkUnitStateError(f"unsafe {field_name}")
    return value


def _digest(record: dict[str, Any]) -> str:
    """Berechnet den SHA256 über den kanonischen Record ohne eigenes Hash-Feld."""
    unsigned = dict(record)
    unsigned.pop("hash", None)
    payload = json.dumps(
        unsigned,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class WorkUnitStateStore:
    """Verwaltet atomare, pro WorkUnit hashverkettete Fortschrittszustände."""

    def __init__(self, root_dir: str | Path, producer_version: str) -> None:
        """Initialisiert das kontrollierte State-Verzeichnis und die Produzentenversion."""
        self.root_dir = Path(root_dir)
        self.producer_version = producer_version

    def path_for(self, batch_id: str, workunit_id: str) -> Path:
        """Erzeugt den sicheren State-Pfad einer WorkUnit innerhalb ihres Batches."""
        _safe_identifier(batch_id, "batch_id")
        _safe_identifier(workunit_id, "workunit_id")
        return self.root_dir / batch_id / f"{workunit_id}.json"

    def initialize(
        self,
        *,
        batch_id: str,
        workunit_id: str,
        image_names: tuple[str, ...],
        config_fingerprint: str,
    ) -> dict[str, Any]:
        """Erzeugt einen neuen pending-State und lässt vorhandene valide States unverändert."""
        if not image_names:
            raise WorkUnitStateError("workunit image_names must not be empty")
        if not config_fingerprint:
            raise WorkUnitStateError("config_fingerprint must not be empty")
        if any(Path(name).name != name for name in image_names):
            raise WorkUnitStateError("image_names must be plain file names")

        existing = self.load(batch_id, workunit_id)
        if existing is not None:
            if tuple(existing["image_names"]) != image_names:
                raise WorkUnitStateError("existing workunit image_names differ")
            if existing["config_fingerprint"] != config_fingerprint:
                raise WorkUnitStateError("existing workunit config fingerprint differs")
            return existing

        record = {
            "schema_version": "1.0",
            "producer_version": self.producer_version,
            "batch_id": batch_id,
            "workunit_id": workunit_id,
            "state": "pending",
            "image_names": list(image_names),
            "next_image_index": 0,
            "created_at": _utc_now(),
            "updated_at": _utc_now(),
            "config_fingerprint": config_fingerprint,
            "previous_state_hash": "",
        }
        record["hash"] = _digest(record)
        self._atomic_write(self.path_for(batch_id, workunit_id), record)
        return record

    def load(self, batch_id: str, workunit_id: str) -> dict[str, Any] | None:
        """Lädt und validiert einen WorkUnit-State oder liefert None für unbekannte WorkUnits."""
        path = self.path_for(batch_id, workunit_id)
        if not path.exists():
            return None
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise WorkUnitStateError(f"invalid workunit state: {path}") from exc
        self.validate(record)
        return record

    def transition(
        self,
        *,
        batch_id: str,
        workunit_id: str,
        new_state: str,
        next_image_index: int | None = None,
        reason: str | None = None,
    ) -> dict[str, Any]:
        """Führt einen erlaubten, atomar persistierten WorkUnit-Zustandsübergang aus."""
        current = self.load(batch_id, workunit_id)
        if current is None:
            raise WorkUnitStateError("workunit state is not initialized")
        if new_state not in _ALLOWED_TRANSITIONS.get(current["state"], set()):
            raise WorkUnitStateError(
                f"invalid transition: {current['state']} -> {new_state}"
            )

        image_count = len(current["image_names"])
        index = current["next_image_index"] if next_image_index is None else next_image_index
        if isinstance(index, bool) or not isinstance(index, int):
            raise WorkUnitStateError("next_image_index must be an integer")
        if not 0 <= index <= image_count:
            raise WorkUnitStateError("next_image_index is outside workunit range")
        if new_state == "completed" and index != image_count:
            raise WorkUnitStateError("completed workunit must have processed every image")

        record = dict(current)
        record["state"] = new_state
        record["next_image_index"] = index
        record["updated_at"] = _utc_now()
        record["previous_state_hash"] = current["hash"]
        if reason is not None:
            record["reason"] = reason
        record["hash"] = _digest(record)
        self._atomic_write(self.path_for(batch_id, workunit_id), record)
        return record

    def next_pending(self, batch_id: str) -> dict[str, Any] | None:
        """Liefert die erste nicht abgeschlossene WorkUnit in deterministischer Dateireihenfolge."""
        _safe_identifier(batch_id, "batch_id")
        batch_dir = self.root_dir / batch_id
        if not batch_dir.exists():
            return None
        for path in sorted(batch_dir.glob("*.json"), key=lambda value: value.name):
            record = self.load(batch_id, path.stem)
            if record is not None and record["state"] != "completed":
                return record
        return None

    @staticmethod
    def validate(record: dict[str, Any]) -> None:
        """Prüft Pflichtfelder, zulässigen State, Bildindex und Hash-Integrität."""
        required = {
            "schema_version",
            "producer_version",
            "batch_id",
            "workunit_id",
            "state",
            "image_names",
            "next_image_index",
            "created_at",
            "updated_at",
            "config_fingerprint",
            "previous_state_hash",
            "hash",
        }
        if not isinstance(record, dict) or required - record.keys():
            raise WorkUnitStateError("workunit state is incomplete")
        if record["state"] not in _ALLOWED_TRANSITIONS:
            raise WorkUnitStateError("workunit state is invalid")
        if not isinstance(record["image_names"], list) or not record["image_names"]:
            raise WorkUnitStateError("workunit image_names are invalid")
        if not isinstance(record["next_image_index"], int):
            raise WorkUnitStateError("workunit next_image_index is invalid")
        if not 0 <= record["next_image_index"] <= len(record["image_names"]):
            raise WorkUnitStateError("workunit next_image_index is outside range")
        if record["state"] == "completed" and record["next_image_index"] != len(record["image_names"]):
            raise WorkUnitStateError("completed workunit is incomplete")
        if record["hash"] != _digest(record):
            raise WorkUnitStateError("workunit hash mismatch")

    @staticmethod
    def _atomic_write(path: Path, record: dict[str, Any]) -> None:
        """Schreibt, synchronisiert und aktiviert den WorkUnit-State atomar auf demselben Dateisystem."""
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(record, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
