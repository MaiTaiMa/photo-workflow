from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.faces.face_proposal_status import build_face_proposal_status_block


def build_registration_status(
    *,
    batch_id: str,
    registration_result: Mapping[str, Any],
    known_matches: int = 0,
    skipped_unknown: int = 0,
    skipped_ambiguous: int = 0,
    skipped_quality: int = 0,
    remaining_batch_slots: int = 0,
    remaining_global_slots: int = 0,
) -> dict[str, Any]:
    """Normalize registration results into a safe batch status payload."""
    registered = registration_result.get("registered", [])
    if not isinstance(registered, list):
        raise ValueError("registration_result.registered must be a list")
    people = sorted({
        str(item["person_slug"])
        for item in registered
        if isinstance(item, Mapping)
        and isinstance(item.get("person_slug"), str)
        and item["person_slug"].strip()
    })
    created = len(registered)
    if created:
        state = "proposals_created"
        reason = None
        action = "human_review_required_move_new_faces_to_reference"
    elif registration_result.get("skipped_count", 0):
        state = "no_candidates"
        reason = "all_candidates_skipped"
        action = "none"
    else:
        state = "no_candidates"
        reason = "no_eligible_known_faces"
        action = "none"
    return {
        "batch_id": batch_id,
        "status": state,
        "known_matches": int(known_matches),
        "eligible_candidates": created,
        "created_new": created,
        "pending_review": created,
        "skipped_unknown": int(skipped_unknown),
        "skipped_ambiguous": int(skipped_ambiguous),
        "skipped_quality": int(skipped_quality),
        "skipped_limits": int(registration_result.get("skipped_count", 0)),
        "remaining_batch_slots": int(remaining_batch_slots),
        "remaining_global_slots": int(remaining_global_slots),
        "people_with_new_proposals": people,
        "reason": reason,
        "action": action,
    }


def format_registration_status_block(**kwargs: Any) -> str:
    """Format one visually separated status block for one batch."""
    return build_face_proposal_status_block(build_registration_status(**kwargs))
