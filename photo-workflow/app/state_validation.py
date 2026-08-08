"""
Skript: app/state_validation.py
Zweck: Validiert Pflichtfelder und Hashintegrität von State-Artefakten.
Autor: MaiTaiMa
Erstellt: 2026-08-08
Version: 1.1
Requires: Python 3.11

Änderungsprotokoll:
  2026-08-08 | 1.1 | AP22.1 Header, Kommentare und Formatierung ergänzt
"""

from __future__ import annotations

# === Standardbibliothek ===
# Zweck: Rekonstruiert State-Hashes und typisiert gelesene Records.
# Eingabe: StateStore und Batch-ID oder ein einzelner Record.
# Ausgabe: Validierter Record oder ein blockierender Validierungsfehler.
import hashlib
import json
from typing import Any

# === Fachmodule ===
# Zweck: Liest den aktuellen, pro Batch gespeicherten State.
# Voraussetzung: Der StateStore muss auf den Runtime-State zeigen.
from .state_store import StateStore


class StateValidationError(ValueError):
    """
    Beschreibt einen unvollständigen oder manipulierten State-Record.

    Der Fehler blockiert abhängige Phasen und jede potenziell destruktive Aktion.
    """


def validate_record(record: dict[str, Any]) -> None:
    """
    Prüft Pflichtfelder und den SHA256-Hash eines State-Records.

    Der erwartete Hash wird aus dem Record ohne das Feld `hash` berechnet.
    Eine Abweichung weist auf unvollständige oder manipulierte Steuerdaten hin.
    """
    required = {"batch_id", "state", "timestamp", "hash", "producer_version"}
    missing = required - record.keys()
    if missing:
        raise StateValidationError(f"Missing state fields: {sorted(missing)}")
    unsigned = dict(record)
    actual = unsigned.pop("hash")
    payload = json.dumps(
        unsigned,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    expected = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    if actual != expected:
        raise StateValidationError("State hash mismatch")


def validate_current_state(store: StateStore, batch_id: str) -> dict[str, Any]:
    """
    Liest und validiert den aktuellen State eines Batches.

    Ein fehlender Record und jeder Integritätsfehler werden als blockierender
    StateValidationError gemeldet, bevor eine Folgephase starten darf.
    """
    record = store.read(batch_id)
    if record is None:
        raise StateValidationError(f"State does not exist: {batch_id}")
    validate_record(record)
    return record
