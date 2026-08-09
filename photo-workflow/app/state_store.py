"""
Skript: app/state_store.py
Zweck: Speichert atomare, pro Batch hashverkettete Zustandsdateien.
Autor: MaiTaiMa
Erstellt: 2026-08-08
Version: 1.2
Requires: Python 3.11

Änderungsprotokoll:
  2026-08-08 | 1.1 | AP22.1 Header, Kommentare und Formatierung ergänzt
  2026-08-08 | 1.2 | State-Hash-Payload an die Validierung angeglichen
"""

from __future__ import annotations

# === Standardbibliothek ===
# Zweck: Erzeugt Hashes, JSON-Artefakte und atomare temporäre Dateien.
# Eingabe: Batch-ID, Workflowstatus und optionale Statusfelder.
# Ausgabe: Persistierter State-Record mit Zeitstempel und Hash.
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    """
    Gibt den aktuellen UTC-Zeitpunkt im ISO-8601-Format zurück.

    UTC verhindert lokale Zeitzonenmehrdeutigkeiten in State-Artefakten.
    Der Wert wird als unveränderlicher Zeitstempel des Schreibvorgangs verwendet.
    """
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _digest(payload: dict[str, Any]) -> str:
    """
    Berechnet einen reproduzierbaren SHA256-Hash eines State-Payloads.

    Wörterbuchschlüssel werden sortiert und JSON kompakt serialisiert.
    Der Hash wird aus dem Record ohne seinen eigenen Hashwert gebildet.
    """
    text = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class StateStore:
    """
    Verwaltet genau eine atomar ersetzte State-Datei pro Batch.

    Jeder neue Record enthält den Hash des vorherigen Records.
    Dadurch bleibt die zuletzt bekannte Zustandsfolge nachweisbar.
    """

    def __init__(self, root: str | Path):
        """
        Initialisiert den StateStore für einen Runtime-State-Ordner.

        Der Ordner wird erst beim ersten Schreibvorgang angelegt.
        Dadurch erzeugt das reine Lesen keine unbeabsichtigten Artefakte.
        """
        self.root = Path(root)

    def path_for(self, batch_id: str) -> Path:
        """
        Erzeugt den sicheren Dateinamen für eine Batch-ID.

        Pfadtrenner werden ersetzt, damit die Batch-ID nicht aus dem State-Root
        heraus navigieren kann.
        """
        safe = batch_id.replace("/", "_").replace("\\", "_")
        return self.root / f"{safe}.json"

    def read(self, batch_id: str) -> dict[str, Any] | None:
        """
        Liest den aktuellen State-Record eines Batches.

        Ein fehlender Record wird als None zurückgegeben.
        Die fachliche Hashvalidierung erfolgt durch state_validation.py.
        """
        path = self.path_for(batch_id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def write(
        self,
        batch_id: str,
        state: str,
        *,
        producer_version: str,
        reason: str | None = None,
        **fields: Any,
    ) -> dict[str, Any]:
        """
        Schreibt einen neuen State-Record atomar und hashverkettet.

        Der vollständige Inhalt wird zunächst in einer temporären Datei erzeugt.
        Erst nach Flush und fsync ersetzt os.replace den bisherigen gültigen Record.
        """
        previous = self.read(batch_id)
        record: dict[str, Any] = {
            "batch_id": batch_id,
            "state": state,
            "timestamp": _now(),
            "hash": "",
            "previous_state_hash": previous.get("hash") if previous else None,
            "producer_version": producer_version,
        }
        if reason is not None:
            record["reason"] = reason
        record.update(fields)

        unsigned = dict(record)
        unsigned.pop("hash")
        record["hash"] = _digest(unsigned)

        self._atomic_write(self.path_for(batch_id), record)
        return record

    @staticmethod
    def _atomic_write(path: Path, value: dict[str, Any]) -> None:
        """
        Ersetzt eine State-Datei atomar auf demselben Dateisystem.

        fsync stellt sicher, dass der temporäre Inhalt vor der Aktivierung
        an das Betriebssystem übergeben wurde.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(
            prefix=f".{path.name}.",
            dir=path.parent,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(value, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)