# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/phase1_runtime_budget_state.py
# PURPOSE:     Speichert atomare aktive Phase-1-Batch-Laufzeiten für sichere Resume-Limits.
# AUTHOR:      Matzethias
# DATE:        2026-08-20
# VERSION:     1.0.0
# REQUIRES:    Python 3.11
# CHANGES:
#   2026-08-20 | 1.0.0 | B2.1: Hashvalidierten State für aktive Batch-Zeit ergänzt.
# =============================================================================


from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class Phase1RuntimeBudgetStateError(ValueError):
    """Beschreibt ungültige persistierte aktive Batch-Laufzeiten."""


def _utc_now() -> str:
    """Liefert einen UTC-Zeitstempel im ISO-8601-Format."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


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


def _safe_batch_id(batch_id: str) -> None:
    """Blockiert leere Batch-IDs und Pfadtraversal im State-Pfad."""
    if not batch_id or Path(batch_id).name != batch_id or batch_id in {".", ".."}:
        raise Phase1RuntimeBudgetStateError("unsafe batch_id")


def _active_seconds(value: Any) -> float:
    """Validiert eine endliche, nicht negative aktive Laufzeit."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise Phase1RuntimeBudgetStateError(
            "active_seconds must be a non-negative number"
        )
    seconds = float(value)
    if not math.isfinite(seconds) or seconds < 0.0:
        raise Phase1RuntimeBudgetStateError(
            "active_seconds must be a finite non-negative number"
        )
    return seconds


class Phase1RuntimeBudgetStateStore:
    """Verwaltet atomare, hashvalidierte aktive Laufzeit je Phase-1-Batch."""

    def __init__(self, state_dir: str | Path, producer_version: str) -> None:
        """Initialisiert das kontrollierte Verzeichnis und die Produzentenversion."""
        self.state_dir = Path(state_dir)
        self.producer_version = producer_version

    def path_for(self, batch_id: str) -> Path:
        """Erzeugt den sicheren Pfad für genau einen Batch-Zeit-State."""
        _safe_batch_id(batch_id)
        return self.state_dir / f"{batch_id}.json"

    def load(self, batch_id: str) -> dict[str, Any] | None:
        """Lädt und validiert den State oder liefert None für unbekannte Batches."""
        path = self.path_for(batch_id)
        if not path.exists():
            return None
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise Phase1RuntimeBudgetStateError(
                f"invalid runtime budget state: {path}"
            ) from exc
        self.validate(record)
        return record

    def add_active_seconds(
        self,
        *,
        batch_id: str,
        seconds: float,
    ) -> dict[str, Any]:
        """Addiert eine vollständig abgeschlossene aktive Bildschritt-Dauer atomar."""
        increment = _active_seconds(seconds)
        current = self.load(batch_id)
        now = _utc_now()

        if current is None:
            record = {
                "schema_version": "1.0",
                "producer_version": self.producer_version,
                "batch_id": batch_id,
                "active_seconds": increment,
                "created_at": now,
                "updated_at": now,
                "previous_hash": "",
            }
        else:
            record = dict(current)
            record["active_seconds"] = (
                _active_seconds(current["active_seconds"]) + increment
            )
            record["updated_at"] = now
            record["previous_hash"] = current["hash"]

        record["hash"] = _digest(record)
        self.validate(record)
        self._atomic_write(self.path_for(batch_id), record)
        return record

    @staticmethod
    def validate(record: dict[str, Any]) -> None:
        """Prüft Pflichtfelder, sichere Batch-ID, Laufzeit und Hash-Integrität."""
        required = {
            "schema_version",
            "producer_version",
            "batch_id",
            "active_seconds",
            "created_at",
            "updated_at",
            "previous_hash",
            "hash",
        }
        if not isinstance(record, dict) or required - record.keys():
            raise Phase1RuntimeBudgetStateError(
                "runtime budget state is incomplete"
            )
        _safe_batch_id(record["batch_id"])
        _active_seconds(record["active_seconds"])
        if record["hash"] != _digest(record):
            raise Phase1RuntimeBudgetStateError(
                "runtime budget state hash mismatch"
            )

    @staticmethod
    def _atomic_write(path: Path, record: dict[str, Any]) -> None:
        """Schreibt, synchronisiert und aktiviert den State atomar."""
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(
            prefix=f".{path.name}.",
            dir=path.parent,
        )
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