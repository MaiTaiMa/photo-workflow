from __future__ import annotations

from pathlib import Path

import numpy as np

from .protocol import FaceMatch, validate_backend_info


class FaceMatcher:
    def __init__(self, backend, threshold: float = 0.60, margin: float = 0.05):
        validate_backend_info(backend.info)
        self.backend = backend
        self.threshold = float(threshold)
        self.margin = float(margin)
        self._references: dict[str, list[np.ndarray]] = {}

    def add_reference(self, person_slug: str, image_path: str | Path) -> None:
        vector = np.asarray(self.backend.embedding(str(image_path)), dtype=np.float32)
        norm = np.linalg.norm(vector)
        if not norm:
            raise ValueError("Reference embedding is empty")
        self._references.setdefault(person_slug, []).append(vector / norm)

    def match(self, image_path: str | Path) -> FaceMatch:
        if not self._references:
            return FaceMatch(None, None, "no_reference_faces_loaded")
        query = np.asarray(self.backend.embedding(str(image_path)), dtype=np.float32)
        query /= max(np.linalg.norm(query), 1e-12)
        candidates = []
        for person, references in self._references.items():
            distance = min(float(1.0 - np.dot(query, reference))
                           for reference in references)
            candidates.append((distance, person))
        candidates.sort()
        best_distance, person = candidates[0]
        second_distance = candidates[1][0] if len(candidates) > 1 else 1.0
        margin = second_distance - best_distance
        if best_distance > self.threshold:
            return FaceMatch(None, None, "no_family_match", best_distance, margin)
        if margin < self.margin:
            return FaceMatch(None, None, "ambiguous_match", best_distance, margin)
        return FaceMatch(person, max(0.0, min(1.0, 1.0 - best_distance)),
                         "matched", best_distance, margin)
