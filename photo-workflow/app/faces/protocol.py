# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/faces/protocol.py
# PURPOSE:     Definiert Metadaten und Schnittstellen lokaler Face-Backends.
# AUTHOR:      Matzethias
# DATE:        2026-08-08
# VERSION:     1.2
# REQUIRES:    Python 3.11
# CHANGES:
#   2026-08-08 | 1.2 | AP22 Face-Backend-Verträge nach 98AP formatiert
# =============================================================================


from __future__ import annotations

# === Standardbibliothek ===
# Zweck: Definiert unveränderliche Backend-Metadaten und Protokolle.
# Eingabe: Adapterinformationen und Face-Match-Ergebnisse.
# Ausgabe: Typisierte Verträge für Face-Adapter und Matcher.
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class BackendInfo:
    """Beschreibt ein Face-Backend und seine reproduzierbare Verarbeitung."""

    registry_id: str
    adapter_name: str
    model_hash: str
    provider: str
    preprocessing: str
    metric: str
    selection_fingerprint: str


@dataclass(frozen=True)
class FaceMatch:
    """Beschreibt das Ergebnis eines Personenvergleichs."""

    person_slug: str | None
    family_score: float | None
    status: str
    distance: float | None = None
    margin: float | None = None


class FaceBackend(Protocol):
    """Minimales Protokoll für einen flüchtigen Face-Embedding-Adapter."""

    info: BackendInfo

    def embedding(self, image_path: str) -> object:
        """Erzeugt ein Embedding ohne persistente Bild- oder Vektordaten."""
        ...


def validate_backend_info(info: BackendInfo) -> None:
    """
    Prüft die Pflichtmetadaten eines Face-Backends.

    Unvollständige Backendinformationen blockieren den Personenvergleich.
    Modell- und Auswahlfingerprints dienen der Nachvollziehbarkeit.
    """
    values = (
        info.registry_id,
        info.adapter_name,
        info.model_hash,
        info.provider,
        info.preprocessing,
        info.metric,
        info.selection_fingerprint,
    )
    if not all(values):
        raise ValueError("Face backend metadata is incomplete")