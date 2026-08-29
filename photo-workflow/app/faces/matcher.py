# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/faces/matcher.py
# PURPOSE:     Vergleicht flüchtige Face-Embeddings mit Referenzpersonen.
# AUTHOR:      Matzethias
# DATE:        2026-08-08
# VERSION:     1.3
# REQUIRES:    Python 3.11, NumPy
# CHANGES:
#   2026-08-08 | 1.2 | AP22 Face-Matching nach 98AP formatiert
#   2026-08-08 | 1.3 | Direkten RAM-Embedding-Vergleich ergänzt
# =============================================================================


from __future__ import annotations

# === Externe Abhängigkeiten ===
# Zweck: Normalisiert und vergleicht Face-Embedding-Vektoren.
# Eingabe: Backend-Embeddings und Referenzbildpfade oder RAM-Vektoren.
# Ausgabe: FaceMatch ohne persistente Embedding-Daten.
from pathlib import Path

import numpy as np

from .protocol import FaceMatch, validate_backend_info


class FaceMatcher:
    """Vergleicht Face-Embeddings mit flüchtigen Referenzpersonen."""

    def __init__(
        self,
        backend,
        threshold: float = 0.60,
        margin: float = 0.05,
    ):
        """Initialisiert Backend, Distanzschwelle und Ambiguitätsabstand."""
        validate_backend_info(backend.info)
        self.backend = backend
        self.threshold = float(threshold)
        self.margin = float(margin)
        self._references: dict[str, list[np.ndarray]] = {}

    @staticmethod
    def _normalise(value: object) -> np.ndarray:
        """Konvertiert einen Vektor in einen endlichen Einheitsvektor."""
        vector = np.asarray(value, dtype=np.float32).reshape(-1)
        if vector.size == 0 or not np.all(np.isfinite(vector)):
            raise ValueError("Embedding is empty or contains non-finite values")
        norm = float(np.linalg.norm(vector))
        if norm <= 0.0:
            raise ValueError("Embedding norm is zero")
        return vector / norm

    def add_reference(self, person_slug: str, image_path: str | Path) -> None:
        """Erzeugt und hält ein Referenz-Embedding ausschließlich im RAM."""
        vector = self._normalise(self.backend.embedding(str(image_path)))
        self._references.setdefault(person_slug, []).append(vector)

    def _match_query(self, query: np.ndarray) -> FaceMatch:
        """Vergleicht einen bereits erzeugten RAM-Vektor."""
        if not self._references:
            return FaceMatch(None, None, "no_reference_faces_loaded")

        candidates = []
        for person, references in self._references.items():
            distance = min(
                float(1.0 - np.dot(query, reference))
                for reference in references
            )
            candidates.append((distance, person))

        candidates.sort()
        best_distance, person = candidates[0]
        second_distance = candidates[1][0] if len(candidates) > 1 else 1.0
        margin = second_distance - best_distance

        if best_distance > self.threshold:
            return FaceMatch(None, None, "no_family_match", best_distance, margin)
        if margin < self.margin:
            return FaceMatch(None, None, "ambiguous_match", best_distance, margin)

        score = max(0.0, min(1.0, 1.0 - best_distance))
        return FaceMatch(person, score, "matched", best_distance, margin)

    def match_embedding(self, vector: object) -> FaceMatch:
        """Vergleicht ein flüchtiges Query-Embedding ohne erneutes Bildladen."""
        return self._match_query(self._normalise(vector))

    def match(self, image_path: str | Path) -> FaceMatch:
        """Erzeugt ein Bild-Embedding und vergleicht es mit den Referenzen."""
        return self.match_embedding(self.backend.embedding(str(image_path)))