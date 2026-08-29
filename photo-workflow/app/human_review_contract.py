# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/human_review_contract.py
# PURPOSE:     Definiert und validiert menschliche Keep-/Reject-Entscheidungen.
# AUTHOR:      Matzethias
# DATE:        2026-08-29
# VERSION:     1.0.0
# REQUIRES:    Python 3.11+
# CHANGES:
#   Initial version
# =============================================================================


from datetime import datetime
from typing import Any, Mapping


REVIEW_SCHEMA_VERSION = "1.0"
VALID_HUMAN_DECISIONS = frozenset({"keep", "reject"})
REQUIRED_REVIEW_FIELDS = frozenset({
    "schema_version",
    "producer_version",
    "batch_id",
    "image_id",
    "human_decision",
    "human_decided_at",
})
OPTIONAL_REVIEW_FIELDS = frozenset({"reason"})


def build_human_review_record(
    *,
    producer_version: str,
    batch_id: str,
    image_id: str,
    human_decision: str,
    human_decided_at: str,
    reason: str | None = None,
) -> dict[str, Any]:
    """Build and validate a non-operative human review record."""
    record: dict[str, Any] = {
        "schema_version": REVIEW_SCHEMA_VERSION,
        "producer_version": producer_version,
        "batch_id": batch_id,
        "image_id": image_id,
        "human_decision": human_decision,
        "human_decided_at": human_decided_at,
    }
    if reason is not None:
        record["reason"] = reason
    validate_human_review_record(record)
    return record


def validate_human_review_record(record: Mapping[str, Any]) -> None:
    """Raise ValueError when a human review record violates the contract."""
    missing = REQUIRED_REVIEW_FIELDS.difference(record)
    if missing:
        raise ValueError(f"human review misses required fields: {sorted(missing)}")

    extra = set(record).difference(REQUIRED_REVIEW_FIELDS | OPTIONAL_REVIEW_FIELDS)
    if extra:
        raise ValueError(f"unexpected human review fields: {sorted(extra)}")

    if record["schema_version"] != REVIEW_SCHEMA_VERSION:
        raise ValueError("unsupported human review schema_version")

    for field in ("producer_version", "batch_id", "image_id"):
        if not isinstance(record[field], str) or not record[field].strip():
            raise ValueError(f"{field} must be a non-empty string")

    if record["human_decision"] not in VALID_HUMAN_DECISIONS:
        raise ValueError("human_decision must be keep or reject")

    reason = record.get("reason")
    if reason is not None and (
        not isinstance(reason, str) or not reason.strip()
    ):
        raise ValueError("reason must be a non-empty string when provided")

    _validate_timestamp(record["human_decided_at"], "human_decided_at")


def _validate_timestamp(value: Any, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be an ISO-8601 timestamp")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{field} must be an ISO-8601 timestamp") from error