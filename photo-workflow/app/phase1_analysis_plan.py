"""
Skript: app/phase1_analysis_plan.py
Zweck: Speichert atomare, secrets-freie Phase-1-Analysepläne je Batch.
Autor: MaiTaiMa
Erstellt: 2026-08-17
Version: 1.0.0
Requires: Python 3.11

Änderungsprotokoll:
  2026-08-17 | 1.0.0 | V12-04A1: Persistenten Analyseplan-Store ergänzt.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class Phase1AnalysisPlanError(ValueError):
    """Beschreibt einen ungültigen Phase-1-Analyseplan."""


_FORBIDDEN_KEYS = {
    "embedding", "embeddings", "image_bytes", "image_data", "secret",
    "token", "session_token", "password", "api_key",
}


def _utc_now() -> str:
    """Liefert einen UTC-Zeitstempel im ISO-8601-Format."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _digest(value: dict[str, Any]) -> str:
    """Berechnet den SHA256 über den kanonischen Plan ohne eigenes Hash-Feld."""
    unsigned = dict(value)
    unsigned.pop("hash", None)
    payload = json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _safe_identifier(value: str, field_name: str) -> None:
    """Blockiert Traversal und unzulässige Batch- oder WorkUnit-IDs."""
    if not value or Path(value).name != value or value in {".", ".."}:
        raise Phase1AnalysisPlanError(f"unsafe {field_name}")


def _reject_forbidden(value: Any, location: str = "$") -> None:
    """Lehnt interne und sicherheitskritische persistierte Felder rekursiv ab."""
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            if key_text.startswith("_") or key_text.casefold() in _FORBIDDEN_KEYS:
                raise Phase1AnalysisPlanError(f"forbidden plan field: {location}.{key_text}")
            _reject_forbidden(child, f"{location}.{key_text}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_forbidden(child, f"{location}[{index}]")


class Phase1AnalysisPlanStore:
    """Verwaltet atomare und hashvalidierte Analysepläne vor WorkUnit-Ausführung."""

    def __init__(self, plan_dir: str | Path, producer_version: str) -> None:
        """Initialisiert das kontrollierte Plan-Verzeichnis und die Produzentenversion."""
        self.plan_dir = Path(plan_dir)
        self.producer_version = producer_version

    def path_for(self, batch_id: str) -> Path:
        """Erzeugt den sicheren Artefaktpfad für genau einen Batch."""
        _safe_identifier(batch_id, "batch_id")
        return self.plan_dir / f"{batch_id}.json"

    def write(self, *, batch_id: str, rows: list[dict[str, Any]], workunits: list[dict[str, Any]], config_fingerprint: str) -> dict[str, Any]:
        """Validiert und schreibt den vollständigen batchweiten Analyseplan atomar."""
        if not config_fingerprint:
            raise Phase1AnalysisPlanError("config_fingerprint must not be empty")
        self._validate_rows_and_workunits(rows, workunits)
        record = {
            "schema_version": "1.0", "producer_version": self.producer_version,
            "batch_id": batch_id, "created_at": _utc_now(),
            "config_fingerprint": config_fingerprint, "rows": rows, "workunits": workunits,
        }
        _reject_forbidden(record)
        record["hash"] = _digest(record)
        self._atomic_write(self.path_for(batch_id), record)
        return record

    def load(self, batch_id: str) -> dict[str, Any] | None:
        """Lädt und validiert einen Analyseplan oder liefert None, wenn keiner existiert."""
        path = self.path_for(batch_id)
        if not path.exists():
            return None
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise Phase1AnalysisPlanError(f"invalid analysis plan: {path}") from exc
        self.validate(record)
        return record

    @staticmethod
    def validate(record: dict[str, Any]) -> None:
        """Prüft Pflichtfelder, Sicherheitsgrenzen, Zuordnung und Hash-Integrität."""
        required = {"schema_version", "producer_version", "batch_id", "created_at", "config_fingerprint", "rows", "workunits", "hash"}
        if not isinstance(record, dict) or required - record.keys():
            raise Phase1AnalysisPlanError("analysis plan is incomplete")
        _safe_identifier(record["batch_id"], "batch_id")
        _reject_forbidden({key: value for key, value in record.items() if key != "hash"})
        Phase1AnalysisPlanStore._validate_rows_and_workunits(record["rows"], record["workunits"])
        if record["hash"] != _digest(record):
            raise Phase1AnalysisPlanError("analysis plan hash mismatch")

    @staticmethod
    def _validate_rows_and_workunits(rows: Any, workunits: Any) -> None:
        """Prüft, dass jede geplante Datei genau einer Analyse-Row entspricht."""
        if not isinstance(rows, list) or not isinstance(workunits, list):
            raise Phase1AnalysisPlanError("rows and workunits must be lists")
        row_files = set()
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("file"), str):
                raise Phase1AnalysisPlanError("analysis row requires file")
            if Path(row["file"]).name != row["file"]:
                raise Phase1AnalysisPlanError("analysis row file must be a plain name")
            row_files.add(row["file"])
        planned_files = []
        for unit in workunits:
            if not isinstance(unit, dict):
                raise Phase1AnalysisPlanError("workunit must be a mapping")
            _safe_identifier(unit.get("workunit_id", ""), "workunit_id")
            names = unit.get("image_names")
            if not isinstance(names, list) or not names:
                raise Phase1AnalysisPlanError("workunit requires image_names")
            planned_files.extend(names)
        if len(planned_files) != len(set(planned_files)):
            raise Phase1AnalysisPlanError("workunit image_names must be unique")
        if set(planned_files) != row_files:
            raise Phase1AnalysisPlanError("workunit image_names must match analysis rows")

    @staticmethod
    def _atomic_write(path: Path, record: dict[str, Any]) -> None:
        """Schreibt, synchronisiert und aktiviert den Analyseplan atomar."""
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
