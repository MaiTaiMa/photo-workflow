# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/faces/face_proposal_reporting.py
# PURPOSE:     Photo Workflow Module
# AUTHOR:      Matzethias
# DATE:        2026-09-03
# VERSION:     1.2.0
# REQUIRES:    Python 3.11+
# CHANGES:
#   2026-09-07 | 1.1.0 | new_per_person gezaehlt; pending_per_person als Parameter.
#   2026-09-09 | 1.2.0 | P6: Parameter not_used_moved_per_person ergaenzt.
#   Initial version
# =============================================================================


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
    pending_per_person: Mapping[str, int] | None = None,
    not_used_moved_per_person: Mapping[str, int] | None = None,
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
    new_per_person: dict[str, int] = {}
    for item in registered:
        if (isinstance(item, Mapping)
                and isinstance(item.get("person_slug"), str)
                and item["person_slug"].strip()):
            slug = item["person_slug"].strip()
            new_per_person[slug] = new_per_person.get(slug, 0) + 1
    created = len(registered)
    if created:
        state = "proposals_created"
        reason = None
        action = "human_review_required_move_new_faces_to_reference"
    elif registration_result.get("skipped_count", 0):
        state = "no_candidates"
        reason = "all_candidates_skipped"
        action = "none"
    elif int(skipped_quality) > 0:
        state = "no_candidates"
        reason = "all_candidates_below_quality_threshold"
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
        "new_per_person": new_per_person,
        "pending_per_person": (
            dict(pending_per_person)
            if isinstance(pending_per_person, Mapping) else {}),
        "not_used_moved_per_person": (
            dict(not_used_moved_per_person)
            if isinstance(not_used_moved_per_person, Mapping) else {}),
        "reason": reason,
        "action": action,
    }


def format_registration_status_block(**kwargs: Any) -> str:
    """Format one visually separated status block for one batch."""
    return build_face_proposal_status_block(build_registration_status(**kwargs))
