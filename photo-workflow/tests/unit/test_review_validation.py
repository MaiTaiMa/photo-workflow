"""
Skript: tests/unit/test_review_validation.py
Zweck: Prüft die Validierung von Predictions gegen menschliche Reviews.
Version: 1.2.0

Änderungsprotokoll:
  2026-08-22 | 1.2.0 | C1.2.4: Test für gemischte Policy-Versionen ergänzt.
  2026-08-22 | 1.1.0 | C1.2.2: Test-Predictions an Policy-Version gebunden.

Änderungsprotokoll:
  2026-08-22 | 1.1.0 | C1.2.2: Test-Predictions an Policy-Version gebunden.
"""

import json

from app.automation_contract import build_prediction_record
from app.automation_store import write_prediction_batch
from app.human_review_contract import build_human_review_record
from app.human_review_store import write_human_review_batch
from app.review_validation import validate_batch_predictions


def seed_predictions(runtime_path) -> None:
    batch_id = "2025-11-02"
    predictions = [
        build_prediction_record(
            producer_version="v1.4", batch_id=batch_id, image_id="keep.jpg",
            model_version="personal-score-v1", policy_version="1.0", predicted_decision="keep",
            prediction_reason="high_confidence_keep", personal_score=0.95,
            final_score=0.92, predicted_at="2026-08-11T00:00:00Z",
        ),
        build_prediction_record(
            producer_version="v1.4", batch_id=batch_id, image_id="reject.jpg",
            model_version="personal-score-v1", policy_version="1.0", predicted_decision="reject",
            prediction_reason="high_confidence_reject", personal_score=0.10,
            final_score=0.12, predicted_at="2026-08-11T00:00:00Z",
        ),
        build_prediction_record(
            producer_version="v1.4", batch_id=batch_id, image_id="review.jpg",
            model_version="personal-score-v1", policy_version="1.0", predicted_decision="review",
            prediction_reason="manual_review_zone", personal_score=0.50,
            final_score=0.50, predicted_at="2026-08-11T00:00:00Z",
        ),
        build_prediction_record(
            producer_version="v1.4", batch_id=batch_id, image_id="unreviewed.jpg",
            model_version="personal-score-v1", policy_version="1.0", predicted_decision="reject",
            prediction_reason="high_confidence_reject", personal_score=0.10,
            final_score=0.12, predicted_at="2026-08-11T00:00:00Z",
        ),
    ]
    write_prediction_batch(runtime_path, batch_id, predictions)


def test_validation_compares_predictions_with_human_reviews(tmp_path) -> None:
    seed_predictions(tmp_path)
    reviews = [
        build_human_review_record(
            producer_version="v1.4", batch_id="2025-11-02", image_id="keep.jpg",
            human_decision="keep", human_decided_at="2026-08-11T00:10:00Z",
        ),
        build_human_review_record(
            producer_version="v1.4", batch_id="2025-11-02", image_id="reject.jpg",
            human_decision="keep", human_decided_at="2026-08-11T00:10:00Z",
        ),
    ]
    write_human_review_batch(tmp_path, "2025-11-02", reviews)

    report, target = validate_batch_predictions(tmp_path, "2025-11-02", "v1.4")

    assert report["prediction_count"] == 4
    assert report["eligible_predictions"] == 3
    assert report["excluded_review_predictions"] == 1
    assert report["unreviewed_predictions"] == 1
    assert report["evaluated_predictions"] == 2
    assert report["matching_predictions"] == 1
    assert report["overall_agreement"] == 0.5
    assert report["keep_precision"] == 1.0
    assert report["reject_precision"] == 0.0
    assert json.loads(target.read_text(encoding="utf-8"))["status"] == "evaluable"


def test_validation_without_human_reviews_is_not_evaluable(tmp_path) -> None:
    seed_predictions(tmp_path)

    report, _ = validate_batch_predictions(tmp_path, "2025-11-02", "v1.4")

    assert report["evaluated_predictions"] == 0
    assert report["unreviewed_predictions"] == 3
    assert report["status"] == "not_evaluable"


def test_mixed_policy_versions_in_one_batch_are_rejected(tmp_path) -> None:
    from pytest import raises

    from app.automation_store import write_prediction_batch

    batch_id = "2025-11-02"
    predictions = [
        build_prediction_record(
            producer_version="v1.4", batch_id=batch_id, image_id="keep.jpg",
            model_version="personal-score-v1", policy_version="1.0", predicted_decision="keep",
            prediction_reason="high_confidence_keep", personal_score=0.95,
            final_score=0.92, predicted_at="2026-08-11T00:00:00Z",
        ),
        build_prediction_record(
            producer_version="v1.4", batch_id=batch_id, image_id="reject.jpg",
            model_version="personal-score-v1", policy_version="1.1", predicted_decision="reject",
            prediction_reason="high_confidence_reject", personal_score=0.10,
            final_score=0.12, predicted_at="2026-08-11T00:00:00Z",
        ),
    ]
    write_prediction_batch(tmp_path, batch_id, predictions)

    with raises(ValueError, match="exactly one policy_version"):
        validate_batch_predictions(tmp_path, batch_id, "v1.4")


def test_missing_prediction_artifact_is_rejected(tmp_path) -> None:
    from pytest import raises

    with raises(FileNotFoundError, match="prediction artifact"):
        validate_batch_predictions(tmp_path, "2025-11-02", "v1.4")
