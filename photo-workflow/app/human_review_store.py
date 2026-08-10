"""
Skript: app/human_review_store.py
Zweck: Speichert menschliche Review-Entscheidungen atomar je Batch.
Version: 1.0.0
"""

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from app.human_review_contract import (
    REQUIRED_REVIEW_FIELDS,
    REVIEW_SCHEMA_VERSION,
    validate_human_review_record,
)


BATCH_SCHEMA_VERSION = "1.0"
FORBIDDEN_FIELD_PARTS = ("embedding", "image_bytes", "binary")


def human_review_batch_path(runtime_path: str | Path, batch_id: str) -> Path:
    """Return the controlled review-artifact path for one batch."""
    _validate_batch_id(batch_id)
    return Path(runtime_path) / "automation" / "reviews" / f"{batch_id}.json"


def write_human_review_batch(
    runtime_path: str | Path,
    batch_id: str,
    reviews: Iterable[Mapping[str, Any]],
) -> Path:
    """Validate and atomically replace the human-review artifact for one batch."""
    _validate_batch_id(batch_id)
    normalized_reviews = [dict(record) for record in reviews]
    _validate_reviews(batch_id, normalized_reviews)

    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "schema_version": BATCH_SCHEMA_VERSION,
        "review_schema_version": REVIEW_SCHEMA_VERSION,
        "batch_id": batch_id,
        "created_at": now,
        "updated_at": now,
        "reviews": normalized_reviews,
    }
    validate_human_review_batch(payload)

    target = human_review_batch_path(runtime_path, batch_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=target.parent,
        prefix=f".{batch_id}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)

    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())

        with temporary.open(encoding="utf-8") as handle:
            persisted_payload = json.load(handle)
        validate_human_review_batch(persisted_payload)
        os.replace(temporary, target)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise

    return target


def validate_human_review_batch(payload: Mapping[str, Any]) -> None:
    """Raise ValueError when a persisted review batch violates the contract."""
    required = {
        "schema_version",
        "review_schema_version",
        "batch_id",
        "created_at",
        "updated_at",
        "reviews",
    }
    missing = required.difference(payload)
    if missing:
        raise ValueError(f"human review batch misses required fields: {sorted(missing)}")
    if payload["schema_version"] != BATCH_SCHEMA_VERSION:
        raise ValueError("unsupported human review batch schema_version")
    if payload["review_schema_version"] != REVIEW_SCHEMA_VERSION:
        raise ValueError("unsupported human review schema_version")

    batch_id = payload["batch_id"]
    _validate_batch_id(batch_id)
    _validate_timestamp(payload["created_at"], "created_at")
    _validate_timestamp(payload["updated_at"], "updated_at")

    reviews = payload["reviews"]
    if not isinstance(reviews, list):
        raise ValueError("reviews must be a list")
    _validate_reviews(batch_id, reviews)


def _validate_reviews(
    batch_id: str,
    reviews: Iterable[Mapping[str, Any]],
) -> None:
    seen_image_ids: set[str] = set()
    for record in reviews:
        if not isinstance(record, Mapping):
            raise ValueError("each human review must be a mapping")
        forbidden = [
            key for key in record
            if any(part in key.lower() for part in FORBIDDEN_FIELD_PARTS)
        ]
        if forbidden:
            raise ValueError(f"forbidden human review fields: {sorted(forbidden)}")
        extra = set(record).difference(REQUIRED_REVIEW_FIELDS | {"reason"})
        if extra:
            raise ValueError(f"unexpected human review fields: {sorted(extra)}")
        validate_human_review_record(record)
        if record["batch_id"] != batch_id:
            raise ValueError("human review batch_id does not match artifact batch_id")
        image_id = record["image_id"]
        if image_id in seen_image_ids:
            raise ValueError("human review artifact contains duplicate image_id")
        seen_image_ids.add(image_id)


def _validate_batch_id(batch_id: Any) -> None:
    if not isinstance(batch_id, str) or not batch_id.strip():
        raise ValueError("batch_id must be a non-empty string")
    if Path(batch_id).name != batch_id or batch_id in {".", ".."}:
        raise ValueError("batch_id must not contain path separators")


def _validate_timestamp(value: Any, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be an ISO-8601 timestamp")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{field} must be an ISO-8601 timestamp") from error
