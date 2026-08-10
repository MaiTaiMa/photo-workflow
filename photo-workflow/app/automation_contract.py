"""
Skript: app/automation_contract.py
Zweck: Definiert und validiert versionierte KI-Prognose-Datensatze.
Version: 1.0.0
"""

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
    "predicted_decision",
    "prediction_reason",
    "personal_score",
    "final_score",
    "predicted_at",
})


def build_prediction_record(
    *,
    producer_version: str,
    batch_id: str,
    image_id: str,
    model_version: str,
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
        "predicted_decision": predicted_decision,
        "prediction_reason": prediction_reason,
        "personal_score": personal_score,
        "final_score": final_score,
        "predicted_at": predicted_at,
    }
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
