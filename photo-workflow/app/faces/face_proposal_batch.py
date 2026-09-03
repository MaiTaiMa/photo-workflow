from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from app.faces.face_crop_generator import create_square_face_crop
from app.faces.face_proposal_scoring import (
    calculate_candidate_utility_score,
    calculate_quality_score,
)


class FaceProposalBatchError(ValueError):
    """Beschreibt einen ungültigen Face-Vorschlagsbatch."""


def build_face_proposal_batch(
    rows: list[Mapping[str, Any]],
    *,
    batch_id: str,
    output_root: str | Path,
    min_quality_score: float = 0.65,
) -> dict[str, Any]:
    """Create only eligible known-face crops under ``new_faces``.

    This is an explicit integration boundary: no reference activation and no
    selection.json persistence happen here. Human activation is represented by
    moving a crop from new_faces to reference in a later workflow step.
    """
    if not isinstance(batch_id, str) or not batch_id.strip():
        raise FaceProposalBatchError("batch_id must be a non-empty string")
    if not 0.0 <= float(min_quality_score) <= 1.0:
        raise FaceProposalBatchError("min_quality_score must be between 0 and 1")

    root = Path(output_root)
    created: list[dict[str, Any]] = []
    counters = {
        "known_matches": 0,
        "eligible_candidates": 0,
        "created_new": 0,
        "skipped_unknown": 0,
        "skipped_ambiguous": 0,
        "skipped_quality": 0,
    }
    people: set[str] = set()

    for row in rows:
        if not isinstance(row, Mapping):
            raise FaceProposalBatchError("analysis row must be a mapping")
        if row.get("batch_id", batch_id) != batch_id:
            raise FaceProposalBatchError("analysis row batch_id mismatch")
        if row.get("known_person") is not True:
            counters["skipped_unknown"] += 1
            continue
        if row.get("ambiguous") is True:
            counters["skipped_ambiguous"] += 1
            continue

        person_slug = row.get("person_slug")
        image_path = row.get("original_path")
        box = row.get("bounding_box")
        confidence = row.get("face_confidence")
        if not isinstance(person_slug, str) or not person_slug.strip():
            counters["skipped_unknown"] += 1
            continue
        counters["known_matches"] += 1
        people.add(person_slug)

        quality = calculate_quality_score(
            face_confidence=confidence,
            face_area_ratio=row.get("face_area_ratio"),
            sharpness_score=row.get("sharpness_score"),
            exposure_score=row.get("exposure_score"),
            framing_score=row.get("framing_score"),
        )
        if quality < min_quality_score:
            counters["skipped_quality"] += 1
            continue

        counters["eligible_candidates"] += 1
        utility = calculate_candidate_utility_score(
            quality_score=quality,
            diversity_score=row.get("diversity_score", 0.5),
            robustness_score=row.get("robustness_score", 0.5),
            confidence_score=confidence,
        )
        source_id = row.get("source_id")
        if not isinstance(source_id, str) or not source_id.strip():
            raise FaceProposalBatchError("eligible candidate source_id is missing")
        face_index = row.get("face_index", 0)
        filename = f"{batch_id}__{Path(str(source_id)).stem}__face-{int(face_index):03d}.jpg"
        crop_path = root / person_slug / "new_faces" / filename
        create_square_face_crop(image_path, box, crop_path)
        created.append({
            "source_id": source_id,
            "batch_id": batch_id,
            "person_slug": person_slug,
            "path": f"new_faces/{filename}",
            "crop_path": str(crop_path),
            "original_path": str(image_path),
            "quality_score": quality,
            "candidate_utility_score": utility,
            "bounding_box": dict(box),
            "face_confidence": float(confidence),
            "status": "new",
        })
        counters["created_new"] += 1

    counters["people_with_new_proposals"] = sorted({
        item["person_slug"] for item in created
    })
    return {"batch_id": batch_id, "candidates": created, "counters": counters}
