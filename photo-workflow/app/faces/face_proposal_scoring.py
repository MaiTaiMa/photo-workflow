# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/faces/face_proposal_scoring.py
# PURPOSE:     Photo Workflow Module
# AUTHOR:      Matzethias
# DATE:        2026-09-03
# VERSION:     1.0.0
# REQUIRES:    Python 3.11+
# CHANGES:
#   Initial version
# =============================================================================


from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


class FaceProposalScoringError(ValueError):
    """Beschreibt ungültige Eingaben für die Vorschlagsbewertung."""


def calculate_quality_score(
    *,
    face_confidence: float,
    face_area_ratio: float,
    sharpness_score: float,
    exposure_score: float,
    framing_score: float,
) -> float:
    """Calculate a transparent 0..1 technical crop quality score."""
    values = {
        "face_confidence": face_confidence,
        "face_area_ratio": face_area_ratio,
        "sharpness_score": sharpness_score,
        "exposure_score": exposure_score,
        "framing_score": framing_score,
    }
    normalized = {key: _unit(value, key) for key, value in values.items()}
    score = (
        0.30 * normalized["face_confidence"]
        + 0.25 * normalized["face_area_ratio"]
        + 0.20 * normalized["sharpness_score"]
        + 0.15 * normalized["exposure_score"]
        + 0.10 * normalized["framing_score"]
    )
    return round(score, 4)


def calculate_candidate_utility_score(
    *,
    quality_score: float,
    diversity_score: float,
    robustness_score: float,
    confidence_score: float,
) -> float:
    """Calculate transparent pool utility without persisting embeddings."""
    values = {
        "quality_score": quality_score,
        "diversity_score": diversity_score,
        "robustness_score": robustness_score,
        "confidence_score": confidence_score,
    }
    normalized = {key: _unit(value, key) for key, value in values.items()}
    score = (
        0.45 * normalized["quality_score"]
        + 0.25 * normalized["diversity_score"]
        + 0.20 * normalized["robustness_score"]
        + 0.10 * normalized["confidence_score"]
    )
    return round(score, 4)


def derive_basic_quality_features(
    *,
    face_confidence: float,
    face_area_ratio: float,
    sharpness_score: float,
    exposure_score: float,
    framing_score: float,
) -> dict[str, float]:
    """Return validated, non-sensitive quality features for auditability."""
    features = {
        "face_confidence": _unit(face_confidence, "face_confidence"),
        "face_area_ratio": _unit(face_area_ratio, "face_area_ratio"),
        "sharpness_score": _unit(sharpness_score, "sharpness_score"),
        "exposure_score": _unit(exposure_score, "exposure_score"),
        "framing_score": _unit(framing_score, "framing_score"),
    }
    features["quality_score"] = calculate_quality_score(**features)
    return features


def _unit(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise FaceProposalScoringError(f"{field} must be numeric")
    value = float(value)
    if not 0.0 <= value <= 1.0:
        raise FaceProposalScoringError(f"{field} must be between 0 and 1")
    return value
