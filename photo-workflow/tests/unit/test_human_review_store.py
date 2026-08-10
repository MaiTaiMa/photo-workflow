import json

import pytest

from app.human_review_contract import REVIEW_SCHEMA_VERSION
from app.human_review_store import (
    human_review_batch_path,
    validate_human_review_batch,
    write_human_review_batch,
)


def review(batch_id: str = "20260811_001") -> dict:
    return {
        "schema_version": REVIEW_SCHEMA_VERSION,
        "producer_version": "v1.4",
        "batch_id": batch_id,
        "image_id": "image.jpg",
        "human_decision": "keep",
        "human_decided_at": "2026-08-11T00:00:00Z",
    }


def test_write_creates_valid_review_artifact(tmp_path) -> None:
    target = write_human_review_batch(
        tmp_path,
        "20260811_001",
        [review()],
    )

    payload = json.loads(target.read_text(encoding="utf-8"))
    validate_human_review_batch(payload)
    assert target == human_review_batch_path(tmp_path, "20260811_001")


def test_duplicate_image_id_is_rejected(tmp_path) -> None:
    with pytest.raises(ValueError, match="duplicate"):
        write_human_review_batch(
            tmp_path,
            "20260811_001",
            [review(), review()],
        )


def test_invalid_review_does_not_replace_existing_artifact(tmp_path) -> None:
    target = write_human_review_batch(
        tmp_path,
        "20260811_001",
        [review()],
    )
    original = target.read_text(encoding="utf-8")
    invalid = review()
    invalid["human_decision"] = "review"

    with pytest.raises(ValueError, match="keep or reject"):
        write_human_review_batch(tmp_path, "20260811_001", [invalid])

    assert target.read_text(encoding="utf-8") == original


def test_embedding_field_is_rejected(tmp_path) -> None:
    invalid = review()
    invalid["embedding"] = [0.1]

    with pytest.raises(ValueError, match="forbidden"):
        write_human_review_batch(tmp_path, "20260811_001", [invalid])
