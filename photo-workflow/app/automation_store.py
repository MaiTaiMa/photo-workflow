"""
Skript: app/automation_store.py
Zweck: Speichert validierte Shadow-Prognosen atomar je Batch.
Version: 1.0.0
"""

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from app.automation_contract import (
    PREDICTION_SCHEMA_VERSION,
    REQUIRED_FIELDS,
    build_prediction_id,
    validate_prediction_record,
)


BATCH_SCHEMA_VERSION = "1.0"
FORBIDDEN_FIELD_PARTS = ("embedding", "image_bytes", "binary")


def prediction_batch_path(runtime_path: str | Path, batch_id: str) -> Path:
    """Return the controlled prediction-artifact path for one batch."""
    _validate_batch_id(batch_id)
    return Path(runtime_path) / "automation" / "predictions" / f"{batch_id}.json"


def write_prediction_batch(
    runtime_path: str | Path,
    batch_id: str,
    predictions: Iterable[Mapping[str, Any]],
) -> Path:
    """Validate and atomically replace the prediction artifact for one batch."""
    _validate_batch_id(batch_id)
    normalized_predictions = [dict(record) for record in predictions]
    _validate_predictions(batch_id, normalized_predictions)

    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "schema_version": BATCH_SCHEMA_VERSION,
        "prediction_schema_version": PREDICTION_SCHEMA_VERSION,
        "batch_id": batch_id,
        "created_at": now,
        "updated_at": now,
        "predictions": normalized_predictions,
    }
    validate_prediction_batch(payload)

    target = prediction_batch_path(runtime_path, batch_id)
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
        validate_prediction_batch(persisted_payload)
        os.replace(temporary, target)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise

    return target


def validate_prediction_batch(payload: Mapping[str, Any]) -> None:
    """Raise ValueError when a persisted batch payload violates the contract."""
    required = {
        "schema_version",
        "prediction_schema_version",
        "batch_id",
        "created_at",
        "updated_at",
        "predictions",
    }
    missing = required.difference(payload)
    if missing:
        raise ValueError(f"prediction batch misses required fields: {sorted(missing)}")
    if payload["schema_version"] != BATCH_SCHEMA_VERSION:
        raise ValueError("unsupported prediction batch schema_version")
    if payload["prediction_schema_version"] != PREDICTION_SCHEMA_VERSION:
        raise ValueError("unsupported prediction schema_version")

    batch_id = payload["batch_id"]
    _validate_batch_id(batch_id)
    _validate_timestamp(payload["created_at"], "created_at")
    _validate_timestamp(payload["updated_at"], "updated_at")

    predictions = payload["predictions"]
    if not isinstance(predictions, list):
        raise ValueError("predictions must be a list")
    _validate_predictions(batch_id, predictions)


def _validate_predictions(
    batch_id: str,
    predictions: Iterable[Mapping[str, Any]],
) -> None:
    for record in predictions:
        if not isinstance(record, Mapping):
            raise ValueError("each prediction must be a mapping")
        forbidden = [
            key for key in record
            if any(part in key.lower() for part in FORBIDDEN_FIELD_PARTS)
        ]
        if forbidden:
            raise ValueError(f"forbidden prediction fields: {sorted(forbidden)}")
        extra = set(record).difference(REQUIRED_FIELDS)
        if extra:
            raise ValueError(f"unexpected prediction fields: {sorted(extra)}")
        validate_prediction_record(record)
        # prediction_id muss zur aktuellen Record-Identität passen
        expected_id = build_prediction_id(record)
        if record.get("prediction_id") != expected_id:
            raise ValueError("prediction_id does not match prediction identity")
        if record["batch_id"] != batch_id:
            raise ValueError("prediction batch_id does not match artifact batch_id")


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
