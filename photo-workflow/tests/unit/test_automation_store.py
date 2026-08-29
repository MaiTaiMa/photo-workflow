# =============================================================================
# PROJECT:     photo-workflow
# FILE:        tests/unit/test_automation_store.py
# PURPOSE:     Prüft atomare Prediction-Artefakte mit Policy-gebundener Identität.
# AUTHOR:      Matzethias
# DATE:        2026-08-29
# VERSION:     1.2.0
# REQUIRES:    Python 3.11+
# CHANGES:
#   2026-08-22 | 1.2.0 | C1.2.2: Persistenz gegen manipulierte Prediction-Identität abgesichert.\n  2026-08-22 | 1.1.0 | C1.2.2: Prediction-Fixture an Policy und ID gebunden.
# =============================================================================


import json

import pytest

from app.automation_contract import (
    PREDICTION_SCHEMA_VERSION,
    build_prediction_id,
)
from app.automation_store import (
    prediction_batch_path,
    validate_prediction_batch,
    write_prediction_batch,
)


def prediction(batch_id: str = "20260811_001") -> dict:
    record = {
        "schema_version": PREDICTION_SCHEMA_VERSION,
        "producer_version": "v1.4",
        "batch_id": batch_id,
        "image_id": "image.jpg",
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


def test_write_creates_valid_prediction_artifact(tmp_path) -> None:
    target = write_prediction_batch(
        tmp_path,
        "20260811_001",
        [prediction()],
    )

    payload = json.loads(target.read_text(encoding="utf-8"))
    validate_prediction_batch(payload)
    assert target == prediction_batch_path(tmp_path, "20260811_001")
    assert payload["predictions"][0]["image_id"] == "image.jpg"


def test_invalid_prediction_does_not_replace_existing_artifact(tmp_path) -> None:
    target = write_prediction_batch(
        tmp_path,
        "20260811_001",
        [prediction()],
    )
    original = target.read_text(encoding="utf-8")
    invalid = prediction()
    invalid["final_score"] = 2.0

    with pytest.raises(ValueError, match="final_score"):
        write_prediction_batch(tmp_path, "20260811_001", [invalid])

    assert target.read_text(encoding="utf-8") == original


def test_tampered_prediction_id_does_not_replace_existing_artifact(
    tmp_path,
) -> None:
    target = write_prediction_batch(
        tmp_path,
        "20260811_001",
        [prediction()],
    )
    original = target.read_text(encoding="utf-8")
    tampered = prediction()
    tampered["policy_version"] = "2.0"

    with pytest.raises(ValueError, match="does not match prediction identity"):
        write_prediction_batch(tmp_path, "20260811_001", [tampered])

    assert target.read_text(encoding="utf-8") == original


def test_forbidden_embedding_field_is_rejected(tmp_path) -> None:
    invalid = prediction()
    invalid["embedding"] = [0.1, 0.2]

    with pytest.raises(ValueError, match="forbidden"):
        write_prediction_batch(tmp_path, "20260811_001", [invalid])


def test_prediction_batch_id_must_match_artifact_batch(tmp_path) -> None:
    with pytest.raises(ValueError, match="does not match"):
        write_prediction_batch(
            tmp_path,
            "20260811_001",
            [prediction("different_batch")],
        )


def test_path_traversal_in_batch_id_is_rejected(tmp_path) -> None:
    with pytest.raises(ValueError, match="path separators"):
        write_prediction_batch(tmp_path, "../escape", [prediction("../escape")])