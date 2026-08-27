"""
Skript: app/phase_state.py
Zweck: Erzwingt erlaubte Phasen-Zustandsübergänge pro Batch.
Autor: MaiTaiMa
Erstellt: 2026-08-08
Version: 1.2.1
Requires: Python 3.11

Änderungsprotokoll:
  2026-08-08 | 1.1 | AP22.2 Header, Kommentare und Formatierung ergänzt
  2026-08-28 | 1.2 | Datei für zentrale Phasen-State-Logik umbenannt
  2026-08-28 | 1.2.1 | API-Kompatibilität und v1.2-Phase-2-Zustände korrigiert
"""

from __future__ import annotations

from typing import Any

from .state_store import StateStore


# === Zustandsgruppen ===
# Zweck: Trennt produktive Zustände von blockierenden Zuständen.
# Wirkung: Nur bekannte Zustände dürfen persistiert werden.
PHASE1_STATES = {
    "phase1_started",
    "phase1_moving",
    "phase1_completed",
}

PHASE2_STATES = {
    "phase2_started",
    "phase2_completed",
}

BLOCKING_STATES = {
    "quarantined",
    "review_state_invalid",
}

VALID_STATES = PHASE1_STATES | PHASE2_STATES | BLOCKING_STATES


# === Erlaubte Übergänge ===
# Zweck: Definiert den linearen Batch-Lebenszyklus für Phase 1 und Phase 2.
# Wirkung: Rückwärts- und unbekannte Übergänge werden fail-closed blockiert.
_ALLOWED = {
    "phase1_started": {
        "phase1_moving",
        "quarantined",
        "review_state_invalid",
    },
    "phase1_moving": {
        "phase1_completed",
        "quarantined",
        "review_state_invalid",
    },
    "phase1_completed": {
        "phase2_started",
    },
    "phase2_started": {
        "phase2_completed",
        "quarantined",
        "review_state_invalid",
    },
    "phase2_completed": set(),
    "quarantined": set(),
    "review_state_invalid": set(),
}


class PhaseTransitionError(ValueError):
    """
    Beschreibt einen unzulässigen Phasen-Zustandswechsel.

    Ein solcher Fehler blockiert den Batch und verhindert Folgeaktionen.
    """


# Öffentliche Kompatibilität für bestehende Phase-1-Aufrufer und Tests.
Phase1TransitionError = PhaseTransitionError


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
    Führt einen erlaubten Phasen-Übergang atomar aus.

    Der aktuelle Zustand wird zuerst gelesen und geprüft.
    Erst danach schreibt StateStore den neuen Zustand.
    """
    current = store.read(batch_id)
    current_state = current.get("state") if current else None

    if target not in VALID_STATES:
        raise PhaseTransitionError(f"Unknown phase state: {target}")

    if current_state is not None:
        allowed_targets = _ALLOWED.get(current_state, set())
        if target not in allowed_targets:
            raise PhaseTransitionError(
                f"Invalid phase transition: {current_state} -> {target}"
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
    Erzwingt den abgeschlossenen Phase-1-Zustand eines Batches.

    Die Prüfung ist das Gate für Phase 2 und nachgelagerte Operationen.
    """
    record = store.read(batch_id)
    if not record or record.get("state") != "phase1_completed":
        raise PhaseTransitionError(
            f"Batch is not phase1_completed: {batch_id}"
        )


def assert_phase2_completed(store: StateStore, batch_id: str) -> None:
    """
    Erzwingt den abgeschlossenen Phase-2-Zustand eines Batches.

    Die Prüfung ist das Gate für einen späteren Phase-3-Vertrag.
    """
    record = store.read(batch_id)
    if not record or record.get("state") != "phase2_completed":
        raise PhaseTransitionError(
            f"Batch is not phase2_completed: {batch_id}"
        )
