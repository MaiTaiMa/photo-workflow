from __future__ import annotations

from typing import Any

from app.faces.face_proposal_selection import select_face_candidates


class FaceProposalPipelineError(ValueError):
    """Beschreibt einen Fehler bei der Face-Vorschlagsauswahl."""


def persist_selected_face_proposals(
    selected: list[dict[str, Any]],
    *,
    pool_root: str,
    slug: str,
    limits: dict[str, int],
) -> list[dict[str, Any]]:
    """Registriert ausgewählte, bereits erzeugte Crops im Face-Pool."""
    from app.faces.proposal_contract import add_face_proposal

    persisted = []
    for candidate in selected:
        crop_path = candidate.get("crop_path")
        if not crop_path:
            raise FaceProposalPipelineError("candidate crop_path is missing")
        if not __import__("pathlib").Path(crop_path).is_file():
            raise FaceProposalPipelineError(
                f"candidate crop does not exist: {crop_path}"
            )

        persisted.append(
            add_face_proposal(
                pool_root=pool_root,
                slug=slug,
                source_id=candidate["source_id"],
                batch_id=candidate["batch_id"],
                crop_path=crop_path,
                original_path=candidate["original_path"],
                quality_score=candidate["quality_score"],
                candidate_utility_score=candidate[
                    "candidate_utility_score"
                ],
                bounding_box=candidate["bounding_box"],
                face_confidence=candidate["face_confidence"],
                limits=limits,
            )
        )

    return persisted


def select_available_face_proposals(
    candidates: list[dict[str, Any]],
    existing_entries: list[dict[str, Any]],
    *,
    batch_id: str,
    limits: dict[str, int],
    min_quality_score: float,
) -> list[dict[str, Any]]:
    """Filtert Kandidaten und wendet globale sowie Batch-Limits an."""
    if not isinstance(batch_id, str) or not batch_id.strip():
        raise FaceProposalPipelineError("batch_id must be a non-empty string")

    max_new = int(limits["max_new"])
    max_new_per_batch = int(limits["max_new_per_batch"])

    if max_new < 0:
        raise FaceProposalPipelineError("max_new must be non-negative")
    if max_new_per_batch < 1:
        raise FaceProposalPipelineError(
            "max_new_per_batch must be positive"
        )
    if max_new_per_batch > max_new:
        raise FaceProposalPipelineError(
            "max_new_per_batch must not exceed max_new"
        )

    new_entries = [
        entry for entry in existing_entries
        if entry.get("status") == "new"
    ]
    global_slots = max(0, max_new - len(new_entries))
    batch_slots = max(
        0,
        max_new_per_batch - sum(
            1
            for entry in new_entries
            if entry.get("batch_id") == batch_id
        ),
    )
    available = min(global_slots, batch_slots)

    return select_face_candidates(
        candidates,
        min_quality_score=min_quality_score,
        max_count=available,
    )
