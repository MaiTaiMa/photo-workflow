# =============================================================================
# PROJECT:     photo-workflow
# FILE:        tests/unit/test_human_review_contract.py
# PURPOSE:     Photo Workflow Module
# AUTHOR:      Matzethias
# DATE:        2026-08-29
# VERSION:     1.0.0
# REQUIRES:    Python 3.11+
# CHANGES:
#   Initial version
# =============================================================================


import pytest

from app.human_review_contract import (
    REVIEW_SCHEMA_VERSION,
    build_human_review_record,
    validate_human_review_record,
)


def review() -> dict:
    return {
        "schema_version": REVIEW_SCHEMA_VERSION,
        "producer_version": "v1.4",
        "batch_id": "20260811_001",
        "image_id": "image.jpg",
        "human_decision": "keep",
        "human_decided_at": "2026-08-11T00:00:00Z",
        "reason": "manual_review",
    }


def test_valid_human_review_is_accepted() -> None:
    validate_human_review_record(review())


def test_builder_creates_valid_human_review() -> None:
    record = build_human_review_record(**{
        key: value
        for key, value in review().items()
        if key != "schema_version"
    })

    assert record["schema_version"] == REVIEW_SCHEMA_VERSION
    assert record["human_decision"] == "keep"


def test_invalid_decision_is_rejected() -> None:
    record = review()
    record["human_decision"] = "review"

    with pytest.raises(ValueError, match="keep or reject"):
        validate_human_review_record(record)


def test_missing_timestamp_is_rejected() -> None:
    record = review()
    del record["human_decided_at"]

    with pytest.raises(ValueError, match="required fields"):
        validate_human_review_record(record)


def test_extra_or_embedding_fields_are_rejected() -> None:
    record = review()
    record["embedding"] = [0.1]

    with pytest.raises(ValueError, match="unexpected"):
        validate_human_review_record(record)