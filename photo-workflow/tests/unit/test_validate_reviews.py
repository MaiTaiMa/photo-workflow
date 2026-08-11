from app.automation_contract import build_prediction_record
from app.automation_store import write_prediction_batch
from app.human_review_contract import build_human_review_record
from app.human_review_store import write_human_review_batch
from app.validate_reviews import validate_reviews


def test_validate_reviews_creates_report_for_evaluable_batch(tmp_path) -> None:
    prediction = build_prediction_record(
        producer_version="v1.4",
        batch_id="2025-11-02",
        image_id="MST06972.JPG",
        model_version="personal-score-v1",
        predicted_decision="keep",
        prediction_reason="high_confidence_keep",
        personal_score=0.95,
        final_score=0.92,
        predicted_at="2026-08-11T00:00:00Z",
    )
    review = build_human_review_record(
        producer_version="v1.4",
        batch_id="2025-11-02",
        image_id="MST06972.JPG",
        human_decision="keep",
        human_decided_at="2026-08-11T00:10:00Z",
    )
    write_prediction_batch(tmp_path, "2025-11-02", [prediction])
    write_human_review_batch(tmp_path, "2025-11-02", [review])

    report, target = validate_reviews(
        runtime_path=tmp_path,
        batch_id="2025-11-02",
        producer_version="v1.4",
    )

    assert report["status"] == "evaluable"
    assert report["overall_agreement"] == 1.0
    assert target.is_file()
