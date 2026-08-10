import pytest

from app.automation_contract import (
    PREDICTION_SCHEMA_VERSION,
    build_prediction_record,
    validate_prediction_record,
)


def valid_record() -> dict:
    return {
        "schema_version": PREDICTION_SCHEMA_VERSION,
        "producer_version": "1.2.0",
        "batch_id": "20260811_001",
        "image_id": "relative/path/image.jpg",
        "model_version": "personal-score-v1",
        "predicted_decision": "keep",
        "prediction_reason": "high_confidence_keep",
        "personal_score": 0.95,
        "final_score": 0.93,
        "predicted_at": "2026-08-11T00:00:00Z",
    }


def test_valid_prediction_record_is_accepted() -> None:
    validate_prediction_record(valid_record())


def test_builder_returns_valid_versioned_record() -> None:
    record = build_prediction_record(**{
        key: value
        for key, value in valid_record().items()
        if key != "schema_version"
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

    validate_prediction_record(record)


def test_invalid_timestamp_is_rejected() -> None:
    record = valid_record()
    record["predicted_at"] = "not-a-timestamp"

    with pytest.raises(ValueError, match="ISO-8601"):
        validate_prediction_record(record)
