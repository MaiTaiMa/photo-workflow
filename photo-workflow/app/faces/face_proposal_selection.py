# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/faces/face_proposal_selection.py
# PURPOSE:     Photo Workflow Module
# AUTHOR:      Matzethias
# DATE:        2026-09-03
# VERSION:     1.0.0
# REQUIRES:    Python 3.11+
# CHANGES:
#   Initial version
# =============================================================================


from __future__ import annotations

import math
from typing import Any


class FaceCandidateSelectionError(ValueError):
    """Beschreibt einen unzulässigen Face-Kandidaten."""


def select_face_candidates(
    candidates: list[dict[str, Any]],
    *,
    min_quality_score: float,
    max_count: int,
    min_candidate_distance: float | None = None,
) -> list[dict[str, Any]]:
    """Filtert und priorisiert bereits bestätigte Face-Kandidaten.

    Bei min_candidate_distance (Default None) werden Kandidaten mit Embedding-Vektor
    nur gewählt, wenn ihre Cosine-Distanz zu allen bereits gewählten Kandidaten
    >= Schwellwert ist. Ohne Vektor oder None = altes Verhalten."""
    if not 0 <= float(min_quality_score) <= 1:
        raise FaceCandidateSelectionError(
            "min_quality_score must be between 0 and 1"
        )
    if max_count < 0:
        raise FaceCandidateSelectionError("max_count must be non-negative")

    selected = []
    for candidate in candidates:
        if candidate.get("known_person") is not True:
            continue
        if candidate.get("human_decision") != "keep":
            continue

        quality = candidate.get("quality_score")
        utility = candidate.get("candidate_utility_score")
        if not isinstance(quality, (int, float)):
            continue
        if not isinstance(utility, (int, float)):
            continue
        if not 0 <= float(quality) <= 1:
            continue
        if not 0 <= float(utility) <= 1:
            continue
        if float(quality) < float(min_quality_score):
            continue

        selected.append(candidate)

    selected.sort(
        key=lambda candidate: (
            -float(candidate["candidate_utility_score"]),
            str(candidate.get("source_id", "")),
        )
    )

    # Diversitaetsfilter (greedy, Cosine-Distanz)
    if min_candidate_distance is not None and min_candidate_distance > 0:
        def cosine_distance(a, b):
            # a, b: Listen von floats; Schutz vor leeren/None Vektoren
            if not a or not b or len(a) != len(b):
                return 0.0
            num = sum(x * y for x, y in zip(a, b))
            den_a = math.sqrt(sum(x * x for x in a)) or 1e-12
            den_b = math.sqrt(sum(x * x for x in b)) or 1e-12
            return 1.0 - (num / (den_a * den_b))  # uses module-level math

        diverse = []
        for cand in selected:
            emb = cand.get("embedding")
            if emb is None:
                # Kein Vektor -> wie bisher akzeptieren
                diverse.append(cand)
                continue
            ok = True
            for chosen in diverse:
                chosen_emb = chosen.get("embedding")
                if chosen_emb is None:
                    continue
                if cosine_distance(emb, chosen_emb) < float(min_candidate_distance):
                    ok = False
                    break
            if ok:
                diverse.append(cand)
        selected = diverse

    return selected[:max_count]
