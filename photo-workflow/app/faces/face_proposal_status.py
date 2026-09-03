from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class FaceProposalStatusError(ValueError):
    """Beschreibt einen ungültigen Face-Proposal-Status."""


def build_face_proposal_status_block(status: Mapping[str, Any]) -> str:
    """Format one visually separated, human-readable proposal status block."""
    if not isinstance(status, Mapping):
        raise FaceProposalStatusError("status must be a mapping")

    batch_id = _required_text(status, "batch_id")
    state = _required_text(status, "status")
    allowed = {
        "no_candidates",
        "proposals_created",
        "existing_pending",
        "limit_reached",
        "activation_detected",
        "blocked",
    }
    if state not in allowed:
        raise FaceProposalStatusError(f"unsupported status: {state}")

    people = _people(status.get("people_with_new_proposals", []))

    fields = (
        ("known_matches", _count(status, "known_matches")),
        ("eligible_candidates", _count(status, "eligible_candidates")),
        ("created_new", _count(status, "created_new")),
        ("pending_review", _count(status, "pending_review")),
        ("skipped_unknown", _count(status, "skipped_unknown")),
        ("skipped_ambiguous", _count(status, "skipped_ambiguous")),
        ("skipped_quality", _count(status, "skipped_quality")),
        ("skipped_limits", _count(status, "skipped_limits")),
        ("remaining_batch_slots", _count(status, "remaining_batch_slots")),
        ("remaining_global_slots", _count(status, "remaining_global_slots")),
    )

    lines = [
        "",
        "=" * 72,
        "FACE-VORSCHLÄGE",
        "=" * 72,
        f"Batch:              {batch_id}",
        f"Status:             {state}",
        f"Personen:           {people}",
    ]
    for label, value in fields:
        lines.append(f"{label + ':':22}{value}")

    reason = status.get("reason")
    if reason is not None:
        lines.append(f"Grund:              {_text(reason, 'unknown')}")
    action = status.get("action")
    if action is not None:
        lines.append(f"Aktion erforderlich: {_text(action, 'none')}")

    lines.extend(("=" * 72, ""))
    return "\n".join(lines)


def _required_text(status: Mapping[str, Any], key: str) -> str:
    value = status.get(key)
    if not isinstance(value, str) or not value.strip():
        raise FaceProposalStatusError(f"{key} must be a non-empty string")
    return value.strip()


def _text(value: Any, fallback: str) -> str:
    if not isinstance(value, str) or not value.strip():
        return fallback
    return value.strip()


def _people(value: Any) -> str:
    if not isinstance(value, (list, tuple, set)):
        raise FaceProposalStatusError(
            "people_with_new_proposals must be a sequence"
        )
    names = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise FaceProposalStatusError(
                "people_with_new_proposals must contain non-empty strings"
            )
        names.append(item.strip())
    return ", ".join(sorted(set(names))) if names else "-"


def _count(status: Mapping[str, Any], key: str) -> int:
    value = status.get(key, 0)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise FaceProposalStatusError(f"{key} must be a non-negative integer")
    return value
