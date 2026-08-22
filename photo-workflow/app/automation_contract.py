"""
Skript: app/automation_contract.py
Zweck: Definiert und validiert versionierte KI-Prognose-Datensatze.
Version: 1.2.0
Requires: Python 3.11

Änderungsprotokoll:
  2026-08-22 | 1.2.0 | C1.2.2: Policy und Prediction-ID verpflichtend gemacht.
  2026-08-22 | 1.1.0 | C1.2.2: Deterministische Prediction-ID-Hilfsfunktion ergänzt.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Mapping


PREDICTION_SCHEMA_VERSION = "1.0"
VALID_PREDICTED_DECISIONS = frozenset({"keep", "reject", "review"})
REQUIRED_FIELDS = frozenset({
    "schema_version",
    "producer_version",
    "batch_id",
    "image_id",
    "model_version",
    "policy_version",
    "prediction_id",
    "predicted_decision",
    "prediction_reason",
    "personal_score",
    "final_score",
    "predicted_at",
})


def build_prediction_id(record: Mapping[str, Any]) -> str:
    """Build a deterministic non-sensitive identifier for one prediction."""
    fields = (
        "schema_version",
        "producer_version",
        "batch_id",
        "image_id",
        "model_version",
        "policy_version",
        "predicted_decision",
        "prediction_reason",
        "personal_score",
        "final_score",
        "predicted_at",
    )
    try:
        identity = {field: record[field] for field in fields}
    except KeyError as error:
        raise ValueError(
            f"prediction identity misses required field: {error.args[0]}"
        ) from error

    payload = json.dumps(
        identity,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_prediction_record(
    *,
    producer_version: str,
    batch_id: str,
    image_id: str,
    model_version: str,
    policy_version: str,
    predicted_decision: str,
    prediction_reason: str,
    personal_score: float | None,
    final_score: float | None,
    predicted_at: str,
) -> dict[str, Any]:
    """Build and validate one immutable, non-operative prediction record."""
    record = {
        "schema_version": PREDICTION_SCHEMA_VERSION,
        "producer_version": producer_version,
        "batch_id": batch_id,
        "image_id": image_id,
        "model_version": model_version,
        "policy_version": policy_version,
        "predicted_decision": predicted_decision,
        "prediction_reason": prediction_reason,
        "personal_score": personal_score,
        "final_score": final_score,
        "predicted_at": predicted_at,
    }
    record["prediction_id"] = build_prediction_id(record)
    validate_prediction_record(record)
    return record


def validate_prediction_record(record: Mapping[str, Any]) -> None:
    """Raise ValueError when a prediction record violates the contract."""
    missing = REQUIRED_FIELDS.difference(record)
    if missing:
        raise ValueError(f"prediction record misses required fields: {sorted(missing)}")

    if record["schema_version"] != PREDICTION_SCHEMA_VERSION:
        raise ValueError("unsupported prediction schema_version")

    for field in (
        "producer_version",
        "batch_id",
        "image_id",
        "model_version",
        "policy_version",
        "prediction_reason",
    ):
        if not isinstance(record[field], str) or not record[field].strip():
            raise ValueError(f"{field} must be a non-empty string")

    decision = record["predicted_decision"]
    if decision not in VALID_PREDICTED_DECISIONS:
        raise ValueError(f"unsupported predicted_decision: {decision}")

    for field in ("personal_score", "final_score"):
        score = record[field]
        if score is not None and (
            isinstance(score, bool)
            or not isinstance(score, (int, float))
            or not 0.0 <= float(score) <= 1.0
        ):
            raise ValueError(f"{field} must be None or a number between 0.0 and 1.0")

    if decision in {"keep", "reject"} and (
        record["personal_score"] is None or record["final_score"] is None
    ):
        raise ValueError("keep and reject predictions require both scores")

    timestamp = record["predicted_at"]
    if not isinstance(timestamp, str) or not timestamp.strip():
        raise ValueError("predicted_at must be an ISO-8601 timestamp")
    try:
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("predicted_at must be an ISO-8601 timestamp") from error

    prediction_id = record["prediction_id"]
    if (
        not isinstance(prediction_id, str)
        or not prediction_id.startswith("sha256:")
        or len(prediction_id) != 71
    ):
        raise ValueError("prediction_id must be a SHA-256 identifier")

    if prediction_id != build_prediction_id(record):
        raise ValueError("prediction_id does not match prediction identity")
