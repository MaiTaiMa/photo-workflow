"""Face-Proposal-Feature-Extractor.

Berechnet echte Qualitäts- und Nutzenmerkmale für Face-Vorschlä¬¬ge
anstatt fester Ersatzwerte.
"""

from __future__ import annotations

from typing import Any


def extract_face_proposal_features(row: dict[str, Any]) -> dict[str, float]:
    """Extrahiert Qualitäts- und Nutzenmerkmale aus einem Analyse-Row.

    Verwendet vorhandene Felder aus dem Row, um `quality_score` und
    `candidate_utility_score` zu berechnen. Fehlt ein Feld, wird ein
    konservativer Default verwendet.

    Args:
        row: Analyse-Row mit Face-Region-Metadaten.

    Returns:
        Dict mit den SchlÃ¼sseln:
        - face_area_ratio
        - sharpness_score
        - exposure_score
        - framing_score
        - diversity_score
        - robustness_score
        - quality_score
        - candidate_utility_score
    """
    face_area_ratio = float(row.get("face_area_ratio", 0.5))
    sharpness_score = float(row.get("sharpness_score", 0.5))
    exposure_score = float(row.get("exposure_score", 0.5))
    framing_score = float(row.get("framing_score", 0.5))

    diversity_score = float(row.get("diversity_score", 0.5))
    robustness_score = float(row.get("robustness_score", 0.5))

    quality_score = (
        0.30 * face_area_ratio
        + 0.25 * sharpness_score
        + 0.25 * exposure_score
        + 0.20 * framing_score
    )

    candidate_utility_score = (
        0.60 * quality_score
        + 0.25 * diversity_score
        + 0.15 * robustness_score
    )

    return {
        "face_area_ratio": face_area_ratio,
        "sharpness_score": sharpness_score,
        "exposure_score": exposure_score,
        "framing_score": framing_score,
        "diversity_score": diversity_score,
        "robustness_score": robustness_score,
        "quality_score": quality_score,
        "candidate_utility_score": candidate_utility_score,
    }
