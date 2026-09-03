from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from app.faces.proposal_contract import add_face_proposal


class FaceProposalRegistrationError(ValueError):
    """Beschreibt einen ungültigen Vorschlag für die Selection-Registrierung."""


def register_face_proposals(
    candidates: list[Mapping[str, Any]],
    *,
    pool_root: str | Path,
    limits: Mapping[str, int],
) -> dict[str, Any]:
    """Register selected existing crops atomically through the P5 contract.

    The function never moves files to reference. Every candidate must already
    point to a crop below ``new_faces``. Selection limits are enforced by the
    canonical proposal contract.
    """
    selected: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    for candidate in sorted(candidates, key=lambda item: str(item.get("source_id", ""))):
        try:
            entry = add_face_proposal(
                pool_root=Path(pool_root) / _required(candidate, "person_slug"),
                slug=_required(candidate, "person_slug"),
                source_id=_required(candidate, "source_id"),
                batch_id=_required(candidate, "batch_id"),
                crop_path=_required(candidate, "crop_path"),
                original_path=_required(candidate, "original_path"),
                quality_score=candidate["quality_score"],
                candidate_utility_score=candidate["candidate_utility_score"],
                bounding_box=candidate["bounding_box"],
                face_confidence=candidate["face_confidence"],
                limits=dict(limits),
            )
        except Exception as error:
            skipped.append({
                "source_id": str(candidate.get("source_id", "")),
                "reason": str(error),
            })
            continue
        selected.append(entry)
    return {
        "registered": selected,
        "registered_count": len(selected),
        "skipped": skipped,
        "skipped_count": len(skipped),
        "activation_required": bool(selected),
    }


def _required(candidate: Mapping[str, Any], key: str) -> str:
    value = candidate.get(key)
    if not isinstance(value, str) or not value.strip():
        raise FaceProposalRegistrationError(f"candidate {key} is missing")
    return value
