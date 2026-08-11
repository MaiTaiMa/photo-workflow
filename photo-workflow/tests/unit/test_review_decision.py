import pytest

from app.automation_contract import build_prediction_record
from app.automation_store import write_prediction_batch
from app.human_review_store import human_review_batch_path
from app.review_decision import record_human_decision


def seed_prediction(runtime_path, batch_id: str = "2025-11-02") -> None:
    prediction = build_prediction_record(
        producer_version="v1.4",
        batch_id=batch_id,
        image_id="MST06972.JPG",
        model_version="personal-score-v1",
        predicted_decision="review",
        prediction_reason="manual_review_zone",
        personal_score=0.42,
        final_score=0.52,
        predicted_at="2026-08-11T00:00:00Z",
    )
    write_prediction_batch(runtime_path, batch_id, [prediction])


def test_creates_review_for_known_predicted_image(tmp_path) -> None:
    seed_prediction(tmp_path)

    target, status = record_human_decision(
        runtime_path=tmp_path,
        batch_id="2025-11-02",
        image_id="MST06972.JPG",
        decision="keep",
        reason="schaerferes Bild",
        producer_version="v1.4",
    )

    assert status == "created"
    assert target == human_review_batch_path(tmp_path, "2025-11-02")
    assert '"human_decision": "keep"' in target.read_text(encoding="utf-8")


def test_replaces_existing_decision_for_same_image(tmp_path) -> None:
    seed_prediction(tmp_path)
    record_human_decision(
        runtime_path=tmp_path,
        batch_id="2025-11-02",
        image_id="MST06972.JPG",
        decision="keep",
        producer_version="v1.4",
    )

    target, status = record_human_decision(
        runtime_path=tmp_path,
        batch_id="2025-11-02",
        image_id="MST06972.JPG",
        decision="reject",
        producer_version="v1.4",
    )

    content = target.read_text(encoding="utf-8")
    assert status == "updated"
    assert content.count('"image_id": "MST06972.JPG"') == 1
    assert '"human_decision": "reject"' in content


def test_unknown_image_is_rejected(tmp_path) -> None:
    seed_prediction(tmp_path)

    with pytest.raises(ValueError, match="not present"):
        record_human_decision(
            runtime_path=tmp_path,
            batch_id="2025-11-02",
            image_id="unknown.JPG",
            decision="keep",
            producer_version="v1.4",
        )


def test_missing_prediction_artifact_is_rejected(tmp_path) -> None:
    with pytest.raises(FileNotFoundError, match="prediction artifact"):
        record_human_decision(
            runtime_path=tmp_path,
            batch_id="2025-11-02",
            image_id="MST06972.JPG",
            decision="keep",
            producer_version="v1.4",
        )
