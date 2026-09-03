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

from typing import Any


class FaceCandidateSelectionError(ValueError):
    """Beschreibt einen unzulässigen Face-Kandidaten."""


def select_face_candidates(
    candidates: list[dict[str, Any]],
    *,
    min_quality_score: float,
    max_count: int,
) -> list[dict[str, Any]]:
    """Filtert und priorisiert bereits bestätigte Face-Kandidaten."""
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
    return selected[:max_count]
