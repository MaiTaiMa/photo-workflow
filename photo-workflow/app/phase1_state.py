"""
Skript: app/phase1_state.py
Zweck: Erzwingt erlaubte PHASE1-Zustandsübergänge pro Batch.
Autor: MaiTaiMa
Erstellt: 2026-08-08
Version: 1.1
Requires: Python 3.11

Änderungsprotokoll:
  2026-08-08 | 1.1 | AP22.2 Header, Kommentare und Formatierung ergänzt
"""

from __future__ import annotations

# === Standardbibliothek ===
# Zweck: Typisiert optionale Übergangsfelder und Zustandsdaten.
# Eingabe: Zielzustand, Batch-ID und StateStore.
# Ausgabe: Atomarer State-Record oder ein blockierender Übergangsfehler.
from typing import Any

# === Fachmodule ===
# Zweck: Persistiert die hashverketteten Zustandswechsel.
# Voraussetzung: StateStore zeigt auf den zentralen Runtime-State-Ordner.
from .state_store import StateStore


# === Zustandsdefinition ===
# Zweck: Trennt reguläre PHASE1-Zustände von blockierenden Zuständen.
# Wirkung: Rückwärtsübergänge und unbekannte Zustände werden abgewiesen.
PHASE1_STATES = {"phase1_started", "phase1_moving", "phase1_completed"}
BLOCKING_STATES = {"quarantined", "review_state_invalid"}
_ALLOWED = {
    "phase1_started": {"phase1_moving", "quarantined", "review_state_invalid"},
    "phase1_moving": {"phase1_completed", "quarantined", "review_state_invalid"},
    "phase1_completed": set(),
    "quarantined": set(),
    "review_state_invalid": set(),
}


class Phase1TransitionError(ValueError):
    """
    Beschreibt einen unzulässigen PHASE1-Zustandswechsel.

    Ein solcher Fehler blockiert den Batch und verhindert Folgeaktionen.
    """


def transition(
    store: StateStore,
    batch_id: str,
    target: str,
    *,
    producer_version: str,
    reason: str | None = None,
    **fields: Any,
) -> dict[str, Any]:
    """
    Führt einen erlaubten PHASE1-Übergang atomar aus.

    Der aktuelle Zustand wird zuerst gelesen und gegen die Übergangstabelle geprüft.
    Erst danach schreibt der StateStore den neuen Zustand mit optionalem Grund.
    """
    current = store.read(batch_id)
    current_state = current.get("state") if current else None
    valid_states = PHASE1_STATES | BLOCKING_STATES
    if target not in valid_states:
        raise Phase1TransitionError(f"Unknown PHASE1 state: {target}")
    if current_state is not None and target not in _ALLOWED.get(current_state, set()):
        raise Phase1TransitionError(
            f"Invalid PHASE1 transition: {current_state} -> {target}"
        )
    return store.write(
        batch_id,
        target,
        producer_version=producer_version,
        reason=reason,
        **fields,
    )


def assert_phase1_completed(store: StateStore, batch_id: str) -> None:
    """
    Erzwingt den abgeschlossenen PHASE1-Zustand eines Batches.

    Die Prüfung ist ein Gate für PHASE2 und nachgelagerte Operationen.
    Jeder fehlende oder abweichende Zustand wird als Übergangsfehler gemeldet.
    """
    record = store.read(batch_id)
    if not record or record.get("state") != "phase1_completed":
        raise Phase1TransitionError(f"Batch is not phase1_completed: {batch_id}")
