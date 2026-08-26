"""
Skript: tests/unit/test_automation_contract.py
Zweck: Prüft den Prediction-Vertrag und deterministische Prediction-IDs.
Version: 1.1.0

Änderungsprotokoll:
  2026-08-22 | 1.1.0 | C1.2.2: Prediction-ID-Hilfsfunktion getestet.
"""

import pytest

from app.automation_contract import (
    PREDICTION_SCHEMA_VERSION,
    build_prediction_id,
    build_prediction_record,
    validate_prediction_record,
)


def valid_record() -> dict:
    record = {
        "schema_version": PREDICTION_SCHEMA_VERSION,
        "producer_version": "1.2.0",
        "batch_id": "20260811_001",
        "image_id": "relative/path/image.jpg",
        "model_version": "personal-score-v1",
        "policy_version": "1.0",
        "predicted_decision": "keep",
        "prediction_reason": "high_confidence_keep",
        "personal_score": 0.95,
        "final_score": 0.93,
        "predicted_at": "2026-08-11T00:00:00Z",
    }
    record["prediction_id"] = build_prediction_id(record)
    return record


def test_valid_prediction_record_is_accepted() -> None:
    validate_prediction_record(valid_record())


def test_builder_returns_valid_versioned_record() -> None:
    record = build_prediction_record(**{
        key: value
        for key, value in valid_record().items()
        if key not in {"schema_version", "prediction_id"}
    })

    assert record["schema_version"] == PREDICTION_SCHEMA_VERSION
    assert record["predicted_decision"] == "keep"


def test_missing_required_field_is_rejected() -> None:
    record = valid_record()
    del record["batch_id"]

    with pytest.raises(ValueError, match="required fields"):
        validate_prediction_record(record)


def test_unknown_prediction_is_rejected() -> None:
    record = valid_record()
    record["predicted_decision"] = "auto_keep"

    with pytest.raises(ValueError, match="predicted_decision"):
        validate_prediction_record(record)


def test_out_of_range_score_is_rejected() -> None:
    record = valid_record()
    record["final_score"] = 1.01

    with pytest.raises(ValueError, match="final_score"):
        validate_prediction_record(record)


def test_keep_prediction_requires_scores() -> None:
    record = valid_record()
    record["personal_score"] = None

    with pytest.raises(ValueError, match="require both scores"):
        validate_prediction_record(record)


def test_review_prediction_may_have_missing_scores() -> None:
    record = valid_record()
    record["predicted_decision"] = "review"
    record["prediction_reason"] = "score_unavailable"
    record["personal_score"] = None
    record["final_score"] = None
    record["prediction_id"] = build_prediction_id(record)

    validate_prediction_record(record)


def test_invalid_timestamp_is_rejected() -> None:
    record = valid_record()
    record["predicted_at"] = ""

    with pytest.raises(ValueError, match="predicted_at must be a non-empty string"):
        validate_prediction_record(record)


def _prediction_identity() -> dict:
    return {
        "schema_version": PREDICTION_SCHEMA_VERSION,
        "producer_version": "1.2.0",
        "batch_id": "20260811_001",
        "image_id": "image.jpg",
        "model_version": "personal-score-v1",
        "policy_version": "1.0",
        "predicted_decision": "keep",
        "prediction_reason": "high_confidence_keep",
        "personal_score": 0.95,
        "final_score": 0.93,
        "predicted_at": "2026-08-11T00:00:00Z",
    }


def test_prediction_id_is_deterministic() -> None:
    first = build_prediction_id(_prediction_identity())
    second = build_prediction_id(_prediction_identity())

    assert first == second
    assert first.startswith("sha256:")
    assert len(first) == 71


def test_prediction_id_rejects_incomplete_identity() -> None:
    identity = _prediction_identity()
    del identity["policy_version"]

    with pytest.raises(ValueError, match="policy_version"):
        build_prediction_id(identity)


def test_tampered_prediction_identity_is_rejected() -> None:
    """Prediction-ID muss sich ändern, wenn sich model_version ändert."""
    from app.automation_contract import build_prediction_id

    base = {
        "schema_version": "1.0",
        "producer_version": "1.2.0",
        "batch_id": "20260811_001",
        "image_id": "image.jpg",
        "model_version": "personal-score-v1",
        "policy_version": "1.0",
        "predicted_decision": "keep",
        "prediction_reason": "high_confidence_keep",
        "personal_score": 0.95,
        "final_score": 0.93,
        "predicted_at": "2026-08-11T00:00:00Z",
    }
    id1 = build_prediction_id(base)
    base["model_version"] = "other-model-v1"
    id2 = build_prediction_id(base)
    assert id1 != id2, "prediction_id must change when model_version changes"
