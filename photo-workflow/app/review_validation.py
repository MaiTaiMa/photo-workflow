"""
Skript: app/review_validation.py
Zweck: Vergleicht KI-Prognosen mit menschlichen Keep-/Reject-Entscheidungen.
Version: 2.0.0
"""

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from app.automation_store import prediction_batch_path, validate_prediction_batch
from app.human_review_store import human_review_batch_path, validate_human_review_batch


VALIDATION_SCHEMA_VERSION = "1.0"


def validate_batch_predictions(
    runtime_path: str | Path,
    batch_id: str,
    producer_version: str,
) -> tuple[dict[str, Any], Path]:
    """Compare one batch of predictions with persisted human decisions."""
    prediction_payload = _load_prediction_payload(runtime_path, batch_id)
    review_payload = _load_review_payload(runtime_path, batch_id)
    reviews = {record["image_id"]: record for record in review_payload["reviews"]}

    eligible_predictions = 0
    excluded_review_predictions = 0
    unreviewed_predictions = 0
    evaluated_predictions = 0
    matching_predictions = 0
    predicted_keep = 0
    predicted_reject = 0
    reviewed_predicted_keep = 0
    reviewed_predicted_reject = 0
    confirmed_keep = 0
    confirmed_reject = 0

    for prediction in prediction_payload["predictions"]:
        decision = prediction["predicted_decision"]
        if decision == "review" or prediction["prediction_reason"] == "manual_keep_override":
            excluded_review_predictions += 1
            continue

        eligible_predictions += 1
        if decision == "keep":
            predicted_keep += 1
        else:
            predicted_reject += 1

        review = reviews.get(prediction["image_id"])
        if review is None:
            unreviewed_predictions += 1
            continue

        evaluated_predictions += 1
        human_decision = review["human_decision"]
        if decision == "keep":
            reviewed_predicted_keep += 1
            if human_decision == "keep":
                confirmed_keep += 1
        else:
            reviewed_predicted_reject += 1
            if human_decision == "reject":
                confirmed_reject += 1

        if decision == human_decision:
            matching_predictions += 1

    report = {
        "schema_version": VALIDATION_SCHEMA_VERSION,
        "producer_version": producer_version,
        "batch_id": batch_id,
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "prediction_count": len(prediction_payload["predictions"]),
        "eligible_predictions": eligible_predictions,
        "excluded_review_predictions": excluded_review_predictions,
        "unreviewed_predictions": unreviewed_predictions,
        "evaluated_predictions": evaluated_predictions,
        "matching_predictions": matching_predictions,
        "overall_agreement": _ratio(matching_predictions, evaluated_predictions),
        "predicted_keep": predicted_keep,
        "predicted_reject": predicted_reject,
        "reviewed_predicted_keep": reviewed_predicted_keep,
        "reviewed_predicted_reject": reviewed_predicted_reject,
        "confirmed_keep": confirmed_keep,
        "confirmed_reject": confirmed_reject,
        "keep_precision": _ratio(confirmed_keep, reviewed_predicted_keep),
        "reject_precision": _ratio(confirmed_reject, reviewed_predicted_reject),
        "status": "evaluable" if evaluated_predictions else "not_evaluable",
    }
    validate_validation_report(report)
    target = write_validation_report(runtime_path, batch_id, report)
    return report, target


def write_validation_report(
    runtime_path: str | Path,
    batch_id: str,
    report: Mapping[str, Any],
) -> Path:
    """Atomically write one already validated validation report."""
    validate_validation_report(report)
    if report["batch_id"] != batch_id:
        raise ValueError("validation report batch_id does not match target batch_id")

    target = Path(runtime_path) / "automation" / "validation" / f"{batch_id}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=target.parent,
        prefix=f".{batch_id}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        persisted = json.loads(temporary.read_text(encoding="utf-8"))
        validate_validation_report(persisted)
        os.replace(temporary, target)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return target


def validate_validation_report(report: Mapping[str, Any]) -> None:
    """Raise ValueError when a validation report is incomplete or inconsistent."""
    required = {
        "schema_version", "producer_version", "batch_id", "validated_at",
        "prediction_count", "eligible_predictions", "excluded_review_predictions",
        "unreviewed_predictions", "evaluated_predictions", "matching_predictions",
        "overall_agreement", "predicted_keep", "predicted_reject",
        "reviewed_predicted_keep", "reviewed_predicted_reject",
        "confirmed_keep", "confirmed_reject", "keep_precision",
        "reject_precision", "status",
    }
    missing = required.difference(report)
    if missing:
        raise ValueError(f"validation report misses required fields: {sorted(missing)}")
    if report["schema_version"] != VALIDATION_SCHEMA_VERSION:
        raise ValueError("unsupported validation schema_version")
    if report["status"] not in {"evaluable", "not_evaluable"}:
        raise ValueError("unsupported validation status")
    if not isinstance(report["batch_id"], str) or not report["batch_id"].strip():
        raise ValueError("batch_id must be a non-empty string")
    for field in ("producer_version", "validated_at"):
        if not isinstance(report[field], str) or not report[field].strip():
            raise ValueError(f"{field} must be a non-empty string")
    for field in required.intersection({
        "prediction_count", "eligible_predictions", "excluded_review_predictions",
        "unreviewed_predictions", "evaluated_predictions", "matching_predictions",
        "predicted_keep", "predicted_reject", "reviewed_predicted_keep",
        "reviewed_predicted_reject", "confirmed_keep", "confirmed_reject",
    }):
        if not isinstance(report[field], int) or report[field] < 0:
            raise ValueError(f"{field} must be a non-negative integer")
    for field in ("overall_agreement", "keep_precision", "reject_precision"):
        value = report[field]
        if value is not None and (not isinstance(value, (int, float)) or not 0.0 <= value <= 1.0):
            raise ValueError(f"{field} must be null or a number between 0.0 and 1.0")


def _load_prediction_payload(runtime_path: str | Path, batch_id: str) -> dict[str, Any]:
    target = prediction_batch_path(runtime_path, batch_id)
    if not target.is_file():
        raise FileNotFoundError(f"prediction artifact does not exist: {target}")
    payload = json.loads(target.read_text(encoding="utf-8"))
    validate_prediction_batch(payload)
    return payload


def _load_review_payload(runtime_path: str | Path, batch_id: str) -> dict[str, Any]:
    target = human_review_batch_path(runtime_path, batch_id)
    if not target.is_file():
        return {"reviews": []}
    payload = json.loads(target.read_text(encoding="utf-8"))
    validate_human_review_batch(payload)
    return payload


def _ratio(numerator: int, denominator: int) -> float | None:
    if not denominator:
        return None
    return round(numerator / denominator, 4)


class ReviewValidator:
    """Compatibility adapter for callers of the former review validator."""

    def __init__(self, runtime_path: Path):
        self.runtime_path = runtime_path

    def validate_decisions(self, batch_id: str, window_days: int = 30) -> dict[str, Any]:
        """Validate persisted decisions; window_days is retained for compatibility."""
        del window_days
        report, _ = validate_batch_predictions(
            self.runtime_path,
            batch_id,
            producer_version="v1.4",
        )
        return report

    def save_validation_report(self, report: Mapping[str, Any], output_path: Path) -> None:
        """Retain the former method for compatibility with existing callers."""
        write_validation_report(output_path.parent.parent.parent, report["batch_id"], report)
